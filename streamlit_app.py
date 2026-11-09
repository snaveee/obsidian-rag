"""Streamlit interactive UI for obsidian-rag.

Provides an intuitive workspace for querying notes, viewing grounded AI answers
with verified citations, exploring related wikilink neighbours, filtering by
tags/folders, and inspecting recent query history.
"""

import os
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("ORAG_API_URL", "http://127.0.0.1:8001").rstrip("/")
API_KEY = os.getenv("API_KEY", "")

st.set_page_config(
    page_title="Obsidian RAG — Second Brain Copilot",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Helper Functions (Defined before UI calls to prevent order-of-declaration traps) ---


def get_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    return headers


def fetch_api_status() -> dict[str, Any] | None:
    try:
        resp = requests.get(f"{API_URL}/", timeout=3.0)
        return resp.json() if resp.status_code == 200 else None
    except Exception:
        return None


def trigger_indexing(full: bool = False) -> dict[str, Any] | None:
    try:
        resp = requests.post(
            f"{API_URL}/index",
            json={"full_reindex": full},
            headers=get_headers(),
            timeout=120.0,
        )
        return resp.json() if resp.status_code == 200 else None
    except Exception as exc:
        st.error(f"Indexing request failed: {exc}")
        return None


def fetch_history(limit: int = 15) -> list[dict[str, Any]]:
    try:
        resp = requests.get(
            f"{API_URL}/history",
            params={"limit": limit, "distinct": True},
            headers=get_headers(),
            timeout=3.0,
        )
        if resp.status_code == 200:
            return resp.json().get("history", [])
        return []
    except Exception:
        return []


def query_rag(
    question: str,
    top_k: int = 5,
    tags: list[str] | None = None,
    folder: str | None = None,
    enable_rerank: bool = True,
) -> dict[str, Any] | None:
    payload = {
        "query": question,
        "top_k": top_k,
        "tags": tags or None,
        "folder": folder or None,
        "enable_rerank": enable_rerank,
    }
    try:
        resp = requests.post(
            f"{API_URL}/ask",
            json=payload,
            headers=get_headers(),
            timeout=90.0,
        )
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 503:
            st.error(f"Local AI service unavailable: {resp.json().get('detail')}")
        else:
            st.error(f"API Error ({resp.status_code}): {resp.text}")
        return None
    except Exception as exc:
        st.error(f"Could not connect to obsidian-rag backend: {exc}")
        return None


# --- Session State Initialization ---

if "search_query" not in st.session_state:
    st.session_state["search_query"] = ""

if "last_response" not in st.session_state:
    st.session_state["last_response"] = None

# If a history item was clicked in a previous rerun, apply it before rendering input
if "pending_query" in st.session_state and st.session_state["pending_query"]:
    st.session_state["search_query"] = st.session_state["pending_query"]
    st.session_state["pending_query"] = ""


# --- Sidebar ---

with st.sidebar:
    st.markdown("### 🧠 Obsidian RAG")
    st.caption("Personal Second-Brain Knowledge Copilot")
    st.divider()

    status_data = fetch_api_status()
    if status_data:
        st.success("● Backend Connected", icon="✅")
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Indexed Notes", status_data.get("total_notes", 0))
        with col_b:
            st.metric("Total Chunks", status_data.get("total_chunks", 0))
        last_idx = status_data.get("last_indexed_at")
        if last_idx:
            st.caption(f"Last sync: {last_idx[:19].replace('T', ' ')}")
    else:
        st.error("● Backend Offline", icon="⚠️")
        st.caption("Ensure `fastapi.bat` is running on port 8001.")

    st.subheader("Vault Synchronization")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sync Vault", use_container_width=True):
            with st.spinner("Indexing vault..."):
                res = trigger_indexing(full=False)
                if res and res.get("status") == "success":
                    rep = res.get("report", {})
                    st.toast(f"Synced: +{rep.get('added', 0)} updated: {rep.get('updated', 0)}", icon="🎉")
                    st.rerun()
    with col2:
        if st.button("Full Re-index", use_container_width=True):
            with st.spinner("Rebuilding indexes..."):
                res = trigger_indexing(full=True)
                if res and res.get("status") == "success":
                    st.toast("Full rebuild completed!", icon="🚀")
                    st.rerun()

    st.divider()

    # Filters
    st.subheader("Scope Filters")
    all_tags = []
    all_folders = []
    if status_data:
        all_folders = status_data.get("folders", [])

    selected_tags_input = st.text_input("Filter by Tags (comma separated)", placeholder="e.g. architecture, rag")
    selected_tags = [t.strip().lstrip("#").lower() for t in selected_tags_input.split(",") if t.strip()]

    folder_opts = ["(All Folders)"] + all_folders
    selected_folder_opt = st.selectbox("Filter by Folder", folder_opts)
    selected_folder = None if selected_folder_opt == "(All Folders)" else selected_folder_opt

    enable_rerank_toggle = st.checkbox("Cross-Encoder Re-ranking", value=True)

    st.divider()

    # Search History
    st.subheader("Recent Queries")
    history_entries = fetch_history(limit=10)
    if history_entries:
        for item in history_entries:
            q_text = item.get("query", "")
            btn_label = q_text if len(q_text) <= 30 else f"{q_text[:27]}..."
            if st.button(f"🔍 {btn_label}", key=f"hist_{item['id']}", help=q_text, use_container_width=True):
                st.session_state["pending_query"] = q_text
                st.rerun()
    else:
        st.caption("No queries recorded yet.")


# --- Main Application Area ---

st.title("Personal Vault Knowledge Engine")
st.markdown(
    "Query your Obsidian notes with **BM25 + Dense Hybrid Search**, "
    "**Reciprocal Rank Fusion**, **Cross-Encoder Re-ranking**, and strict grounded AI citations."
)

query_col, btn_col = st.columns([5, 1])
with query_col:
    user_query = st.text_input(
        "Ask anything across your notes:",
        value=st.session_state["search_query"],
        key="main_query_input",
        placeholder="e.g. How does reciprocal rank fusion combine search results?",
    )
with btn_col:
    st.write("")
    st.write("")
    run_clicked = st.button("Ask Copilot", type="primary", use_container_width=True)

# Trigger query when button clicked or when user_query changes
if run_clicked and user_query.strip():
    with st.spinner("Searching vault, re-ranking passages, and generating grounded answer..."):
        resp_data = query_rag(
            question=user_query.strip(),
            top_k=5,
            tags=selected_tags,
            folder=selected_folder,
            enable_rerank=enable_rerank_toggle,
        )
        if resp_data:
            st.session_state["last_response"] = resp_data

# Display Results
resp = st.session_state.get("last_response")
if resp:
    st.divider()

    # Retrieval Metadata Badge
    mode_badge = resp.get("retrieval_mode", "hybrid").upper()
    rerank_flag = "✨ Cross-Encoder Reranked" if resp.get("rerank_applied") else "Fast RRF Fused"
    st.caption(f"Mode: **{mode_badge}** | {rerank_flag} | References Cited: **{len(resp.get('citations', []))}**")

    # Grounded Answer
    st.markdown("### Answer")
    st.markdown(resp.get("answer", ""))

    # Related Notes Graph
    related = resp.get("related_notes", [])
    if related:
        st.markdown("#### 🔗 Related Notes in Graph")
        cols = st.columns(min(len(related), 4))
        for idx, rel in enumerate(related[:4]):
            with cols[idx % 4]:
                rel_badge = "Mutual" if rel["relation"] == "mutual" else ("Outgoing" if rel["relation"] == "links_to" else "Backlink")
                st.info(f"**{rel['title']}**\n\n*{rel_badge}*")

    # Source Citations
    sources = resp.get("sources", [])
    if sources:
        st.markdown("#### 📚 Verified Source References")
        for src in sources:
            cite_num = src.get("citation_index", "?")
            note_title = src.get("title", "Untitled")
            heading = src.get("heading_path") or "Note Body"
            l_start = src.get("line_start", 1)
            l_end = src.get("line_end", 1)
            score = src.get("rerank_score") or src.get("score", 0.0)

            with st.expander(f"[{cite_num}] {note_title} — {heading} (Lines {l_start}–{l_end})"):
                st.caption(f"Score: `{score:.4f}` | Path: `{src.get('chunk_id')}`")
                st.markdown(src.get("text", ""))

elif not status_data or status_data.get("total_notes", 0) == 0:
    st.info("👋 Welcome! Your vault index is currently empty. Click **Sync Vault** in the sidebar to index your notes.")

