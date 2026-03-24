"""
Shared utilities for XHS automation scripts.
"""

import os
import subprocess
from pathlib import Path

PROJECT_DIR = Path.home() / "claude" / "xiaohongshu-ops"
STATE_FILE = PROJECT_DIR / "WORKFLOW-STATE.md"
ENV_FILE = PROJECT_DIR / ".env"


def load_env() -> None:
    """Load environment variables from .env file.
    launchd does not read ~/.zshrc, so all scripts must call this at startup.
    """
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def read_state_field(field: str) -> str:
    if not STATE_FILE.exists():
        return ""
    for line in STATE_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{field}:"):
            return line[len(f"{field}:"):].strip()
    return ""


def update_state_field(field: str, value: str) -> None:
    if STATE_FILE.exists():
        text = STATE_FILE.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        updated = False
        new_lines = []
        for line in lines:
            if line.startswith(f"{field}:"):
                new_lines.append(f"{field}: {value}\n")
                updated = True
            else:
                new_lines.append(line)
        if not updated:
            new_lines.append(f"{field}: {value}\n")
        STATE_FILE.write_text("".join(new_lines), encoding="utf-8")
    else:
        STATE_FILE.write_text(f"{field}: {value}\n", encoding="utf-8")


def send_notification(message: str, title: str) -> None:
    """Send macOS notification."""
    subprocess.run(
        [
            "osascript",
            "-e",
            f'display notification "{message}" with title "{title}" sound name "Ping"',
        ],
        check=False,
    )


def send_slack(message: str, title: str) -> None:
    """Send Slack notification via webhook."""
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook:
        return
    import json
    payload = json.dumps({"text": f"*{title}*\n{message}"})
    subprocess.run(
        ["curl", "-s", "-X", "POST", "-H", "Content-type: application/json",
         "--data", payload, webhook],
        check=False,
        capture_output=True,
    )


def send_all_notifications(message: str, title: str) -> None:
    """Send both macOS and Slack notifications."""
    send_notification(message, title)
    send_slack(message, title)
