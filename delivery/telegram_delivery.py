"""
Telegram delivery — sends the brief to a Telegram chat/channel.
"""

import os
import requests


class TelegramDelivery:
    def __init__(self, config: dict):
        delivery = config.get("delivery", {})
        self.token = delivery.get("telegram_token", "") or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = delivery.get("telegram_chat_id", "") or os.getenv("TELEGRAM_CHAT_ID", "")

    def send(self, message: str) -> bool:
        if not self.token or not self.chat_id:
            print("  [Telegram] No token/chat_id configured. Skipping delivery.")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        chunks = self._split_message(message, 4000)

        for chunk in chunks:
            try:
                resp = requests.post(url, json={
                    "chat_id": self.chat_id,
                    "text": chunk,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                })
                resp.raise_for_status()
            except Exception as e:
                print(f"  [Telegram] Error sending: {e}")
                return False

        print(f"  [Telegram] Sent brief ({len(chunks)} message(s))")
        return True

    def _split_message(self, text: str, max_len: int) -> list[str]:
        if len(text) <= max_len:
            return [text]
        chunks = []
        lines = text.split("\n")
        current = ""
        for line in lines:
            if len(current) + len(line) + 1 > max_len:
                chunks.append(current)
                current = line
            else:
                current = current + "\n" + line if current else line
        if current:
            chunks.append(current)
        return chunks
