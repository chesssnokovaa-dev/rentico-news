"""Отправляет новые сводки из digests/ в Telegram-бота.

Chat ID берётся по порядку: секрет TELEGRAM_CHAT_ID, файл config/chat_id.txt,
а если нет ни того ни другого, из последнего сообщения, отправленного боту
(достаточно один раз написать боту /start). Найденный ID сохраняется в
config/chat_id.txt, чтобы не искать его повторно.
"""

import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
API = f"https://api.telegram.org/bot{TOKEN}"
CHAT_FILE = Path("config/chat_id.txt")
LIMIT = 3900  # лимит Telegram 4096 символов, оставляем запас на разметку


def call(method: str, params: dict) -> dict:
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"{API}/{method}", data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.exit(f"Telegram {method} вернул {e.code}: {body}")


def resolve_chat_id() -> str:
    env_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if env_id:
        return env_id
    if CHAT_FILE.exists() and CHAT_FILE.read_text().strip():
        return CHAT_FILE.read_text().strip()
    updates = call("getUpdates", {"limit": 100}).get("result", [])
    chats = []
    for u in updates:
        msg = u.get("message") or u.get("channel_post") or u.get("my_chat_member")
        if msg and msg.get("chat"):
            chats.append(msg["chat"])
    if not chats:
        sys.exit("Не нашёл chat id: напишите боту /start и запустите отправку ещё раз.")
    private = [c for c in chats if c.get("type") == "private"]
    chat_id = str((private or chats)[-1]["id"])
    CHAT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHAT_FILE.write_text(chat_id + "\n")
    print(f"Chat id найден и сохранён: {chat_id}")
    return chat_id


def changed_digests() -> list[Path]:
    manual = os.environ.get("MANUAL_FILE", "").strip()
    if manual:
        return [Path(manual)]
    before = os.environ.get("BEFORE_SHA", "").strip()
    if not before or set(before) == {"0"}:
        cmd = ["git", "show", "--pretty=", "--name-only", "--diff-filter=AM", "HEAD"]
    else:
        cmd = ["git", "diff", "--name-only", "--diff-filter=AM", before, "HEAD"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        out = subprocess.run(
            ["git", "show", "--pretty=", "--name-only", "--diff-filter=AM", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout
    files = [Path(p) for p in out.split() if p.startswith("digests/") and p.endswith(".md")]
    return sorted(files)


def to_html(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?m)^#{1,6}\s*(.+)$", r"<b>\1</b>", text)
    return text


def chunks(text: str) -> list[str]:
    parts, current = [], ""
    for block in text.split("\n\n"):
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) <= LIMIT:
            current = candidate
            continue
        if current:
            parts.append(current)
        while len(block) > LIMIT:
            parts.append(block[:LIMIT])
            block = block[LIMIT:]
        current = block
    if current:
        parts.append(current)
    return parts


def main() -> None:
    if not TOKEN:
        sys.exit("Нет секрета TELEGRAM_BOT_TOKEN в настройках репозитория.")
    files = changed_digests()
    if not files:
        print("Новых сводок нет, отправлять нечего.")
        return
    chat_id = resolve_chat_id()
    for path in files:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            continue
        for part in chunks(raw):
            res = call("sendMessage", {
                "chat_id": chat_id,
                "text": to_html(part),
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            })
            if not res.get("ok"):
                sys.exit(f"Ошибка отправки {path}: {res}")
        print(f"Отправлено: {path}")


if __name__ == "__main__":
    main()
