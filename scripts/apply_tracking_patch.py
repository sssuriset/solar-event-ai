"""Safely register tracking with the existing solar-ai CLI.

Does not overwrite science/data files. Refuses unfamiliar CLI structure.
"""
import ast
from pathlib import Path

root = Path(__file__).resolve().parents[1]
cli = root / "src/solar_event_ai/cli.py"
if not cli.exists():
    raise SystemExit("Expected src/solar_event_ai/cli.py. No changes made.")
old = cli.read_text()
if 'subcommands.add_parser("track"' in old:
    print("Tracking command already registered; nothing changed.")
    raise SystemExit(0)
markers = [
    'from .iris_sji import IRISSJI\n',
    '    return parser\n',
    '    raise ValueError(f"Unknown command: {args.command}")\n',
]
if any(old.count(marker) != 1 for marker in markers):
    raise SystemExit("CLI differs from expected structure; no files modified. Please inspect cli.py.")
new = old.replace(markers[0], markers[0] + 'from .tracking import track_catalog\n')
new = new.replace(markers[1],
    '    track = subcommands.add_parser("track", help="Link candidate regions into provisional tracks")\n'
    '    track.add_argument("--catalog", required=True, type=Path, help="Raw or Phase-2 QC candidate CSV")\n'
    '    track.add_argument("--output", type=Path, default=Path("results"))\n'
    '    track.add_argument("--max-distance", type=float, default=7.0, help="Association gate in pixels")\n'
    '    track.add_argument("--max-gap-frames", type=int, default=2)\n'
    '    track.add_argument("--max-gap-seconds", type=float, default=90.0)\n'
    '    track.add_argument("--min-detections", type=int, default=2)\n'
    '    track.add_argument("--ambiguity-margin", type=float, default=1.5)\n'
    + markers[1]
)
new = new.replace(markers[2], '    if args.command == "track":\n        return track_catalog(args)\n' + markers[2])
ast.parse(new)
backup = cli.with_name("cli.py.before-tracking.bak")
if not backup.exists():
    backup.write_text(old)
cli.write_text(new)
print("Added 'solar-ai track' CLI command.")
print("Backup:", backup)
