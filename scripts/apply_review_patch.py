"""Safely add the temporal review subcommand to the known v0.1 CLI."""
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
cli = root / "src/solar_event_ai/cli.py"
original = cli.read_text()
if "review_candidates(args)" in original:
    print("Review command already configured.")
    raise SystemExit(0)

import_marker = "from .iris_sji import IRISSJI\n"
parser_marker = "    return parser\n"
main_marker = "    raise ValueError(f\"Unknown command: {args.command}\")\n"
for marker in (import_marker, parser_marker, main_marker):
    if original.count(marker) != 1:
        raise SystemExit("CLI layout differs from expected; no files changed. Please send cli.py for review.")

updated = original.replace(import_marker, import_marker + "from .review import review_candidates\n")
updated = updated.replace(
    parser_marker,
    '    review = subcommands.add_parser("review", help="Compare detections across frames")\n'
    '    review.add_argument("file", type=Path, help="Same original FITS cube used for scanning")\n'
    '    review.add_argument("--catalog", required=True, type=Path, help="CSV from solar-ai scan")\n'
    '    review.add_argument("--max-examples", type=int, default=6)\n'
    '    review.add_argument("--offset-frames", type=int, default=3)\n'
    '    review.add_argument("--crop-radius", type=int, default=25)\n'
    '    review.add_argument("--edge-margin", type=int, default=16)\n'
    '    review.add_argument("--output", type=Path, default=Path("results"))\n'
    + parser_marker
)
updated = updated.replace(main_marker, '    if args.command == "review":\n        return review_candidates(args)\n' + main_marker)
ast.parse(updated)
backup = cli.with_name("cli.py.before-review.bak")
if not backup.exists():
    backup.write_text(original)
cli.write_text(updated)
print("Review command added to cli.py")
print("Backup:", backup)
