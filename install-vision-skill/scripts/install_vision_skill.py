#!/usr/bin/env python3
"""Install claude-code-vision-skill on a machine and wire it to an
Aliyun MaaS (DashScope / OpenAI-compatible) workspace.

Installs:
  - Codex skill:  <codex-skills>/vision/{SKILL.md, vision.py}
  - Claude skill: <claude-home>/skills/vision/{SKILL.md, vision.py}
  - Env config:   <claude-home>/settings.json (DASHSCOPE/OPENAI keys,
                  base URL, model, VISION_PROVIDER=qwen) plus a
                  SessionStart routing hook
  - CLAUDE.md:    vision inspection workflow merged once (single markers)
  - CC Switch:    input_modalities ["text"] -> ["text", "image"] in
                  <codex-home>/cc-switch-model-catalog.json

Secrets are never stored in this skill. Pass the API key per run via
--api-key or the VISION_SETUP_API_KEY environment variable.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO_ZIP_URL = "https://github.com/xiincs/claude-code-vision-skill/archive/refs/heads/main.zip"
VISION_FILES = ["SKILL.md", "vision.py"]
MARKER_START = "<!-- === VISION_SKILL_START === -->"
MARKER_END = "<!-- === VISION_SKILL_END === -->"
HOOK_MATCHER = "startup|resume|clear|compact"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("VISION_SETUP_API_KEY", ""),
        help="Aliyun MaaS API key (or set VISION_SETUP_API_KEY)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("VISION_SETUP_BASE_URL", ""),
        help="OpenAI-compatible base URL, e.g. "
        "https://<host>.maas.aliyuncs.com/compatible-mode/v1 "
        "(or set VISION_SETUP_BASE_URL)",
    )
    parser.add_argument("--model", default="qwen-vl-max")
    parser.add_argument(
        "--codex-skills-dir",
        default=str(Path.home() / ".codex" / "skills"),
    )
    parser.add_argument("--claude-home", default=str(Path.home() / ".claude"))
    parser.add_argument(
        "--cc-switch-catalog",
        default=str(Path.home() / ".codex" / "cc-switch-model-catalog.json"),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Download and validate inputs, but write nothing",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def backup(path: Path) -> None:
    if path.exists():
        bak = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, bak)
        print(f"  backup -> {bak}")


def download_repo(tmp_dir: Path) -> tuple[Path, Path]:
    """Return (repo_root, vision_dir)."""
    zip_path = tmp_dir / "repo.zip"
    req = urllib.request.Request(
        REPO_ZIP_URL,
        headers={"User-Agent": "codex-skill-installer"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        zip_path.write_bytes(resp.read())
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(tmp_dir)
    top_level = next(
        p for p in tmp_dir.iterdir()
        if p.is_dir() and (p / "vision" / "SKILL.md").exists()
    )
    return top_level, top_level / "vision"


def install_skill_files(vision_dir: Path, dest_root: Path, dry_run: bool) -> None:
    dest = dest_root / "vision"
    dest.mkdir(parents=True, exist_ok=True)
    for name in VISION_FILES:
        src = vision_dir / name
        target = dest / name
        if dry_run:
            print(f"  [dry-run] copy {name} -> {target}")
            continue
        shutil.copy2(src, target)
        print(f"  copied {name} -> {target}")


def configure_settings(
    claude_home: Path,
    vision_py: Path,
    api_key: str,
    base_url: str,
    model: str,
    dry_run: bool,
) -> None:
    settings_path = claude_home / "settings.json"
    settings = read_json(settings_path) if not dry_run else {}
    if not dry_run:
        backup(settings_path)
        settings["env"] = {
            "DASHSCOPE_API_KEY": api_key,
            "DASHSCOPE_BASE_URL": base_url,
            "QWEN_MODEL": model,
            "OPENAI_API_KEY": api_key,
            "OPENAI_BASE_URL": base_url,
            "OPENAI_MODEL": model,
            "VISION_PROVIDER": "qwen",
        }
        session_start = settings.setdefault("hooks", {}).setdefault(
            "SessionStart", []
        )
        session_start[:] = [
            entry
            for entry in session_start
            if not any(
                h.get("type") == "command"
                and "--session-start-hook" in h.get("command", "")
                for h in entry.get("hooks", [])
            )
        ]
        session_start.append(
            {
                "matcher": HOOK_MATCHER,
                "hooks": [
                    {
                        "type": "command",
                        "command": f'python "{vision_py}" --session-start-hook',
                        "timeout": 10,
                    }
                ],
            }
        )
        write_json(settings_path, settings)
    print(f"  env + SessionStart hook -> {settings_path}" + (" (dry-run)" if dry_run else ""))


def merge_claude_md(claude_home: Path, repo_root: Path, dry_run: bool) -> None:
    template_path = repo_root / "CLAUDE.md"
    if not template_path.exists():
        print("  (no CLAUDE.md template in repo, skipping merge)")
        return
    template = template_path.read_text(encoding="utf-8").strip()
    # Template already contains markers; never double-wrap.
    if MARKER_START not in template:
        template = f"{MARKER_START}\n{template}\n{MARKER_END}"
    marked = f"\n\n{template}"

    user_claude = claude_home / "CLAUDE.md"
    if dry_run:
        print(f"  [dry-run] merge CLAUDE.md -> {user_claude}")
        return

    backup(user_claude)
    if user_claude.exists():
        existing = user_claude.read_text(encoding="utf-8")
        if MARKER_START in existing and MARKER_END in existing:
            before = existing.split(MARKER_START)[0]
            after = existing.split(MARKER_END)[-1]
            new_content = before + marked + after
            user_claude.write_text(new_content, encoding="utf-8")
            print("  updated CLAUDE.md (existing vision section replaced)")
        else:
            user_claude.write_text(existing + marked, encoding="utf-8")
            print("  merged CLAUDE.md (appended with markers)")
    else:
        user_claude.parent.mkdir(parents=True, exist_ok=True)
        user_claude.write_text(marked.strip(), encoding="utf-8")
        print("  created CLAUDE.md")


def enable_image_modality(catalog_path: Path, dry_run: bool) -> None:
    if not catalog_path.exists():
        print(
            f"  (CC Switch catalog not found at {catalog_path}, skipping "
            "input_modalities change)"
        )
        return
    try:
        catalog = read_json(catalog_path)
    except json.JSONDecodeError as exc:
        print(f"  (CC Switch catalog is invalid JSON, skipping: {exc})")
        return

    changed = 0
    for model in catalog.get("models", []):
        if model.get("input_modalities") == ["text"]:
            model["input_modalities"] = ["text", "image"]
            changed += 1
    if changed:
        if dry_run:
            print(f"  [dry-run] enable image input for {changed} model(s) in {catalog_path}")
        else:
            backup(catalog_path)
            write_json(catalog_path, catalog)
            print(f"  enabled image input for {changed} model(s) in {catalog_path}")
    else:
        print(f"  input_modalities already includes image (or nothing to change) in {catalog_path}")


def main() -> int:
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    if not args.api_key:
        print("Error: missing API key (pass --api-key or set VISION_SETUP_API_KEY)", file=sys.stderr)
        return 1
    if not args.base_url:
        print("Error: missing base URL (pass --base-url or set VISION_SETUP_BASE_URL)", file=sys.stderr)
        return 1

    codex_skills = Path(args.codex_skills_dir)
    claude_home = Path(args.claude_home)
    catalog = Path(args.cc_switch_catalog)

    print("Downloading claude-code-vision-skill...")
    with tempfile.TemporaryDirectory(prefix="vision-install-") as tmp:
        tmp_dir = Path(tmp)
        repo_root, vision_dir = download_repo(tmp_dir)
        print(f"  repo extracted from {REPO_ZIP_URL}")

        print("Installing skill files (Codex + Claude Code)...")
        install_skill_files(vision_dir, codex_skills, args.dry_run)
        install_skill_files(vision_dir, claude_home / "skills", args.dry_run)

        print("Configuring ~/.claude/settings.json...")
        vision_py = claude_home / "skills" / "vision" / "vision.py"
        configure_settings(
            claude_home, vision_py, args.api_key, args.base_url, args.model, args.dry_run
        )

        print("Merging CLAUDE.md...")
        merge_claude_md(claude_home, repo_root, args.dry_run)

    print("Enabling image input in CC Switch catalog...")
    enable_image_modality(catalog, args.dry_run)

    if args.dry_run:
        print("\n[dry-run] No files were modified.")
    else:
        print("\nDone. Next steps:")
        print("  pip install 'openai>=1.0.0' 'anthropic>=0.40.0'")
        print(f'  python "{vision_py}" --help')
        print(
            '  python "{}" "some.png" "describe this image"'.format(vision_py)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
