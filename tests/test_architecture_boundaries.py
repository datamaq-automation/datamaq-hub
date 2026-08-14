"""Architecture boundary tests using Python AST analysis.

Enforces strict Clean Architecture and DDD purity:
1. src/domain/: 100% pure Python (stdlib + src.domain only). No 3rd party, no outer layers.
2. src/application/: Only stdlib, src.domain, src.application. Pydantic allowed ONLY in application/dtos/.
3. src/adapters/: Never imports src.infrastructure. Controllers and Presenters NEVER import fastapi or starlette.
4. src/domain/: No volatile temporal/monetary defaults hardcoded in dataclasses.
"""

import ast
import re
import sys
from pathlib import Path

SRC_DIR = Path(__file__).parent.parent / "src"

# Built-in standard library module names (Python 3.10+)
STDLIB_MODULES = set(sys.stdlib_module_names) | {
    "typing",
    "dataclasses",
    "enum",
    "abc",
    "re",
    "math",
    "datetime",
    "collections",
    "functools",
    "itertools",
    "pathlib",
    "io",
    "json",
    "uuid",
    "copy",
    "os",
    "sys",
    "warnings",
}

PERIOD_REGEX = re.compile(r"^\d{6}$")
DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _extract_imported_modules(file_path: Path) -> list[tuple[str, int]]:
    """Extracts all top-level imported module names and their line numbers from a python file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except Exception as e:
        raise RuntimeError(f"Failed to parse AST for {file_path}: {e}") from e

    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.module, node.lineno))

    return imports


def _get_python_files(relative_dir: str) -> list[Path]:
    target_dir = SRC_DIR / relative_dir
    if not target_dir.exists():
        return []
    return [
        p for p in target_dir.rglob("*.py") if p.is_file() and p.name != "__init__.py"
    ]


def test_domain_layer_strict_purity():
    """Domain layer must only depend on stdlib and src.domain."""
    domain_files = _get_python_files("domain")
    assert len(domain_files) > 0, "No domain files found"

    violations: list[str] = []

    for file_path in domain_files:
        imports = _extract_imported_modules(file_path)
        for mod, line in imports:
            root_mod = mod.split(".")[0]
            # Must be stdlib or src.domain
            if mod.startswith("src.domain"):
                continue
            if root_mod in STDLIB_MODULES:
                continue

            violations.append(
                f"[{file_path.relative_to(SRC_DIR)}:{line}] Forbidden domain import: '{mod}'"
            )

    assert not violations, (
        f"Domain layer purity violations found ({len(violations)}):\n"
        + "\n".join(violations)
    )


def test_application_layer_strict_purity():
    """Application layer must only depend on stdlib, src.domain, src.application, and pydantic (dtos only)."""
    app_files = _get_python_files("application")
    assert len(app_files) > 0, "No application files found"

    violations: list[str] = []

    for file_path in app_files:
        is_dto_file = "application/dtos" in str(file_path)
        imports = _extract_imported_modules(file_path)

        for mod, line in imports:
            root_mod = mod.split(".")[0]

            # Allowed internal imports
            if mod.startswith(("src.domain", "src.application")):
                continue

            # Pydantic is only allowed in dtos
            if root_mod == "pydantic":
                if is_dto_file:
                    continue
                violations.append(
                    f"[{file_path.relative_to(SRC_DIR)}:{line}] Pydantic is forbidden outside application/dtos/: '{mod}'"
                )
                continue

            # Standard library is allowed
            if root_mod in STDLIB_MODULES:
                continue

            violations.append(
                f"[{file_path.relative_to(SRC_DIR)}:{line}] Forbidden application import: '{mod}'"
            )

    assert not violations, (
        f"Application layer purity violations found ({len(violations)}):\n"
        + "\n".join(violations)
    )


def test_adapters_never_import_infrastructure():
    """Adapters layer must NEVER import from src.infrastructure."""
    adapter_files = _get_python_files("adapters")
    assert len(adapter_files) > 0, "No adapter files found"

    violations: list[str] = []

    for file_path in adapter_files:
        imports = _extract_imported_modules(file_path)
        for mod, line in imports:
            if mod.startswith("src.infrastructure"):
                violations.append(
                    f"[{file_path.relative_to(SRC_DIR)}:{line}] Adapters cannot import infrastructure: '{mod}'"
                )

    assert not violations, (
        f"Adapter->Infrastructure dependency violations found ({len(violations)}):\n"
        + "\n".join(violations)
    )


def test_controllers_and_presenters_web_agnosticism():
    """Controllers and Presenters in adapters MUST NOT import web frameworks (fastapi, starlette)."""
    controllers = _get_python_files("adapters/controllers")
    presenters = _get_python_files("adapters/presenters")
    targets = controllers + presenters

    violations: list[str] = []
    forbidden_frameworks = {"fastapi", "starlette"}

    for file_path in targets:
        imports = _extract_imported_modules(file_path)
        for mod, line in imports:
            root_mod = mod.split(".")[0]
            if root_mod in forbidden_frameworks:
                violations.append(
                    f"[{file_path.relative_to(SRC_DIR)}:{line}] Web framework import forbidden in adapters: '{mod}'"
                )

    assert not violations, (
        f"Web framework leak in adapters found ({len(violations)}):\n"
        + "\n".join(violations)
    )


def test_domain_dataclasses_no_volatile_defaults():
    """Domain dataclasses must not have hardcoded volatile/monetary/temporal defaults."""
    domain_files = _get_python_files("domain")
    violations: list[str] = []

    for file_path in domain_files:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                is_dataclass = any(
                    (isinstance(d, ast.Name) and d.id == "dataclass")
                    or (
                        isinstance(d, ast.Call)
                        and isinstance(d.func, ast.Name)
                        and d.func.id == "dataclass"
                    )
                    for d in node.decorator_list
                )
                if not is_dataclass:
                    continue

                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and item.value is not None:
                        field_name = (
                            item.target.id
                            if isinstance(item.target, ast.Name)
                            else "unknown"
                        )
                        if isinstance(item.value, ast.Constant):
                            val = item.value.value
                            if isinstance(val, str) and (
                                PERIOD_REGEX.match(val) or DATE_REGEX.match(val)
                            ):
                                violations.append(
                                    f"[{file_path.relative_to(SRC_DIR)}:{item.lineno}] Class '{node.name}' has volatile default '{field_name} = \"{val}\"'"
                                )
                            elif isinstance(val, (int, float)) and val > 1.0:
                                violations.append(
                                    f"[{file_path.relative_to(SRC_DIR)}:{item.lineno}] Class '{node.name}' has hardcoded numeric default '{field_name} = {val}'"
                                )

    assert not violations, (
        f"Volatile defaults in Domain Dataclasses found ({len(violations)}):\n"
        + "\n".join(violations)
    )
