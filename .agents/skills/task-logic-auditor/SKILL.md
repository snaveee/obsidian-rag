---
name: task-logic-auditor
description: >-
  Audit Pull Requests (PRs), tasks, and implementation plans for logical coherence,
  real-world usability, UX lifecycle edge cases, data sanity, and architectural sense.
  Goes beyond literal issue checklists to catch design flaws, deduplication needs, empty
  state issues, infinite loop risks, and practical friction. Triggers: "does this make sense",
  "audit task logic", "check logical sanity", "is this logically sound", "task logic check",
  "sanity check plan", "logic review".
---

# Task Logic Auditor (`task-logic-auditor`)

This skill equips the agent to act as a **Principal Product Architect & Systems Logician**. While `pr-issue-verifier` verifies literal requirement completion and `code-review` checks code syntax and security, this skill evaluates whether the task or PR **actually makes sense logically, operationally, and experientially in the real world**.

---

## 1. The 5-Dimension Logical Audit Framework

Whenever a task, issue, plan, or PR is evaluated, assess it through these five logical dimensions:

```mermaid
flowchart TD
    A[Proposed Task / PR] --> B1[1. Prerequisite & Dependency Sense]
    A --> B2[2. UX & State Lifecycle Sense]
    A --> B3[3. Data Sanity & Deduplication]
    A --> B4[4. Architectural Coherence]
    A --> B5[5. Value vs. Operational Friction]
    B1 --> C[Logical Synthesis & Edge-Case Traps]
    B2 --> C
    B3 --> C
    B4 --> C
    B5 --> C
    C --> D[Logical Verdict: SOUND, ADJUSTMENTS NEEDED, or ILLOGICAL]
```

### Dimension 1: Prerequisite & Dependency Sense
- Are foundational tables, schemas, backend routes, or models actually ready, or is this task attempting to build downstream UI on nonexistent foundations?
- Does this task assume state (e.g., an authenticated user, an initialized collection) that might not exist at runtime?

### Dimension 2: UX & State Lifecycle Sense
- **The Empty State Trap:** What happens when there is zero data (e.g., brand-new user with zero history)? Does the UI look broken, or does it provide a clean, purposeful empty state?
- **The Rerun / Infinite Loop Trap:** (Especially in reactive frameworks like Streamlit or React) Does selecting or clicking an item trigger repeated reruns or reload loops?
- **The Click-Action Trap & Automated UI Test Requirement:** When an action happens, is the user's focus preserved? Is feedback clear, or does the screen abruptly flash? **Crucial:** Never declare UI changes or click handlers complete based on code inspection alone. Every interactive UI workflow (e.g., clicking a button, updating widget inputs, trigger pipelines) must be verified via automated headless UI tests (e.g., Streamlit `AppTest.from_file(...)`) simulating the full click and state transition cycle.
- **The Order-of-Declaration Trap:** In script-run UI frameworks like Streamlit, are helper functions defined BEFORE any UI container/sidebar calls them? Does any conditional branch reference undeclared functions or variables?

### Dimension 3: Data Sanity & Deduplication
- **The Repetition Trap:** If a user performs the same action 5 times consecutively (e.g. searching the same word 5 times), does the system create 5 redundant duplicate items or intelligently deduplicate them?
- **The Boundary / Limit Trap:** What prevents the UI or database from being overwhelmed if there are 1,000 items? Are sensible limits, truncation, or pagination enforced?

### Dimension 4: Architectural Coherence
- Does the implementation pattern match existing established patterns in the codebase?
- Are errors handled gracefully (e.g. fail-safe non-blocking telemetry vs crashing the main user workflow)?
- Does it maintain clean isolation (e.g., User A never sees User B's private data)?

### Dimension 5: Value vs. Operational Friction
- Does this feature solve a genuine user problem, or does it create confusing visual clutter?
- Can an operator understand how to use this feature immediately without reading instructions?

---

## 2. Standard Output Schema

When conducting a task logic audit, report findings using this structured template:

```markdown
# Task Logic & Sanity Audit Report: [Task / PR Name]

## 1. Executive Logical Verdict
- **Verdict:** [LOGICALLY SOUND / ADJUSTMENTS NEEDED / ILLOGICAL / BLOCKED]
- **Core Sanity Score:** [e.g., 9/10]
- **Summary:** [1-2 sentences capturing whether this task makes sense in the real world]

## 2. Five-Dimension Evaluation

| Dimension | Status | Observation & Logical Check |
| :--- | :--- | :--- |
| **1. Prerequisites & Dependencies** | `PASS` / `CONCERN` | [Are foundations solid?] |
| **2. UX & State Lifecycle** | `PASS` / `CONCERN` | [Empty states, reruns, interactions] |
| **3. Data Sanity & Deduplication**| `PASS` / `CONCERN` | [Consecutive duplicates, limits] |
| **4. Architectural Coherence** | `PASS` / `CONCERN` | [Consistency with codebase standards] |
| **5. Value vs. Operational Friction**| `PASS` / `CONCERN`| [Real-world user value vs clutter] |

## 3. Identified Edge Cases & Logical Traps
- **[Edge Case 1]:** [What could go wrong in actual usage]
  - *Logical Fix:* [How the plan or code should accommodate this]
- **[Edge Case 2]:** [What could go wrong in actual usage]
  - *Logical Fix:* [How the plan or code should accommodate this]

## 4. Recommended Logical Adjustments (Before / During Implementation)
1. [Concrete improvement 1]
2. [Concrete improvement 2]
```

---

## 3. Rules of Engagement
1. **Never Just "Rubber Stamp":** Even if an issue author wrote a simple description, question edge cases and missing lifecycle states.
2. **Pragmatic & Constructive:** Do not block progress with pedantic over-engineering; recommend clean, 2-line standard Python/Streamlit solutions that prevent real-world glitches.
3. **Protect User & Operator Privacy:** Always verify multi-user boundaries and access filters.

