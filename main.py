"""
main.py — Orchestrator utama pipeline lomba IT
"""

import logging
import sys
import os
import json
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

# Load config
CONFIG = {}
config_path = os.path.join(os.path.dirname(__file__), 'config.json')
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)
    logger.info("✓ Config loaded dari config.json")
else:
    logger.warning("⚠ config.json tidak ditemukan, menggunakan environment variables")


def run_pipeline(dry_run: bool = False):
    start = datetime.now()
    logger.info("=" * 60)
    logger.info(f"PIPELINE MULAI — {start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # STEP 1: SCRAPING
    logger.info("[STEP 1/4] Scraping sumber data...")
    raw_data = []
    try:
        from scraper import scrape_all
        raw_data = scrape_all()
        logger.info(f"✓ Scraping selesai — {len(raw_data)} item mentah")
    except Exception as e:
        logger.error(f"✗ Scraping gagal: {e}", exc_info=True)
        _notify_error(f"Scraping gagal: {str(e)}")

    if not raw_data:
        logger.warning("⚠ Tidak ada data hasil scraping. Pipeline berhenti.")
        return False

    # STEP 2: FILTER & DEDUP
    logger.info("[STEP 2/4] Filter keyword & deduplikasi...")
    clean_data = []
    try:
        from filter_dedup import process
        clean_data = process(raw_data)
        logger.info(f"✓ Filter selesai — {len(clean_data)} lomba bersih")
    except Exception as e:
        logger.error(f"✗ Filter gagal: {e}", exc_info=True)
        clean_data = raw_data
        logger.warning("⚠ Menggunakan data mentah (tanpa filter)")

    if dry_run:
        logger.info("🔧 DRY RUN aktif — berhenti di sini")
        for i, lomba in enumerate(clean_data[:20], 1):
            logger.info(f"  {i}. {lomba.get('nama_lomba', 'N/A')} | {lomba.get('deadline', 'N/A')}")
        return True

    # STEP 3: GOOGLE SHEETS
    logger.info("[STEP 3/4] Sinkronisasi ke Google Sheets...")
    sheets_summary = {"added": 0, "removed": 0}
    sheets_success = False
    
    try:
        from sheets_manager import sync_to_sheets
        sheets_summary = sync_to_sheets(clean_data)
        sheets_success = True
        logger.info(f"✓ Sheets sync — +{sheets_summary['added']} baru, -{sheets_summary['removed']} expired")
    except Exception as e:
        logger.error(f"✗ Google Sheets gagal: {e}", exc_info=True)
        logger.info("Melanjutkan ke Telegram meski Sheets gagal...")

    # STEP 4: TELEGRAM
    logger.info("[STEP 4/4] Mengirim ringkasan ke Telegram...")
    telegram_success = False
    
    try:
        from telegram_bot import send_lomba_update
        from sheets_manager import get_active_lomba
        
        try:
            active_lomba = get_active_lomba()
        except Exception:
            active_lomba = clean_data
            logger.warning("⚠ Menggunakan data lokal (Sheets tidak tersedia)")
        
        periode = datetime.now().strftime("%d %B %Y")
        success = send_lomba_update(active_lomba, periode)
        telegram_success = success
        
        if success:
            logger.info(f"✓ Telegram — {len(active_lomba)} lomba terkirim")
        else:
            logger.warning("✗ Telegram — sebagian pesan gagal")
    except Exception as e:
        logger.error(f"✗ Telegram gagal: {e}", exc_info=True)

    # SELESAI
    duration = (datetime.now() - start).seconds
    logger.info("=" * 60)
    logger.info(
        f"PIPELINE SELESAI dalam {duration}s | "
        f"Scraped: {len(raw_data)} | Bersih: {len(clean_data)} | "
        f"Sheet +{sheets_summary['added']} -{sheets_summary['removed']} | "
        f"Telegram: {'OK' if telegram_success else 'FAIL'}"
    )
    logger.info("=" * 60)
    
    pipeline_success = len(clean_data) > 0 and (sheets_success or telegram_success)
    return pipeline_success


def _notify_error(message: str):
    try:
        from telegram_bot import notify_error
        notify_error(message)
    except Exception:
        pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pipeline Lomba IT")
    parser.add_argument("--dry-run", action="store_true", help="Scrape saja, jangan simpan/kirim")
    parser.add_argument("--test-telegram", action="store_true", help="Test kirim pesan ke Telegram")
    args = parser.parse_args()

    if args.test_telegram:
        logger.info("Mode: TEST TELEGRAM")
        try:
            from telegram_bot import notify
            notify("🧪 Test notifikasi dari pipeline lomba IT!")
            logger.info("✓ Test Telegram terkirim")
        except Exception as e:
            logger.error(f"✗ Test Telegram gagal: {e}")
    else:
        success = run_pipeline(dry_run=args.dry_run)
        sys.exit(0 if success else 1)