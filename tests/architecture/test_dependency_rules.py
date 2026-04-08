import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "pm_bot"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def test_domain_stays_free_of_io_framework_imports() -> None:
    forbidden = {"fastapi", "httpx", "jinja2", "sqlite3", "pydantic_settings"}
    for path in (SRC_ROOT / "domain").rglob("*.py"):
        imported = _imported_modules(path)
        message = f"{path} imports forbidden modules: {imported & forbidden}"
        assert imported.isdisjoint(forbidden), message


def test_strategy_layer_does_not_import_integrations_clients() -> None:
    strategy_root = SRC_ROOT / "strategy"
    if not strategy_root.exists():
        return

    for path in strategy_root.rglob("*.py"):
        imported = _imported_modules(path)
        assert "integrations" not in imported, f"{path} must not import integrations directly"
