"""
telegram_bot.py — Kirim ringkasan lomba ke grup/channel Telegram
Library: python-telegram-bot (v20+)

Setup:
  pip install python-telegram-bot

Cara dapat BOT_TOKEN:
  - Chat @BotFather di Telegram → /newbot → ikuti instruksi

Cara dapat CHAT_ID:
  - Untuk grup: tambah bot ke grup → kirim pesan → cek via
    https://api.telegram.org/bot<TOKEN>/getUpdates
  - Untuk channel: tambah bot sebagai admin → gunakan @namaChannel
    atau numeric ID (prefix dengan -100 untuk supergroup/channel)
"""

import logging
import asyncio
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# KONFIGURASI — EDIT BAGIAN INI
# ──────────────────────────────────────────────

BOT_TOKEN = "8615881534:AAE8aXfCjbV0qzOS87cKqpAjQgzJe3a56eA"   # Dari @BotFather
CHAT_ID   = "6783869140"        # ID grup/channel tujuan

MAX_LOMBA_PER_PESAN = 10   # Batasi agar pesan tidak terlalu panjang
MAX_MESSAGE_LENGTH  = 4000 # Batas Telegram: 4096 karakter


# ──────────────────────────────────────────────
# FORMATTER PESAN
# ──────────────────────────────────────────────

def format_lomba_item(lomba: dict, index: int) -> str:
    """Format satu item lomba jadi teks Telegram (Markdown)."""
    nama     = lomba.get("Nama Lomba") or lomba.get("nama_lomba", "—")
    deadline = lomba.get("Deadline")   or lomba.get("deadline",   "Cek website")
    link     = lomba.get("Link")       or lomba.get("link",       "")
    kategori = lomba.get("Kategori")   or lomba.get("kategori",   "—")

    link_text = f"[🔗 Daftar sekarang]({link})" if link else "_(link tidak tersedia)_"

    return (
        f"*{index}. {nama}*\n"
        f"📂 Kategori : {kategori}\n"
        f"⏰ Deadline  : {deadline}\n"
        f"{link_text}"
    )


def format_pesan(lomba_list: list[dict], periode: str = "") -> list[str]:
    """
    Format daftar lomba jadi satu atau beberapa pesan Telegram.
    Otomatis split jika melebihi MAX_MESSAGE_LENGTH.
    """
    if not periode:
        periode = datetime.now().strftime("%d %B %Y")

    header = (
        f"🏆 *REKAP LOMBA IT — {periode}* 🏆\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    footer = (
        f"\n━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *{len(lomba_list)} lomba aktif*\n"
        f"🤖 Update otomatis tiap 2 minggu\n"
        f"_Powered by Himpunan IT Bot_"
    )

    items = []
    for i, lomba in enumerate(lomba_list[:MAX_LOMBA_PER_PESAN], start=1):
        items.append(format_lomba_item(lomba, i))

    # Gabungkan dan split jika terlalu panjang
    messages = []
    current = header
    for item in items:
        candidate = current + item + "\n\n"
        if len(candidate) > MAX_MESSAGE_LENGTH:
            messages.append(current.rstrip())
            current = item + "\n\n"
        else:
            current = candidate

    current += footer
    messages.append(current)

    return messages


# ──────────────────────────────────────────────
# KIRIM PESAN
# ──────────────────────────────────────────────

async def send_messages_async(messages: list[str]) -> bool:
    """Kirim daftar pesan ke Telegram secara async."""
    bot = Bot(token=BOT_TOKEN)
    success = True

    for i, msg in enumerate(messages):
        try:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False,
            )
            logger.info(f"Pesan {i+1}/{len(messages)} berhasil dikirim")
            if i < len(messages) - 1:
                await asyncio.sleep(1)  # Jeda antar pesan
        except TelegramError as e:
            logger.error(f"Gagal kirim pesan {i+1}: {e}")
            success = False

    return success


def send_lomba_update(lomba_list: list[dict], periode: str = "") -> bool:
    """
    Fungsi utama: format & kirim update lomba ke Telegram.
    Return True jika semua pesan berhasil.
    """
    if not lomba_list:
        logger.warning("Tidak ada lomba untuk dikirim")
        return False

    logger.info(f"Mengirim {len(lomba_list)} lomba ke Telegram (chat: {CHAT_ID})")
    messages = format_pesan(lomba_list, periode)

    return asyncio.run(send_messages_async(messages))


async def send_plain_message_async(text: str) -> bool:
    """Kirim pesan teks biasa (untuk notifikasi error/status)."""
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode=ParseMode.MARKDOWN)
        return True
    except TelegramError as e:
        logger.error(f"Gagal kirim notifikasi: {e}")
        return False


def notify(text: str) -> bool:
    return asyncio.run(send_plain_message_async(text))


# ──────────────────────────────────────────────
# TEST
# ──────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    sample = [
        {"nama_lomba": "Hackathon AI Nasional 2025", "deadline": "31 Desember 2025", "link": "https://example.com/hackathon-ai", "kategori": "AI / Machine Learning"},
        {"nama_lomba": "Data Science Competition UI", "deadline": "15 Januari 2026", "link": "https://example.com/ds-comp", "kategori": "Data Science"},
        {"nama_lomba": "National Programming Contest", "deadline": "20 Februari 2026", "link": "https://example.com/npc", "kategori": "Programming"},
    ]

    if BOT_TOKEN == "ISI_TOKEN_BOT_KAMU_DI_SINI":
        print("⚠️  Isi BOT_TOKEN dan CHAT_ID dulu!")
        # Preview format pesan tanpa kirim
        messages = format_pesan(sample)
        print("\n── PREVIEW PESAN ──")
        for i, msg in enumerate(messages, 1):
            print(f"\n[Pesan {i}]\n{msg}")
    else:
        result = send_lomba_update(sample)
        print("✅ Berhasil!" if result else "❌ Gagal kirim")