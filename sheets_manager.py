"""
sheets_manager.py — Sinkronisasi data lomba ke Google Sheets
Library: gspread + google-auth

Setup awal:
  pip install gspread google-auth

Cara dapat credentials:
  1. Buka https://console.cloud.google.com
  2. Buat project baru → Enable "Google Sheets API" & "Google Drive API"
  3. IAM & Admin → Service Accounts → Create → Download JSON
  4. Share Google Sheet kamu ke email service account (editor)
  5. Taruh file JSON di path CREDENTIALS_FILE di bawah
"""

import logging
from datetime import datetime
from typing import Optional
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# KONFIGURASI — EDIT BAGIAN INI
# ──────────────────────────────────────────────

CREDENTIALS_FILE = "credentials.json"          # Path ke file JSON service account
SPREADSHEET_NAME = "Informasi Lomba Nasional dan Internasional"         # Nama Google Sheets kamu
WORKSHEET_NAME   = "Info Lomba"                     # Nama sheet/tab

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Kolom header (urutan ini yang akan muncul di Sheets)
HEADERS = [
    "Nama Lomba", "Deadline", "Link", "Kategori",
    "Sumber", "Status", "Tanggal Scrape",
]

# Mapping dict key → header kolom
KEY_MAP = {
    "nama_lomba":     "Nama Lomba",
    "deadline":       "Deadline",
    "link":           "Link",
    "kategori":       "Kategori",
    "sumber":         "Sumber",
    "status":         "Status",
    "tanggal_scrape": "Tanggal Scrape",
}


# ──────────────────────────────────────────────
# CLIENT
# ──────────────────────────────────────────────

def get_client() -> gspread.Client:
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def get_worksheet() -> gspread.Worksheet:
    client = get_client()
    try:
        sh = client.open(SPREADSHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = client.create(SPREADSHEET_NAME)
        logger.info(f"Spreadsheet baru dibuat: {SPREADSHEET_NAME}")

    try:
        ws = sh.worksheet(WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=len(HEADERS))
        ws.append_row(HEADERS)
        logger.info(f"Worksheet baru dibuat: {WORKSHEET_NAME}")

    return ws


# ──────────────────────────────────────────────
# READ
# ──────────────────────────────────────────────

def read_existing(ws: gspread.Worksheet) -> list[dict]:
    """Baca semua data yang ada di sheet."""
    records = ws.get_all_records()
    return records


def get_existing_links(ws: gspread.Worksheet) -> set[str]:
    """Ambil semua link yang sudah ada (untuk cek duplikat)."""
    records = read_existing(ws)
    return {r.get("Link", "").strip() for r in records if r.get("Link")}


# ──────────────────────────────────────────────
# WRITE
# ──────────────────────────────────────────────

def lomba_to_row(lomba: dict) -> list:
    """Konversi dict lomba ke list sesuai urutan HEADERS."""
    return [lomba.get(k, "") for k in KEY_MAP.keys()]


def add_new_lomba(ws: gspread.Worksheet, new_data: list[dict]) -> int:
    """
    Tambah lomba baru ke sheet.
    Skip yang linknya sudah ada.
    Return jumlah baris yang ditambahkan.
    """
    existing_links = get_existing_links(ws)
    rows_to_add = []

    for lomba in new_data:
        link = lomba.get("link", "").strip()
        if link and link in existing_links:
            logger.debug(f"Skip (sudah ada): {lomba.get('nama_lomba')}")
            continue
        rows_to_add.append(lomba_to_row(lomba))
        if link:
            existing_links.add(link)

    if rows_to_add:
        ws.append_rows(rows_to_add, value_input_option="USER_ENTERED")
        logger.info(f"Ditambahkan {len(rows_to_add)} lomba baru ke Sheets")
    else:
        logger.info("Tidak ada lomba baru untuk ditambahkan")

    return len(rows_to_add)


def remove_expired(ws: gspread.Worksheet) -> int:
    """
    Hapus baris lomba yang statusnya 'Expired' atau deadline sudah lewat.
    Return jumlah baris yang dihapus.
    """
    from filter_dedup import parse_deadline, is_expired

    records = ws.get_all_records()
    rows_to_delete = []

    for i, record in enumerate(records):
        # +2 karena: row 1 = header, enumerate mulai dari 0
        row_index = i + 2
        lomba = {
            "deadline": record.get("Deadline", ""),
            "status": record.get("Status", ""),
        }
        if record.get("Status") == "Expired" or is_expired(lomba):
            rows_to_delete.append(row_index)

    # Hapus dari bawah agar index tidak bergeser
    for row_index in sorted(rows_to_delete, reverse=True):
        ws.delete_rows(row_index)
        logger.debug(f"Hapus baris {row_index}")

    if rows_to_delete:
        logger.info(f"Dihapus {len(rows_to_delete)} lomba expired dari Sheets")
    return len(rows_to_delete)


# ──────────────────────────────────────────────
# SYNC UTAMA
# ──────────────────────────────────────────────

def sync_to_sheets(new_data: list[dict]) -> dict:
    """
    Sinkronisasi penuh:
    1. Buka worksheet
    2. Tambah data baru
    3. Hapus yang expired
    Return: ringkasan hasil
    """
    logger.info("Memulai sinkronisasi ke Google Sheets...")
    ws = get_worksheet()

    added   = add_new_lomba(ws, new_data)
    removed = remove_expired(ws)

    summary = {
        "added":   added,
        "removed": removed,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    logger.info(f"Sync selesai: +{added} ditambah, -{removed} dihapus")
    return summary


def get_active_lomba() -> list[dict]:
    """Ambil semua lomba aktif dari Sheets (untuk format pesan Telegram)."""
    ws = get_worksheet()
    records = read_existing(ws)
    return [r for r in records if r.get("Status", "").lower() != "expired"]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Test koneksi
    try:
        ws = get_worksheet()
        data = read_existing(ws)
        print(f"Koneksi berhasil. {len(data)} baris ditemukan.")
    except Exception as e:
        print(f"Gagal koneksi: {e}")
        print("Pastikan credentials.json sudah diatur dengan benar.")