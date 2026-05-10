"""
telegram_bot.py — Kirim notifikasi lomba ke Telegram
"""

import logging
import os
import json
import requests
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger("telegram_bot")

# Load config
CONFIG = {}
config_path = os.path.join(os.path.dirname(__file__), 'config.json')
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)

BOT_TOKEN = CONFIG.get('telegram_bot_token') or os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = CONFIG.get('telegram_chat_id') or os.environ.get('TELEGRAM_CHAT_ID')


def _escape_html(text: str) -> str:
    if not text:
        return "-"
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_lomba_message(lomba_list: List[Dict], periode: str) -> str:
    if not lomba_list:
        return f"🏆 <b>REKAP LOMBA IT — {periode}</b>\n\n<i>Tidak ada lomba aktif saat ini.</i>"
    
    lines = [
        f"🏆 <b>REKAP LOMBA IT — {periode}</b>",
        "━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    
    for i, lomba in enumerate(lomba_list[:15], 1):
        nama = _escape_html(lomba.get("nama_lomba", "Tidak diketahui"))
        kategori = _escape_html(lomba.get("kategori", "Umum"))
        deadline = _escape_html(lomba.get("deadline", "Cek website"))
        link = lomba.get("link", "")
        
        if link and link != "Cek website" and link.startswith("http"):
            link_text = f'<a href="{link}">🔗 Link Lomba</a>'
        else:
            link_text = "<i>link tidak tersedia</i>"
        
        lines.append(f"{i}. <b>{nama}</b>")
        lines.append(f"   📂 Kategori : {kategori}")
        lines.append(f"   ⏰ Deadline  : {deadline}")
        lines.append(f"   {link_text}")
        lines.append("")
    
    total = len(lomba_list)
    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━",
        f"📌 <b>{total} lomba aktif</b>",
        "🤖 Update otomatis tiap 2 minggu",
        "Powered by Himpunan IT Bot",
    ])
    
    return "\n".join(lines)


def send_lomba_update(lomba_list: List[Dict], periode: str = None) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        logger.error("❌ TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID tidak di-set!")
        logger.info("💡 Tips: Buat config.json atau set environment variable")
        return False
    
    if periode is None:
        periode = datetime.now().strftime("%d %B %Y")
    
    message = format_lomba_message(lomba_list, periode)
    
    if len(message) > 4000:
        return _send_long_message(message)
    
    return _send_telegram_message(message)


def _send_telegram_message(text: str) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        
        if data.get("ok"):
            logger.info("✓ Pesan Telegram terkirim")
            return True
        else:
            logger.error(f"✗ Telegram error: {data.get('description')}")
            return False
    except Exception as e:
        logger.error(f"✗ Gagal kirim Telegram: {e}")
        return False


def _send_long_message(text: str) -> bool:
    lines = text.split("\n")
    chunks = []
    current_chunk = []
    current_length = 0
    
    for line in lines:
        line_length = len(line) + 1
        if current_length + line_length > 4000:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_length = line_length
        else:
            current_chunk.append(line)
            current_length += line_length
    
    if current_chunk:
        chunks.append("\n".join(current_chunk))
    
    success = True
    for i, chunk in enumerate(chunks):
        if i > 0:
            chunk = f"<i>(lanjutan {i+1}/{len(chunks)})</i>\n\n" + chunk
        if not _send_telegram_message(chunk):
            success = False
        import time
        time.sleep(1)
    
    return success


def notify(message: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        logger.error("Telegram credentials tidak di-set!")
        return False
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        return resp.json().get("ok", False)
    except Exception as e:
        logger.error(f"Gagal kirim notifikasi: {e}")
        return False


def notify_error(error_message: str) -> bool:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"⚠️ <b>PIPELINE ERROR</b>\n\n<i>{timestamp}</i>\n\n<code>{error_message}</code>"
    return notify(message)