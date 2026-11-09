# Government & Enterprise Security Compliance Standards

This reference specifies federal security, cryptography, and application protection standards required for government agencies and enterprise clients.

---

## 1. NIST SP 800-218 (Secure Software Development Framework - SSDF)

All reviewed code must align with NIST SSDF tasks:
- **Protect Code from Unauthorized Access & Tampering (PO)**: Ensure secrets are never committed, dependencies are pinned, and static security analysis passes cleanly.
- **Produce Well-Secured Software (PW)**: Design software to meet security requirements, reuse validated secure components, and sanitize all input/output vectors.
- **Respond to Vulnerabilities (RV)**: Remediate all known vulnerabilities (CWEs) prior to production deployment.

---

## 2. FIPS 140-3 Cryptographic Compliance

Government agencies mandate cryptographic implementations compliant with FIPS 140-3:

### A. Prohibited Algorithms & Implementations
- ❌ **Hashes**: MD5, SHA-1 for security/integrity functions.
- ❌ **Ciphers**: DES, 3DES, RC4, Blowfish, AES in ECB mode (`CipherMode.ECB`).
- ❌ **Asymmetric Keys**: RSA keys < 2048 bits (RSA 3072+ required for high security), ECC curves not on FIPS-approved list (use P-256 / P-384).
- ❌ **Random Number Generators**: Standard `random` module (e.g. `random.randint()`, `random.choice()`) for tokens, keys, passwords, or nonce generation.

### B. Mandatory Approved Algorithms
- ✅ **Symmetric Encryption**: AES-256-GCM or AES-256-CBC with HMAC-SHA256 authenticated encryption.
- ✅ **Hashing**: SHA-256, SHA-384, SHA-512, SHA3-256.
- ✅ **Randomness**: `secrets` module (`secrets.token_hex()`, `secrets.token_urlsafe()`, `secrets.SystemRandom()`).

```python
# NON-COMPLIANT (FIPS Violation & Weak RNG)
import hashlib
import random

def generate_session_token(username: str) -> str:
    raw = f"{username}:{random.randint(1000, 9999)}"
    return hashlib.md5(raw.encode()).hexdigest()  # MD5 is broken & random is predictable!

# COMPLIANT (FIPS 140-3 Compliant)
import secrets

def generate_session_token(username: str) -> str:
    return secrets.token_urlsafe(32)  # Uses OS-level secure CSPRNG
```

---

## 3. Zero Trust Architecture & Access Controls (NIST SP 800-53 AC / IA)

- **Implicit Distrust**: Validate all inputs at every API boundary. Never assume internal callers or microservices are trusted.
- **Principle of Least Privilege**: Verify authorization (`RBAC` or `ABAC`) explicitly before executing privileged actions.
- **Session Management**: Session tokens must expire, support revoking, and be bound to secure HTTP-only cookies (`SameSite=Strict`).

---

## 4. Application Security (OWASP Top 10 & CWE Top 25)

### A. Injection Vulnerabilities (CWE-89 SQLi, CWE-78 Command Injection)
- **SQL Injection**: Always use parameterized queries (ORM or prepared statements). Never concatenate SQL strings.
- **Command Injection**: Avoid `os.system()` or `subprocess.Popen(shell=True)`. Pass argument vectors as lists (`subprocess.run(["ls", "-l", path], check=True)`).

```python
# NON-COMPLIANT (Command Injection Risk)
import subprocess

def list_user_dir(user_input: str):
    subprocess.run(f"ls -l {user_input}", shell=True)  # Injection vulnerability!

# COMPLIANT
import subprocess
from pathlib import Path

def list_user_dir(user_input: str):
    safe_path = Path(user_input).resolve()
    subprocess.run(["ls", "-l", str(safe_path)], check=True)
```

### B. Secret Management & Hardcoded Credentials (CWE-798)
- Zero tolerance for embedded passwords, API tokens, RSA private keys, or AWS keys in source code or configuration files.
- Load secrets exclusively from validated environment variables or secret management services (AWS Secrets Manager, HashiCorp Vault).

### C. Log Injection & Audit Trail Integrity (NIST SP 800-53 AU-2 / AU-12 & CWE-117)
- **Log Injection Prevention**: Newlines (`\n`, `\r`) in user input can forge log entries. All logged inputs must be sanitized.
- **Audit Field Requirements**: Log entries must include ISO 8601 UTC timestamp, Correlation/Trace ID, Event Type, Actor ID, and Outcome (Success/Failure).
- **PII/PHI Protection**: Never log passwords, SSNs, credit card numbers, or personally identifiable information.

```python
# NON-COMPLIANT (Log Injection Risk & Unstructured Log)
def log_user_action(user_input: str):
    print(f"User performed action: {user_input}")  # Can forge log lines via \n!

# COMPLIANT (Sanitized & Structured Audit Log)
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("audit")

def log_user_action(actor_id: str, action: str, trace_id: str):
    sanitized_action = action.replace("\n", "_").replace("\r", "_")
    audit_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "actor_id": actor_id,
        "event": "USER_ACTION",
        "action": sanitized_action,
        "status": "SUCCESS"
    }
    logger.info(json.dumps(audit_entry))
```

### D. Path Traversal Prevention (CWE-22)
- Enforce strict path resolution and boundary checking (`pathlib.Path.resolve()`) to ensure requested files remain within intended directories.
