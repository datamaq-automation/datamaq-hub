"""Test unitario obligatorio para garantizar inmutabilidad de paquetes."""

from pathlib import Path


def test_all_init_files_are_strictly_empty() -> None:
    """Verifica que todos los archivos __init__.py en src/ y tests/ estén 100% vacíos (0 bytes)."""
    root_dir = Path(__file__).resolve().parent.parent
    src_dir = root_dir / "src"
    tests_dir = root_dir / "tests"

    init_files = list(src_dir.rglob("__init__.py")) + list(
        tests_dir.rglob("__init__.py")
    )
    assert len(init_files) > 0, f"No se encontraron archivos __init__.py en {src_dir}"

    non_empty_inits: list[str] = []
    for init_file in init_files:
        if init_file.stat().st_size != 0:
            content = init_file.read_text(encoding="utf-8").strip()
            if content:
                non_empty_inits.append(
                    f"- {init_file.relative_to(root_dir)} ({init_file.stat().st_size} bytes)"
                )

    assert not non_empty_inits, (
        "Se encontraron archivos __init__.py que NO están vacíos:\n"
        + "\n".join(non_empty_inits)
    )
