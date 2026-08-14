#!/usr/bin/env python3
"""Deterministic AST Architecture and DDD Purity Guard.

Execution time: < 30ms. Zero third-party dependencies.
Checks:
1. Clean Architecture Layer Dependency Rules.
2. Web Framework Decoupling in Domain, Application, and Adapters (Controllers/Presenters).
3. DDD Purity: Ban on volatile monetary/temporal defaults in Domain Dataclasses.
"""

from __future__ import annotations

import ast
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"

# ANSI Colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

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

FORBIDDEN_WEB_FRAMEWORKS = {"fastapi", "starlette", "flask", "django", "litestar"}
PERIOD_REGEX = re.compile(r"^\d{6}$")  # e.g., '202608'
DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class ArchitectureViolation:
    category: str
    file_path: Path
    line: int
    summary: str
    rationale: str
    refactoring_guide: str

    def format_pedagogical_message(self) -> str:
        rel_path = self.file_path.relative_to(ROOT_DIR)
        return (
            f"{RED}{BOLD}🛑 [VIOLACIÓN ARQUITECTÓNICA] {self.category}{RESET}\n"
            f"   {CYAN}📍 Ubicación:{RESET} {rel_path}:{self.line}\n"
            f"   {YELLOW}🔍 Detalle:{RESET}   {self.summary}\n"
            f"   {DIM}🧠 Principio:{RESET} {self.rationale}\n"
            f"   {GREEN}💡 Solución:{RESET}  {self.refactoring_guide}\n"
        )


class ArchitectureChecker:
    def __init__(self, src_dir: Path) -> None:
        self.src_dir = src_dir
        self.violations: list[ArchitectureViolation] = []

    def check_all(self) -> list[ArchitectureViolation]:
        py_files = [
            p
            for p in self.src_dir.rglob("*.py")
            if p.is_file() and p.name != "__init__.py"
        ]
        for file_path in py_files:
            try:
                tree = ast.parse(
                    file_path.read_text(encoding="utf-8"), filename=str(file_path)
                )
            except (SyntaxError, UnicodeDecodeError, OSError) as e:
                self.violations.append(
                    ArchitectureViolation(
                        category="Syntax/Parse Error",
                        file_path=file_path,
                        line=1,
                        summary=f"No se pudo parsear AST: {e}",
                        rationale="El código debe ser sintácticamente válido para ser analizado.",
                        refactoring_guide="Corrija los errores de sintaxis en el archivo.",
                    )
                )
                continue

            self._check_imports(file_path, tree)
            self._check_domain_dataclass_defaults(file_path, tree)

        return self.violations

    def _check_imports(self, file_path: Path, tree: ast.AST) -> None:
        rel_path = file_path.relative_to(self.src_dir).as_posix()
        is_domain = rel_path.startswith("domain/")
        is_app = rel_path.startswith("application/")
        is_dto = rel_path.startswith("application/dtos/")
        is_adapter = rel_path.startswith("adapters/")
        is_controller_or_presenter = rel_path.startswith(
            ("adapters/controllers/", "adapters/presenters/")
        )

        for node in ast.walk(tree):
            imports: list[tuple[str, int]] = []
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append((node.module, node.lineno))

            for mod, lineno in imports:
                root_mod = mod.split(".")[0]

                # 1. Regla: Pureza del Dominio (Solo stdlib + src.domain)
                if (
                    is_domain
                    and not mod.startswith("src.domain")
                    and root_mod not in STDLIB_MODULES
                ):
                    self.violations.append(
                        ArchitectureViolation(
                            category="Domain Layer Impurity",
                            file_path=file_path,
                            line=lineno,
                            summary=f"Import prohibido en Dominio: '{mod}'",
                            rationale="El Dominio debe ser 100% puro (stdlib + src.domain). No puede depender de frameworks ni capas externas.",
                            refactoring_guide="Mueva la lógica o DTO a la capa de Aplicación/Infraestructura o use un Puerto (Interface/Protocol).",
                        )
                    )

                # 2. Regla: Aplicación (Solo stdlib, src.domain, src.application, pydantic solo en dtos/)
                if is_app:
                    if root_mod == "pydantic" and not is_dto:
                        self.violations.append(
                            ArchitectureViolation(
                                category="Pydantic Leak in Application",
                                file_path=file_path,
                                line=lineno,
                                summary=f"Pydantic importado fuera de application/dtos/: '{mod}'",
                                rationale="Pydantic es un detalle de serialización/validación de entrada y solo se permite en DTOs.",
                                refactoring_guide="Mueva el esquema Pydantic a src/application/dtos/ y mapeelo a Entidades puras en Use Cases.",
                            )
                        )
                    elif (
                        not mod.startswith(("src.domain", "src.application"))
                        and root_mod not in STDLIB_MODULES
                        and root_mod != "pydantic"
                    ):
                        self.violations.append(
                            ArchitectureViolation(
                                category="Application Layer Impurity",
                                file_path=file_path,
                                line=lineno,
                                summary=f"Import prohibido en Aplicación: '{mod}'",
                                rationale="La capa de Aplicación solo puede orquestar casos de uso usando Dominio y sus propios DTOs/Mappers.",
                                refactoring_guide="Defina un puerto en domain/ports.py e impleméntelo en adapters/gateways/.",
                            )
                        )

                # 3. Regla: Adapters nunca importa Infrastructure
                if is_adapter and mod.startswith("src.infrastructure"):
                    self.violations.append(
                        ArchitectureViolation(
                            category="Inversion of Dependency Violation",
                            file_path=file_path,
                            line=lineno,
                            summary=f"Adapters importa Infrastructure: '{mod}'",
                            rationale="Adapters no puede conocer detalles de infraestructura (servidores, routers, bases de datos concretas).",
                            refactoring_guide="Inyecte la dependencia mediante interfaces en controllers/dependencies.py o invierta el control.",
                        )
                    )

                # 4. Regla: Controladores y Presenters agnósticos de Frameworks Web
                if is_controller_or_presenter and root_mod in FORBIDDEN_WEB_FRAMEWORKS:
                    self.violations.append(
                        ArchitectureViolation(
                            category="Web Framework Coupling in Adapters",
                            file_path=file_path,
                            line=lineno,
                            summary=f"Framework web ('{mod}') importado en Controller/Presenter",
                            rationale="Controllers y Presenters deben ser clases puras de Python agnósticas del protocolo de transporte (HTTP, CLI, Worker).",
                            refactoring_guide="Mueva las rutas de FastAPI (@router.post, Depends, UploadFile) a src/infrastructure/fastapi/routes/.",
                        )
                    )

    def _check_domain_dataclass_defaults(self, file_path: Path, tree: ast.AST) -> None:
        rel_path = file_path.relative_to(self.src_dir).as_posix()
        if not rel_path.startswith("domain/"):
            return

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
                            # Detectar strings temporales volátiles (ej. "202608", "2026-08-14")
                            if isinstance(val, str) and (
                                PERIOD_REGEX.match(val) or DATE_REGEX.match(val)
                            ):
                                self.violations.append(
                                    ArchitectureViolation(
                                        category="Volatile Temporal Default in Domain Dataclass",
                                        file_path=file_path,
                                        line=item.lineno,
                                        summary=f"Clase '{node.name}', campo '{field_name}' tiene default temporal hardcodeado: '{val}'",
                                        rationale="Los períodos o fechas fijas no deben ser defaults estáticos del modelo de dominio.",
                                        refactoring_guide=f"Haga '{field_name}: str' un campo requerido o inyéctelo desde el Use Case / Parámetros de liquidación.",
                                    )
                                )
                            # Detectar números mágicos / coeficientes / valores monetarios (> 1.0)
                            elif isinstance(val, (int, float)) and val > 1.0:
                                self.violations.append(
                                    ArchitectureViolation(
                                        category="Magic Number / Hardcoded Business Default in Domain",
                                        file_path=file_path,
                                        line=item.lineno,
                                        summary=f"Clase '{node.name}', campo '{field_name}' tiene default numérico de negocio: {val}",
                                        rationale="Los montos monetarios o coeficientes variables deben pasarse como argumentos al instanciar, no como defaults en el esquema de dominio.",
                                        refactoring_guide=f"Defina '{field_name}: float' sin valor default, o cree un objeto de configuración/paritaria que encapsule los valores vigentes.",
                                    )
                                )


def main() -> int:
    start_time = time.perf_counter()
    checker = ArchitectureChecker(SRC_DIR)
    violations = checker.check_all()
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    if not violations:
        print(
            f"{GREEN}{BOLD}🏛️  [Architecture Guard] Todas las capas y reglas DDD verificadas con éxito en {elapsed_ms:.1f}ms (0 violaciones).{RESET}"
        )
        return 0

    print(
        f"\n{RED}{BOLD}❌ [Architecture Guard] Se encontraron {len(violations)} violaciones arquitectónicas ({elapsed_ms:.1f}ms):{RESET}\n"
    )
    for v in violations:
        print(v.format_pedagogical_message())

    return 1


if __name__ == "__main__":
    sys.exit(main())
