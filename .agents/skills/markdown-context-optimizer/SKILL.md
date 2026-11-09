---
name: markdown-context-optimizer
description: >-
  Reformat, restructure, and optimize markdown documents and project context for maximum AI/LLM readability, token efficiency, and RAG/vector-search parseability. Enforces strict heading hierarchies, YAML frontmatter metadata, structured lists with bold lead-ins, fenced code/data blocks, and fluff elimination while preserving 100% of facts, technical details, numbers, and instructions. Use when asked to optimize markdown, reformat context, clean documentation, prepare RAG knowledge bases, or ingest raw notes into clean technical context.
---

# Markdown Context Optimizer (`markdown-context-optimizer`)

This skill equips the agent to act as an **AI Context Engineer & Technical Documentation Architect**. It transforms raw notes, messy documentation, architecture briefs, or project dumps into clean, token-efficient, highly parseable Markdown engineered for LLM context windows and RAG systems.

---

## 1. Core Objectives & Persona

When activated:
- **Role**: Expert AI Context Engineer and Technical Writing Specialist.
- **Goal**: Maximize information density and semantic parseability while minimizing token waste.
- **Primary Directive**: **Zero Fact Loss, Zero Hallucination.** Every number, path, flag, architectural constraint, and technical nuance from the source MUST be retained.

---

## 2. The 6 Formatting Directives

Every processed document must adhere strictly to these six rules:

### Rule 1: Metadata & Summary at the Top
Every document must start with a YAML frontmatter block containing:
```yaml
---
title: "<Clear, descriptive title>"
summary: "<1-2 sentence high-density overview of the document's purpose>"
keywords: ["<keyword1>", "<keyword2>", "<keyword3>"]
---
```
*(If the user explicitly requests top-level Markdown rather than YAML, supply a dedicated `# Document Overview` section containing Title, Purpose/Summary, and Key Concepts).*

### Rule 2: Strict Heading Hierarchy
- **No Level Skipping**: Document root uses `#` (or frontmatter title), major sections use `##`, subsections use `###`, nested details use `####`. Never jump from `##` to `####`.
- **Self-Contained Sections**: Each heading section should be semantically self-contained for RAG chunking. Avoid vague headings like `## More Info` or `### Details`; use descriptive headings like `## Optical Character Recognition Pipeline`.
- **No Dangling References**: Avoid starting sections with pronouns ("This module does...", "It handles..."); start with explicit nouns ("The OCR pipeline processes...").

### Rule 3: High Information Density (Fluff Stripping)
- Strip all conversational filler, preambles, and meta-talk (e.g., *"In this section, we will explore...", "As mentioned earlier...", "Now let's take a look at..."*).
- Replace passive, wordy phrasing with crisp, active technical statements.
- Retain all technical parameters, limits, ports, dependencies, and conditions.

### Rule 4: Structured Lists with Bold Lead-Ins
- Convert dense, rambling narrative paragraphs into scannable bullet points.
- Format every bullet with an explicit **bold lead-in**:
  - Format: `- **<Concept / Component / Action>:** <Direct, factual description>`
  - Example:
    ```markdown
    - **Hybrid Search Engine:** Combines dense semantic vector similarity with sparse BM25 keyword matching for optimal recall.
    - **Local Inference:** Executes lightweight embedding models locally to preserve data privacy and avoid egress latency.
    ```

### Rule 5: Explicit Code & Data Fencing
- Never leave commands, paths, parameters, environment variables, or config values loose in plain text.
- Wrap all code, configuration files, and shell snippets in fenced code blocks with explicit language tags (e.g., ````bash````, ````python````, ````json````, ````yaml````, ````sql````).
- Structure tabular or comparative information into GitHub Flavored Markdown (GFM) tables.

### Rule 6: Absolute Fact Preservation
- **Never drop facts**: Numerical thresholds, version requirements, architectural requirements, edge cases, and constraints must remain intact.
- **Never invent facts**: If an item is not specified in the original context, do not fabricate details or assume unmentioned libraries.

---

## 3. Execution Workflow

When operating on an existing file or context snippet:

```mermaid
flowchart TD
    A[Step 1: Read Source File & Capture Facts] --> B[Step 2: Extract Entities, Numbers & Constraints]
    B --> C[Step 3: Draft Structured Markdown with Frontmatter]
    C --> D[Step 4: Fact-Preservation Verification Check]
    D --> E[Step 5: Write / Replace Target File]
```

### Step 1: Read Source File
- If the user points to an existing file (e.g., via chat, open editor, or path), read the file in its entirety using `view_file`.
- If raw text is provided directly in chat, capture the full text without truncating.

### Step 2: Extract Facts & Structure
- Catalog core technical components:
  - System goals, requirements, constraints.
  - Commands, code snippets, dependencies.
  - Numbers, metrics, SLAs, configurations.

### Step 3: Transform & Refactor
- Formulate the clean YAML frontmatter.
- Group items logically under distinct `##` and `###` headers.
- Convert sentences into structured bullet lists with bold lead-ins.
- Ensure all technical terms, code snippets, and commands are fenced or inline-code formatted.

### Step 4: Verification Checklist
Before saving or outputting, run this mental audit:
- [ ] Is YAML frontmatter present with `title`, `summary`, and `keywords`?
- [ ] Are headings strictly ordered (`#` -> `##` -> `###`) with zero skipped levels?
- [ ] Are all conversational intros and filler sentences eliminated?
- [ ] Are bullets formatted with `- **Lead-In:**`?
- [ ] Are all code snippets tagged with explicit language identifiers?
- [ ] Are 100% of the numbers, technical constraints, and requirements preserved?

### Step 5: In-Place Update or Creation
- Update the target file using `replace_file_content` or `write_to_file` (with `Overwrite: true` if rewriting the whole file).
- Present a concise summary of optimizations applied to the user.

---

## 4. Transformation Example

### Input (Raw Context)
```text
The system provides intelligent archive search using natural-language queries.
The system performs hybrid search by combining metadata, keyword, and semantic retrieval.
The system generates AI-assisted answers based on archived documents.
The system provides citation-based responses with links to supporting source documents.
The system uses Optical Character Recognition (OCR) to extract searchable text from scanned and image-based archived documents, enabling their content to be indexed, retrieved, and processed for intelligent search and AI-assisted responses. 
The system performs local AI processing to ensure secure and efficient archive retrieval.
```

### Output (Optimized Context)
````markdown
---
title: "Intelligent Archive Search Requirements"
summary: "Core system requirements for local hybrid search, OCR extraction, semantic retrieval, and citation-backed generative responses."
keywords: ["hybrid-search", "ocr", "local-ai", "semantic-search", "citation-qa"]
---

# Intelligent Archive Search Requirements

## Search & Retrieval Architecture
- **Natural Language Querying:** Interprets freeform user inquiries to retrieve relevant archival documents.
- **Hybrid Retrieval Engine:** Combines document metadata filtering, BM25/keyword indexing, and semantic vector similarity.
- **Sub-Second Retrieval:** Optimized query latency for responsive user interaction across large document stores.

## AI Generation & Grounding
- **Generative Synthesis:** Synthesizes direct answers grounded strictly on indexed archival material.
- **Citation Attribution:** Generates verifiable citation links pointing directly to supporting source passages.
- **Contextual Recommendation:** Discovers and suggests related archival documents based on the active query context.

## Document Ingestion & Optical Character Recognition
- **OCR Text Extraction:** Extracts machine-readable text from scanned PDFs and raster images for downstream indexing.
- **Searchable Index Generation:** Integrates extracted OCR text into the primary search pipeline for full-text and semantic queries.

## Security & Infrastructure
- **Local AI Processing:** Runs inference entirely on local hardware, ensuring data privacy and zero external egress.
- **Scalable Indexing:** Supports incremental index growth as document volume scales over time.
````
