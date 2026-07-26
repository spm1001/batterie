# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Render a repo's README skill table from its skills/ directory.

Canonical copy: batterie-de-savoir scripts/render-skills.py. Component repos do
NOT carry a copy — their CI fetches this file from raw main (see MAINTAINING.md).

The generated block sits between these markers in README.md:

    <!-- GENERATED:SKILLS:START -->
    ...table...
    <!-- GENERATED:SKILLS:END -->

Usage:
    uv run --script render-skills.py [REPO_ROOT]           # rewrite README in place
    uv run --script render-skills.py [REPO_ROOT] --check   # exit 1 if README is stale

The table's one-liner is the SKILL.md description truncated at the first
sentence boundary, with the trailing "(user)" audience tag stripped. The skill
count is emitted inside the block, so prose counts can't drift separately.
"""

import re
import sys
from pathlib import Path

import yaml

START = "<!-- GENERATED:SKILLS:START -->"
END = "<!-- GENERATED:SKILLS:END -->"


def one_liner(description: str) -> str:
    text = " ".join(description.split())
    text = re.sub(r"\s*\(user\)\s*$", "", text)
    # First sentence: up to the first ". " (or the whole thing if none).
    # "Triggers on ..." tails are CSO plumbing, never table material.
    text = re.split(r"(?<=[.!?]) ", text, maxsplit=1)[0]
    return text.rstrip(".")


def read_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise SystemExit(f"no frontmatter in {skill_md}")
    return yaml.safe_load(match.group(1))


def render_block(repo_root: Path) -> str:
    skills_dir = repo_root / "skills"
    rows = []
    for skill_dir in sorted(skills_dir.iterdir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        fm = read_frontmatter(skill_md)
        name = fm.get("name", skill_dir.name)
        rows.append((name, one_liner(str(fm.get("description", "")))))
    if not rows:
        raise SystemExit(f"no skills found under {skills_dir}")
    count = len(rows)
    noun = "skill" if count == 1 else "skills"
    lines = [
        START,
        f"{count} {noun}, tabled from `skills/*/SKILL.md` frontmatter by"
        " [render-skills.py](https://github.com/spm1001/batterie-de-savoir/blob/main/scripts/render-skills.py)"
        " — regenerate from this repo's root with",
        "`uv run --script ../batterie-de-savoir/scripts/render-skills.py .`",
        "",
        "| Skill | What it does |",
        "|-------|--------------|",
    ]
    for name, desc in rows:
        lines.append(f"| `/{name}` | {desc} |")
    lines.append(END)
    return "\n".join(lines)


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--check"]
    check = "--check" in sys.argv[1:]
    repo_root = Path(args[0]) if args else Path.cwd()
    readme = repo_root / "README.md"
    original = readme.read_text(encoding="utf-8")
    if START not in original or END not in original:
        raise SystemExit(f"{readme} has no {START} block — add the markers first")
    block = render_block(repo_root)
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    rendered = pattern.sub(lambda _: block, original, count=1)
    if check:
        if rendered != original:
            print(f"STALE: {readme} skill table doesn't match skills/ —")
            print("  fix, from the repo root:")
            print("  uv run --script ../batterie-de-savoir/scripts/render-skills.py .")
            raise SystemExit(1)
        print(f"OK: {readme} skill table matches skills/")
        return
    if rendered != original:
        readme.write_text(rendered, encoding="utf-8")
        print(f"rewrote {readme}")
    else:
        print(f"unchanged {readme}")


if __name__ == "__main__":
    main()
