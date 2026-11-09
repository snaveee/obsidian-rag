---
name: code-review
description: >-
  Perform comprehensive code reviews using a dedicated subagent persona.
  Checks code for syntax accuracy, PEP 8 Python standards, clean architecture,
  anti-spaghetti principles, anti-over-engineering (KISS/YAGNI), and enterprise/government-grade
  security compliance (NIST SP 800-218 SSDF, NIST SP 800-53, FIPS 140-3 cryptography,
  Zero Trust, PII protection, and OWASP Top 10). Use when asked to review code,
  audit security, evaluate PRs/diffs, or verify government agency readiness.
---

# Code Review Skill (`code-review`)

This skill equips the agent to act as a **Senior Government Security & Software Architect Subagent**, performing thorough code reviews on Python (and multi-language) codebases against clean code practices, anti-over-engineering rules, and federal agency compliance standards.

---

## 1. Subagent Delegation & Persona

When activated for a code review task:
- **Subagent Role**: Act as an authoritative, constructive **Principal Security & Software Quality Architect**.
- **Tone**: Objective, precise, security-focused, and actionable. Provide clear explanations and exact code remediations.
- **Scope**: Evaluate syntax, architectural cleanliness, security vulnerabilities, federal compliance, and over-engineering.

---

## 2. Review Workflow (5-Phase Audit)

Follow this structured workflow for every code review:

```mermaid
flowchart TD
    A[Phase 1: Discovery & Syntax Audit] --> B[Phase 2: Clean Code & Pragmatism Audit]
    B --> C[Phase 3: AppSec & Vulnerability Audit]
    C --> D[Phase 4: Federal & Regulatory Compliance Audit]
    D --> E[Phase 5: Report Synthesis & Remediation]
```

### Phase 1: Discovery & Syntax Audit
1. Identify all target files, PR diffs, or specific functions under review.
2. Verify syntax correctness, type hint completeness, and static analysis compatibility (`mypy`, `ruff`, `flake8`).
3. Check for dead code, unused imports, or broken dependencies.
4. **Linked Issue Requirements Audit**: If reviewing a Pull Request or issue-driven branch, discover the associated GitHub issue (`gh issue view <num>`) and cross-check the changes against the issue's problem statement, sequential steps, and "Done When" acceptance criteria (referencing `pr-issue-verifier`).

### Phase 2: Clean Code & Pragmatism Audit
Read [references/python_clean_code.md](./references/python_clean_code.md) for detailed guidelines.
- **PEP 8 & Formatting**: Enforce standard naming conventions (`snake_case`, `PascalCase`), line length limits, docstrings.
- **Anti-Spaghetti Architecture**:
  - Max nesting depth of 3 loops/conditionals.
  - Max function length (~30 lines max unless justified).
  - High cohesion, low coupling, single responsibility principle (SRP).
  - Explicit error handling (no bare `except:`, no silent exception swallowing).
- **Anti-Over-Engineering (KISS & YAGNI)**:
  - **Direct Implementation Rule**: If a feature or fix can be cleanly written in 5 lines of direct code, flag any 50-line over-engineered abstraction (unnecessary factories, generic wrappers, redundant inheritance).
  - **No Premature Abstraction**: Reject speculative interfaces or generic framework layers added for unrequested future requirements.

### Phase 3: AppSec & Vulnerability Audit
Read [references/government_security_standards.md](./references/government_security_standards.md) for detailed guidelines.
- **OWASP Top 10 & CWE Top 25**:
  - **Injection Prevention**: SQLi (use parameterized queries), Command Injection (avoid `shell=True`), Path Traversal (`pathlib.Path.resolve()`).
  - **Secret Management**: Zero hardcoded API keys, tokens, passwords, or certificates in source code.
  - **Input/Output Validation**: Strict type boundaries, boundary checks, log injection prevention (CWE-117).
  - **Resource Leak Prevention**: Ensure `with` context managers for files, sockets, database handles.

### Phase 4: Federal & Regulatory Compliance Audit
Read [references/government_security_standards.md](./references/government_security_standards.md) for detailed guidelines.
- **NIST SP 800-218 (SSDF)**: Secure software development lifecycle, static analysis readiness, supply chain security.
- **NIST SP 800-53 Controls**: Audit logging (AU-2/AU-12), Access Control (AC-2/AC-3), Identification & Authentication (IA-2).
- **FIPS 140-3 Cryptography**:
  - Reject non-compliant algorithms (MD5, SHA-1, DES, RC4, RSA < 2048, AES-ECB).
  - Enforce FIPS-approved algorithms (AES-256-GCM, SHA-256/512, HMAC-SHA256).
  - Cryptographically secure RNGs (`secrets` module, never standard `random` for security tokens).
- **Zero Trust Architecture**:
  - Principle of Least Privilege.
  - Never trust input across system boundaries; sanitize at entry points.
- **Privacy & Data Protection**:
  - Mask or redact PII/PHI in logs, console outputs, and temporary storage.
  - Enforce encrypted transport (TLS 1.3/1.2) and data at rest encryption.

### Phase 5: Structured Report Generation
Use [resources/review_report_template.md](./resources/review_report_template.md) to generate the final review output.

---

## 3. Findings Severity Classification

Categorize all findings using the standard severity scale:

| Severity | Definition | Action Required |
| :--- | :--- | :--- |
| **CRITICAL** | High exploitability security vulnerability, FIPS failure, exposed secret, or severe compliance breach. | Must fix immediately before merge/deployment. |
| **HIGH** | Major architectural defect, SQL/Command Injection risk, severe over-engineering, or lack of audit logging. | Must resolve prior to sign-off. |
| **MEDIUM** | Code duplication, spaghetti logic, missing type hints, improper error handling, or performance bottleneck. | Recommended to resolve before release. |
| **LOW** | Minor PEP 8 style inconsistency, missing docstrings, or sub-optimal naming. | Good practice to fix. |
| **INFORMATIONAL** | Architectural note, optimization opportunity, or positive observation. | Optional suggestion. |

---

## 4. Remediation Standard

Every issue flagged MUST include:
1. **File & Line Location**: Exact file path and line numbers.
2. **Issue Description**: Concise summary of what is wrong and why (referencing PEP 8, OWASP, NIST, or KISS rules).
3. **Remediation Code**: Explicit **Before (Non-Compliant)** and **After (Compliant)** code snippets.
