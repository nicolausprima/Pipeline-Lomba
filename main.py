"""
main.py — Orchestrator utama pipeline lomba IT
Jalankan ini untuk eksekusi seluruh pipeline sekaligus.

Urutan:
  1. Scraping dari semua sumber
  2. Filter keyword + deduplikasi
  3. Sinkronisasi ke Google Sheets
  4. Kirim ringkasan ke Telegram
"""

import logging
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


def run_pipeline(dry_run: bool = False):
    """
    Jalankan full pipeline.
    dry_run=True → scrape & filter saja, tidak kirim ke Sheets/Telegram.
    """
    start = datetime.now()
    logger.info("=" * 50)
    logger.info(f"PIPELINE MULAI — {start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)

    # ── STEP 1: SCRAPING ──────────────────────────
    logger.info("STEP 1: Scraping sumber data...")
    try:
        from scraper import scrape_all
        raw_data = scrape_all()
        logger.info(f"✓ Scraping selesai — {len(raw_data)} item mentah")
    except Exception as e:
        logger.error(f"✗ Scraping gagal: {e}")
        raw_data = []

    if not raw_data:
        logger.warning("Tidak ada data hasil scraping. Pipeline berhenti.")
        return

    # ── STEP 2: FILTER & DEDUP ────────────────────
    logger.info("STEP 2: Filter keyword & deduplikasi...")
    try:
        from filter_dedup import process
        clean_data = process(raw_data)
        logger.info(f"✓ Filter selesai — {len(clean_data)} lomba bersih")
    except Exception as e:
        logger.error(f"✗ Filter gagal: {e}")
        clean_data = raw_data  # Fallback: lanjutkan dengan data mentah

    if dry_run:
        logger.info("DRY RUN aktif — berhenti di sini (tidak simpan/kirim)")
        for i, lomba in enumerate(clean_data, 1):
            logger.info(f"  {i}. {lomba['nama_lomba']} | {lomba['deadline']}")
        return

    # ── STEP 3: GOOGLE SHEETS ─────────────────────
    logger.info("STEP 3: Sinkronisasi ke Google Sheets...")
    sheets_summary = {"added": 0, "removed": 0}
    try:
        from sheets_manager import sync_to_sheets
        sheets_summary = sync_to_sheets(clean_data)
        logger.info(
            f"✓ Sheets sync — +{sheets_summary['added']} baru, "
            f"-{sheets_summary['removed']} dihapus"
        )
    except Exception as e:
        logger.error(f"✗ Google Sheets gagal: {e}")
        logger.info("Melanjutkan ke Telegram meski Sheets gagal...")

    # ── STEP 4: TELEGRAM ──────────────────────────
    logger.info("STEP 4: Mengirim ringkasan ke Telegram...")
    try:
        from sheets_manager import get_active_lomba
        active_lomba = get_active_lomba()
    except Exception:
        # Fallback: pakai data clean lokal jika Sheets tidak tersedia
        active_lomba = clean_data

    try:
        from telegram_bot import send_lomba_update, notify
        periode = datetime.now().strftime("%d %B %Y")
        success = send_lomba_update(active_lomba, periode)

        if success:
            logger.info(f"✓ Telegram — {len(active_lomba)} lomba terkirim")
        else:
            logger.warning("✗ Telegram — sebagian atau semua pesan gagal")
    except Exception as e:
        logger.error(f"✗ Telegram gagal: {e}")

    # ── SELESAI ───────────────────────────────────
    duration = (datetime.now() - start).seconds
    logger.info("=" * 50)
    logger.info(
        f"PIPELINE SELESAI dalam {duration}s | "
        f"Scraped: {len(raw_data)} | "
        f"Bersih: {len(clean_data)} | "
        f"Sheet +{sheets_summary['added']} -{sheets_summary['removed']}"
    )
    logger.info("=" * 50)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pipeline Lomba IT")
    parser.add_argument("--dry-run", action="store_true", help="Scrape saja, jangan simpan/kirim")
    args = parser.parse_args()

    run_pipeline(dry_run=args.dry_run)