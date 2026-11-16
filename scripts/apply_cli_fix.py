"""Add a stable installed entry point without replacing existing settings."""
from pathlib import Path
import tomllib

root = Path(__file__).resolve().parents[1]
config = root / "pyproject.toml"
source = root / "src" / "solar_event_ai" / "__init__.py"
if not config.is_file() or not source.is_file():
    raise SystemExit("Expected pyproject.toml and src/solar_event_ai/__init__.py in this repository")

original = config.read_text()
parsed = tomllib.loads(original)
scripts = parsed.get("project", {}).get("scripts", {})
expected = "solar_event_ai.cli:main"
if scripts.get("solar-ai") == expected:
    print("Entry point already configured.")
    raise SystemExit(0)
if "solar-ai" in scripts:
    raise SystemExit(f"Existing solar-ai entry point needs review: {scripts['solar-ai']!r}")

section = "[project.scripts]"
if section in original:
    updated = original.replace(section, f'{section}\nsolar-ai = "{expected}"', 1)
else:
    updated = original.rstrip() + f'\n\n{section}\nsolar-ai = "{expected}"\n'

verified = tomllib.loads(updated)
assert verified["project"]["scripts"]["solar-ai"] == expected
backup = config.with_name("pyproject.toml.before-cli.bak")
if not backup.exists():
    backup.write_text(original)
config.write_text(updated)
print("Entry point installed in pyproject.toml.")
print("Backup:", backup.name)
