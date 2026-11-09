# Python Clean Code & Architectural Guidelines

This reference defines the coding standards, architectural principles, and pragmatism rules enforced during code reviews.

---

## 1. Python Syntax & PEP 8 Standards

- **Naming Conventions**:
  - `snake_case`: Module names, variables, functions, methods, attributes.
  - `PascalCase`: Classes, exception classes, type aliases.
  - `UPPER_CASE`: Constants defined at module level.
- **Type Annotations**:
  - Use explicit type hints for function arguments and return types (`typing` / Python 3.9+ built-in types `list[str]`, `dict[str, Any]`, `Optional[int]`).
  - Code must pass static type checkers (`mypy`) without unhandled implicit `Any` conversions.
- **Docstrings & Comments**:
  - Google style or Sphinx style docstrings for all public modules, classes, and functions.
  - Explain *why* code exists, not *what* self-explanatory code does. Remove commented-out dead code.

---

## 2. Anti-Spaghetti Code Rules

Spaghetti code creates brittle, unmaintainable software. The reviewer subagent MUST flag and reject the following anti-patterns:

### A. Arrow Anti-Pattern (Deep Nesting)
- **Rule**: Code must not exceed **3 levels of indentation/nesting**.
- **Fix**: Use guard clauses, early returns, and extract sub-functions.

```python
# NON-COMPLIANT (Deeply Nested Spaghetti)
def process_user_data(data):
    if data is not None:
        if "user" in data:
            if data["user"].get("is_active"):
                if data["user"].get("role") == "admin":
                    return execute_admin_task(data)

# COMPLIANT (Guard Clauses / Clean Flow)
def process_user_data(data: dict | None) -> bool:
    if not data or "user" not in data:
        return False
    user = data["user"]
    if not user.get("is_active") or user.get("role") != "admin":
        return False
    return execute_admin_task(data)
```

### B. Excessive Function Length & God Objects
- **Rule**: Functions should be under **30 lines** of logic. Classes should adhere to the **Single Responsibility Principle (SRP)** and avoid becoming "God Objects" (>300 lines managing multiple unrelated domains).
- **Fix**: Decompose complex workflows into modular, single-purpose helper functions or domain modules.

### C. Silent Exception Swallowing
- **Rule**: Never use bare `except:` or `except Exception: pass`.
- **Fix**: Catch specific exceptions, log structured diagnostic context, and re-raise or return explicit error results.

```python
# NON-COMPLIANT
try:
    save_to_database(record)
except:
    pass  # Silently hides database connection failures and data loss!

# COMPLIANT
try:
    save_to_database(record)
except DatabaseConnectionError as err:
    logger.error("Failed to persist record", extra={"record_id": record.id, "error": str(err)})
    raise
```

---

## 3. Anti-Over-Engineering & Pragmatic Simplicity (KISS & YAGNI)

Over-engineered code is as dangerous as spaghetti code—it increases cognitive load, hides bugs in abstraction layers, and slows down development.

### A. The Direct Implementation Rule (5 vs 50 Lines)
- **Rule**: If a feature, fix, or logic block can be implemented cleanly and directly in **5 lines of standard Python**, reject any 50-line over-engineered abstraction (e.g. custom factory interfaces, generic base classes, multi-layered wrappers, or speculative configuration classes).
- **Motto**: *Simple is better than complex. Direct is better than indirect.*

```python
# NON-COMPLIANT (50-Line Over-Engineered Abstract Factory Boilerplate)
class IStringFormatter(ABC):
    @abstractmethod
    def format(self, text: str) -> str: pass

class UpperCaseFormatter(IStringFormatter):
    def format(self, text: str) -> str:
        return text.upper()

class FormatterFactory:
    _formatters = {"upper": UpperCaseFormatter}
    @classmethod
    def get_formatter(cls, fmt_type: str) -> IStringFormatter:
        return cls._formatters[fmt_type]()

# ... calling code ...
formatter = FormatterFactory.get_formatter("upper")
result = formatter.format(raw_input)

# COMPLIANT (Direct, Clean 2-Line Implementation)
result = raw_input.upper()
```

### B. Avoid Premature Abstraction (YAGNI - You Aren't Gonna Need It)
- Do NOT introduce generic base classes, plugin interfaces, or abstract factories unless there are at least **3 existing, distinct implementations** actively in production.
- Do NOT write speculative code for hypothetical future requirements.

### C. Standard Library First
- Prefer Python standard library modules (`pathlib`, `json`, `dataclasses`, `secrets`, `functools`, `itertools`) over heavy custom helper functions or unnecessary third-party abstractions.
