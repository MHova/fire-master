"""Convert a Markdown file to a styled HTML report in the FIREMaster dark theme.

Handles pandoc's quirks with pipe tables and list spacing:
- Inserts blank lines before list blocks so pandoc recognizes them as <ul>/<li>
- Converts 2-space sub-items to 4-space for proper nesting
- Uses +pipe_tables extension for markdown table support
- Wraps output in the FIREMaster dark theme (Inter + JetBrains Mono fonts)

Usage:
    cd backend && uv run python ../scripts/md_to_html.py ../PATH.md ../reports/PATH.html
    cd backend && uv run python ../scripts/md_to_html.py ../PLAN_Retirement_Realignment.md ../reports/PLAN_Retirement_Realignment.html

Requirements:
    pandoc (brew install pandoc)
"""

import subprocess
import sys
from pathlib import Path

HTML_HEADER = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #0a0a0f; color: #e8e8f0; font-family: 'Inter', sans-serif; padding: 40px; min-height: 100vh; line-height: 1.7; font-size: 15px; }}
  .container {{ max-width: 1100px; margin: 0 auto; }}
  h1 {{ font-size: 32px; font-weight: 700; letter-spacing: -0.5px; margin: 32px 0 8px; color: #e8e8f0; }}
  h2 {{ font-size: 22px; font-weight: 700; color: #4d8eff; margin: 40px 0 16px; padding-bottom: 8px; border-bottom: 2px solid rgba(77,142,255,0.2); }}
  h3 {{ font-size: 17px; font-weight: 600; color: #00d4aa; margin: 28px 0 12px; }}
  h4 {{ font-size: 15px; font-weight: 600; color: #ffc04d; margin: 20px 0 8px; }}
  p {{ color: #c8c8d8; margin: 8px 0; }}
  strong {{ color: #e8e8f0; }}
  a {{ color: #4d8eff; text-decoration: none; }}
  code {{ font-family: 'JetBrains Mono', monospace; background: rgba(77,142,255,0.1); padding: 2px 6px; border-radius: 3px; font-size: 13px; color: #4d8eff; }}
  pre {{ background: #151520; border: 1px solid rgba(42,42,62,0.5); border-radius: 6px; padding: 16px; overflow-x: auto; margin: 12px 0; }}
  pre code {{ background: none; padding: 0; }}
  blockquote {{ border-left: 3px solid rgba(0,212,170,0.4); padding: 12px 20px; margin: 16px 0; background: rgba(0,212,170,0.04); border-radius: 0 6px 6px 0; }}
  blockquote p {{ color: #8888a0; }}
  hr {{ border: none; border-top: 1px solid rgba(42,42,62,0.5); margin: 32px 0; }}
  ul, ol {{ margin: 8px 0 8px 24px; color: #c8c8d8; }}
  li {{ margin: 4px 0; }}
  del {{ color: #666; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0 20px; font-size: 14px; background: #151520; border: 1px solid rgba(42,42,62,0.5); border-radius: 8px; overflow: hidden; }}
  thead th {{ text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #8888a0; padding: 10px 12px; border-bottom: 2px solid rgba(42,42,62,0.5); font-weight: 500; }}
  tbody td {{ padding: 9px 12px; border-bottom: 1px solid rgba(42,42,62,0.25); color: #c8c8d8; vertical-align: top; font-family: 'JetBrains Mono', monospace; font-size: 13px; }}
  tbody tr:hover {{ background: rgba(255,255,255,0.02); }}
  thead th:first-child, tbody td:first-child {{ font-family: 'Inter', sans-serif; font-size: 14px; }}
</style>
</head>
<body>
<div class="container">
"""

HTML_FOOTER = """
</div>
</body>
</html>
"""


def fix_markdown_for_pandoc(md: str) -> str:
    """Fix common markdown patterns that pandoc doesn't handle well.

    1. Insert blank line before list blocks (pandoc needs it to recognize <ul>)
    2. Convert 2-space sub-items to 4-space for proper nesting
    """
    lines = md.splitlines(keepends=True)
    fixed = []
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        prev = lines[i - 1].strip() if i > 0 else ""
        prev_is_blank = prev == ""
        prev_is_list = prev.startswith("- ") or prev.startswith("  -") or prev.startswith("    -")

        # Insert blank line before list items if previous line isn't blank/list
        if stripped.startswith("- ") and not prev_is_blank and not prev_is_list:
            fixed.append("\n")

        # Insert blank line before numbered list if previous line isn't blank
        if stripped[:1].isdigit() and ". " in stripped[:5] and not prev_is_blank:
            fixed.append("\n")

        # Insert blank line before table if previous line isn't blank
        if stripped.startswith("| ") and not prev_is_blank and not prev.startswith("|"):
            fixed.append("\n")

        # Convert 2-space sub-items to 4-space for pandoc nesting
        if line.startswith("  - "):
            line = "    " + line.lstrip()
        fixed.append(line)
    return "".join(fixed)


def extract_title(md: str) -> str:
    """Extract title from first H1 heading."""
    for line in md.splitlines():
        if line.startswith("# "):
            return line.lstrip("# ").strip()
    return "Report"


def convert(input_path: str, output_path: str) -> None:
    md = Path(input_path).read_text()
    title = extract_title(md)
    fixed_md = fix_markdown_for_pandoc(md)

    # Run pandoc to convert markdown body to HTML
    result = subprocess.run(
        ["pandoc", "--from=markdown+pipe_tables", "--to=html5"],
        input=fixed_md,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"pandoc error: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    body = result.stdout
    html = HTML_HEADER.format(title=title) + body + HTML_FOOTER

    Path(output_path).write_text(html)

    # Stats
    tables = body.count("<table")
    items = body.count("<li>")
    print(f"Generated {output_path}: {tables} tables, {items} list items")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.md> <output.html>")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
