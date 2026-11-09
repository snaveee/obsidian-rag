# Code Review & Government Compliance Audit Report

**Target Scope**: `[Files / Diff / Module Name]`  
**Reviewer**: Code Review Subagent (Government Security & Software Architect Persona)  
**Date**: `[YYYY-MM-DD]`  
**Overall Status**: `[APPROVED / REJECTED / APPROVED WITH CONDITIONS]`

---

## Executive Summary

| Total Files Inspected | Critical Issues | High Issues | Medium Issues | Low Issues | Compliance Score |
| :---: | :---: | :---: | :---: | :---: | :---: |
| `[Count]` | `[Count]` | `[Count]` | `[Count]` | `[Count]` | `[0-100%]` |

`[Provide a 2-3 paragraph summary of the codebase quality, key security risks identified, over-engineering observations, and readiness for enterprise/government agency deployment.]`

---

## Audit Checklist Scorecard

- [ ] **Syntax & Type Safety**: PEP 8 compliance, explicit type hints, no unresolved dead code.
- [ ] **Clean Code & Anti-Spaghetti**: Nesting level ≤ 3, SRP adherence, function length < 30 lines.
- [ ] **Pragmatic Simplicity (KISS)**: Direct implementation verified (no 50-line over-engineered abstractions for 5-line tasks).
- [ ] **AppSec & OWASP Top 10**: Zero hardcoded secrets, injection protection (SQLi/Command), safe resource handling.
- [ ] **FIPS 140-3 Cryptography**: FIPS-approved ciphers/hashes (AES-256-GCM, SHA-256), `secrets` CSPRNG used.
- [ ] **Federal Compliance (NIST SP 800-218/53)**: Audit logging present, Zero Trust boundaries enforced, PII/PHI protected.

---

## Detailed Findings & Actionable Remediations

### Finding 1: `[Title of Finding]`
- **Severity**: `[CRITICAL / HIGH / MEDIUM / LOW / INFO]`
- **Category**: `[Clean Code / Security / FIPS Cryptography / Over-Engineering / Federal Compliance]`
- **Location**: `[file_path.py:Line Number]`
- **Description**: `[Clear breakdown of why this code fails standards, referencing PEP 8, NIST, FIPS, or KISS rules.]`

#### Non-Compliant Code (Before):
```python
# [Original code snippet showing the defect]
```

#### Compliant Remediation (After):
```python
# [Corrected, clean, secure, direct implementation]
```

---

## Summary of Required Actions Before Sign-Off

1. `[Action item 1]`
2. `[Action item 2]`
3. `[Action item 3]`
