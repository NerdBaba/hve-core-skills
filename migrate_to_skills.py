#!/usr/bin/env python3
"""Migrate .github/ agents, instructions, prompts, skills → skills/ for skills CLI compatibility."""

import os
import shutil
from pathlib import Path

BASE = Path(".")
GITHUB = BASE / ".github"
DST = BASE / "skills"


def split_frontmatter(content):
    """Split markdown into (frontmatter_string, body_string)."""
    if not content.startswith("---\n") and not content.startswith("---\r\n"):
        return None, content
    sep = "\n" if content.startswith("---\n") else "\r\n"
    lines = content.split(sep)
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm = sep.join(lines[1:i])
            body = sep.join(lines[i + 1 :])
            return fm, body
    return None, content


def ensure_name(fm, name):
    """Ensure name field exists and matches directory name (skill standard requirement)."""
    if fm is None:
        return f"name: {name}"
    lines = fm.split("\n")
    new_lines = [f"name: {name}"]
    for line in lines:
        if line.startswith("name:"):
            continue  # skip existing — our injected one is authoritative
        new_lines.append(line)
    return "\n".join(new_lines)


def rebuild_content(content, name):
    """Rebuild markdown with corrected name in frontmatter."""
    fm, body = split_frontmatter(content)
    fm = ensure_name(fm, name)
    return f"---\n{fm}\n---\n{body}"


def migrate_kind(src_dir, suffix, dst_subdir):
    """Migrate all *{suffix} files from src_dir to skills/{dst_subdir}/ as SKILL.md skills."""
    dst_base = DST / dst_subdir
    count = 0
    if not src_dir.exists():
        return 0
    for md_file in sorted(src_dir.rglob(f"*{suffix}")):
        rel = md_file.relative_to(src_dir)
        name = rel.with_suffix("").name  # last path component = skill name
        dst_dir = dst_base / rel.with_suffix("")
        dst_dir.mkdir(parents=True, exist_ok=True)
        content = md_file.read_text(encoding="utf-8")
        content = rebuild_content(content, name)
        (dst_dir / "SKILL.md").write_text(content, encoding="utf-8")
        count += 1
        print(f"  {dst_subdir}: {rel.with_suffix('')}")
    return count


def migrate_capabilities():
    """Copy existing .github/skills/ (with scripts/tests) to skills/capabilities/."""
    src = GITHUB / "skills"
    dst_base = DST / "capabilities"
    count = 0
    if not src.exists():
        return 0
    for skill_md in sorted(src.rglob("SKILL.md")):
        skill_root = skill_md.parent
        rel = skill_root.relative_to(src)
        dst_dir = dst_base / rel
        if dst_dir.exists():
            shutil.rmtree(dst_dir)
        shutil.copytree(skill_root, dst_dir)
        count += 1
        print(f"  capabilities: {rel}")
    return count


def main():
    print("Migrating to skills/ directory...\n")

    a = migrate_kind(GITHUB / "agents", ".agent.md", "agents")
    i = migrate_kind(GITHUB / "instructions", ".instructions.md", "instructions")
    p = migrate_kind(GITHUB / "prompts", ".prompt.md", "prompts")
    c = migrate_capabilities()

    # Symlink .agents/skills → skills/ (canonical location for skills CLI)
    agents_dir = BASE / ".agents"
    agents_skills = agents_dir / "skills"
    agents_dir.mkdir(exist_ok=True)
    if agents_skills.exists() or agents_skills.is_symlink():
        agents_skills.unlink()
    os.symlink(DST.resolve(), agents_skills)

    total = a + i + p + c
    print(f"\n{'='*50}")
    print(f"Done! {total} skills created in skills/")
    print(f"  Agents:       {a}")
    print(f"  Instructions: {i}")
    print(f"  Prompts:      {p}")
    print(f"  Capabilities: {c}")
    print(f"  .agents/skills → skills/ (symlink created)")


if __name__ == "__main__":
    main()
