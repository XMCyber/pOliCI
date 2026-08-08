#!/usr/bin/env python3
"""Fix markdown reference link text to use consistent Title Case."""

import re
import sys
from pathlib import Path

ALWAYS_UPPER = {
    "oci", "iam", "cli", "imds", "mfa", "ocir", "kms", "sdk", "api",
    "os", "fn", "v2", "ui",
}
ALWAYS_LOWER = {"a", "an", "the", "and", "or", "for", "in", "on", "to", "from", "of", "via"}


def title_case_word(word: str, is_first: bool) -> str:
    lower = word.lower()
    if lower in ALWAYS_UPPER:
        return word.upper()

    if "-" in word and not word.startswith("—"):
        parts = word.split("-")
        return "-".join(title_case_word(p, i == 0) for i, p in enumerate(parts))

    if lower in ALWAYS_LOWER and not is_first:
        return lower

    return word.capitalize()


def title_case_text(text: str) -> str:
    if " — " in text:
        segments = text.split(" — ")
        return " - ".join(title_case_text(s.strip()) for s in segments)

    words = text.split()
    result = []
    for i, word in enumerate(words):
        result.append(title_case_word(word, i == 0))
    return " ".join(result)


def fix_link_line(line: str) -> str:
    match = re.match(r'^(\- \[)(.+?)(\]\(.+\))$', line)
    if not match:
        return line

    prefix, link_text, suffix = match.groups()

    if link_text.startswith("OCI CLI: "):
        cli_part = link_text[len("OCI CLI: "):]
        fixed_cli = title_case_text(cli_part)
        return f"{prefix}OCI CLI: {fixed_cli}{suffix}"

    return f"{prefix}{title_case_text(link_text)}{suffix}"


def fix_file(filepath: Path, dry_run: bool = False) -> bool:
    content = filepath.read_text()
    lines = content.split("\n")
    in_references = False
    changed = False
    new_lines = []

    for line in lines:
        if line.strip() == "## References":
            in_references = True
            new_lines.append(line)
            continue

        if in_references and line.startswith("## "):
            in_references = False

        if in_references and line.startswith("- ["):
            new_line = fix_link_line(line)
            if new_line != line:
                changed = True
                if dry_run:
                    print(f"  {filepath.name}:")
                    print(f"    - {line}")
                    print(f"    + {new_line}")
                line = new_line

        new_lines.append(line)

    if changed and not dry_run:
        filepath.write_text("\n".join(new_lines))
        print(f"  Fixed: {filepath}")

    return changed


def main():
    dry_run = "--dry-run" in sys.argv
    dirs = [a for a in sys.argv[1:] if a != "--dry-run"]

    if not dirs:
        print("Usage: fix_link_capitalization.py [--dry-run] <dir1> [dir2] ...")
        sys.exit(1)

    total_fixed = 0
    for d in dirs:
        root = Path(d)
        for md in sorted(root.rglob("tech-*.md")):
            if fix_file(md, dry_run):
                total_fixed += 1

    action = "Would fix" if dry_run else "Fixed"
    print(f"\n{action} {total_fixed} file(s).")


if __name__ == "__main__":
    main()
