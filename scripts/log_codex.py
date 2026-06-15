#!/usr/bin/env python3
"""
Codex VS Code log scanner - extracts user prompts from local Codex rollout
transcripts and appends them to .ai-log/session.jsonl.

Source of truth:
    ~/.codex/sessions/**/rollout-*.jsonl
    ~/.codex/archived_sessions/rollout-*.jsonl

Codex writes one JSON object per line. For VS Code sessions, the cleanest user
prompt appears as:
    {"type":"event_msg","payload":{"type":"user_message","message":"..."}}

Usage:
  python scripts/log_codex.py --auto          # default: last 24h
  python scripts/log_codex.py --hours 72
  python scripts/log_codex.py --all           # every session, no cutoff
  python scripts/log_codex.py --session-id ID # one Codex session
  python scripts/log_codex.py --dry-run       # preview only

Env overrides:
  CODEX_HOME       Codex data directory (default: ~/.codex)
  CODEX_SESSIONS_DIR  extra sessions directory to scan
  AI_LOG_DIR       where session.jsonl is written (default: .ai-log)
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VN_TZ = timezone(timedelta(hours=7))
SESSION_ID_RE = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
    re.IGNORECASE,
)


def git(cmd: str) -> str:
    try:
        return subprocess.check_output(
            cmd.split(), shell=False, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ""


def _normalize(p: str) -> str:
    if not p:
        return ""
    return p.strip().lower().replace("/", "\\").rstrip("\\")


def _path_matches_repo(path: str, repo_root_n: str) -> bool:
    if not repo_root_n:
        return True
    path_n = _normalize(path)
    if not path_n:
        return False
    return (
        path_n == repo_root_n
        or path_n.startswith(repo_root_n + "\\")
        or repo_root_n.startswith(path_n + "\\")
    )


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _to_vn_iso(value: str) -> str:
    parsed = _parse_time(value)
    if parsed:
        return parsed.astimezone(VN_TZ).isoformat()
    return value or datetime.now(VN_TZ).isoformat()


def get_session_roots() -> list[Path]:
    roots: list[Path] = []
    extra = os.environ.get("CODEX_SESSIONS_DIR")
    if extra:
        roots.append(Path(extra))

    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    roots.extend([codex_home / "sessions", codex_home / "archived_sessions"])

    seen: set[Path] = set()
    existing: list[Path] = []
    for root in roots:
        try:
            resolved = root.expanduser().resolve()
        except OSError:
            continue
        if resolved.exists() and resolved not in seen:
            existing.append(resolved)
            seen.add(resolved)
    return existing


def iter_session_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        files.extend(root.rglob("rollout-*.jsonl"))
    return sorted(files)


def get_logged_entry_ids(log_file: Path) -> set[str]:
    logged: set[str] = set()
    if not log_file.exists():
        return logged
    with open(log_file, encoding="utf-8-sig") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            entry_id = entry.get("entry_id")
            if entry_id:
                logged.add(entry_id)
    return logged


def _content_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") in ("input_text", "text"):
            text = item.get("text", "")
            if text:
                parts.append(str(text))
    return "\n".join(parts).strip()


def _looks_like_injected_context(text: str) -> bool:
    stripped = text.strip()
    return (
        stripped.startswith("<environment_context>")
        or stripped.startswith("# AGENTS.md instructions")
        or stripped.startswith("# Context from my IDE setup:")
    )


def _extract_codex_request(text: str) -> str:
    marker = "## My request for Codex:"
    if marker in text:
        return text.split(marker, 1)[1].strip()
    return text.strip()


def read_session(path: Path) -> tuple[dict, list[dict]]:
    meta: dict = {"session_id": "", "cwd": "", "model": "", "source": ""}
    event_messages: list[dict] = []
    fallback_messages: list[dict] = []

    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            payload = obj.get("payload")
            if not isinstance(payload, dict):
                continue

            if obj.get("type") == "session_meta":
                meta.update({
                    "session_id": payload.get("id") or meta["session_id"],
                    "cwd": payload.get("cwd") or meta["cwd"],
                    "model": payload.get("model") or meta["model"],
                    "source": payload.get("originator") or payload.get("source") or meta["source"],
                })
                continue
            if obj.get("type") == "turn_context":
                meta.update({
                    "cwd": payload.get("cwd") or meta["cwd"],
                    "model": payload.get("model") or meta["model"],
                })
                continue

            if payload.get("type") == "user_message":
                text = str(payload.get("message") or "").strip()
                target = event_messages
            elif payload.get("type") == "message" and payload.get("role") == "user":
                text = _content_text(payload.get("content"))
                if _looks_like_injected_context(text):
                    continue
                text = _extract_codex_request(text)
                target = fallback_messages
            else:
                continue

            if len(text) < 2 or _looks_like_injected_context(text):
                continue

            target.append({
                "line_no": line_no,
                "timestamp": obj.get("timestamp") or "",
                "text": text,
            })

    if not meta["session_id"]:
        # Fallback for files named rollout-...-<uuid>.jsonl.
        match = SESSION_ID_RE.search(path.stem)
        meta["session_id"] = match.group(1) if match else path.stem
    return meta, event_messages or fallback_messages


def build_entry(msg: dict, meta: dict, repo: str, branch: str,
                commit: str, student: str) -> dict:
    session_id = meta.get("session_id") or "unknown"
    model = meta.get("model") or "codex"
    return {
        "ts": _to_vn_iso(msg["timestamp"]),
        "tool": "codex-vscode" if meta.get("source") == "codex_vscode" else "codex",
        "event": "UserPrompt",
        "entry_id": f"codex-{session_id}-{msg['line_no']:05d}",
        "session_id": session_id,
        "model": model,
        "repo": repo,
        "branch": branch,
        "commit": commit,
        "student": student,
        "prompt": msg["text"],
        "response_summary": "",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract user prompts from Codex VS Code transcripts into .ai-log/session.jsonl."
    )
    parser.add_argument("--auto", action="store_true",
                        help="Default mode: scan recent Codex sessions.")
    parser.add_argument("--hours", type=int, default=24,
                        help="Window in hours when scanning (default: 24).")
    parser.add_argument("--all", action="store_true",
                        help="Ignore the time window; scan everything.")
    parser.add_argument("--session-id",
                        help="Limit to one Codex session id.")
    parser.add_argument("--no-repo-filter", action="store_true",
                        help="Don't filter sessions by current repo.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be logged, don't write.")
    args = parser.parse_args()

    roots = get_session_roots()
    if not roots:
        print("[codex-log] No Codex sessions directory found.", file=sys.stderr)
        sys.exit(0)

    log_dir = Path(os.environ.get("AI_LOG_DIR", ".ai-log"))
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "session.jsonl"
    logged_ids = get_logged_entry_ids(log_file)

    cutoff = None if args.all else datetime.now(tz=VN_TZ) - timedelta(hours=args.hours)
    repo_root_n = "" if args.no_repo_filter else _normalize(str(Path.cwd()))

    repo = git("git remote get-url origin").split("/")[-1].replace(".git", "")
    branch = git("git rev-parse --abbrev-ref HEAD")
    commit = git("git rev-parse --short HEAD")
    student = git("git config user.email") or os.environ.get(
        "USERNAME", os.environ.get("USER", "unknown"))

    new_entries: list[dict] = []
    for session_file in iter_session_files(roots):
        try:
            meta, messages = read_session(session_file)
        except OSError:
            continue
        if args.session_id and meta.get("session_id") != args.session_id:
            continue
        if not args.no_repo_filter and not _path_matches_repo(meta.get("cwd", ""), repo_root_n):
            continue

        for msg in messages:
            msg_time = _parse_time(msg["timestamp"])
            if cutoff and msg_time and msg_time < cutoff:
                continue
            entry = build_entry(msg, meta, repo or Path.cwd().name,
                                branch, commit, student)
            if entry["entry_id"] in logged_ids:
                continue
            new_entries.append(entry)
            logged_ids.add(entry["entry_id"])

    if not new_entries:
        scope = "all" if args.all else f"{args.hours}h"
        repo_note = "any repo" if args.no_repo_filter else f"repo={repo_root_n or '(unknown)'}"
        print(f"[codex-log] No new prompts ({repo_note}, window={scope}).",
              file=sys.stderr)
        sys.exit(0)

    if args.dry_run:
        print(f"\n[codex-log] DRY RUN - would log {len(new_entries)} entries:\n")
        for entry in new_entries:
            preview = entry["prompt"].replace("\n", " ")[:120]
            print(f"  [{entry['ts'][:19]}] {preview}")
        sys.exit(0)

    with open(log_file, "a", encoding="utf-8") as f:
        for entry in new_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"[codex-log] Logged {len(new_entries)} prompt(s) from Codex.",
          file=sys.stderr)


if __name__ == "__main__":
    main()
