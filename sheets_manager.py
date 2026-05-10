"""
sheets_manager.py — Sinkronisasi dengan Google Sheets
"""

import logging
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict

logger = logging.getLogger("sheets_manager")

# Load config
CONFIG = {}
config_path = os.path.join(os.path.dirname(__file__), 'config.json')
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)

SPREADSHEET_ID = CONFIG.get('google_sheets_id') or os.environ.get('GOOGLE_SHEETS_ID')


def get_sheets_client():
    import gspread
    from google.oauth2.service_account import Credentials
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    
    creds_path = "credentials.json"
    if os.path.exists(creds_path):
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    else:
        creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
        if creds_json:
            creds_info = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        else:
            raise ValueError("Google Sheets credentials tidak ditemukan!")
    
    client = gspread.authorize(creds)
    return client


def sync_to_sheets(lomba_list: List[Dict]) -> Dict:
    if not SPREADSHEET_ID:
        raise ValueError("GOOGLE_SHEETS_ID tidak di-set!")
    
    try:
        client = get_sheets_client()
        
        try:
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
        except Exception as e:
            logger.error(f"Spreadsheet tidak ditemukan: {e}")
            raise
        
        try:
            sheet = spreadsheet.worksheet("Lomba")
        except:
            logger.warning("Worksheet 'Lomba' tidak ditemukan, membuat baru...")
            sheet = spreadsheet.add_worksheet(title="Lomba", rows="1000", cols="7")
            headers = ["Nama Lomba", "Deadline", "Link", "Kategori", "Sumber", "Status", "Tanggal Scrape"]
            sheet.append_row(headers)
        
        try:
            existing = sheet.get_all_records()
            existing_links = {row.get("Link", ""): row for row in existing}
        except:
            existing = []
            existing_links = {}
        
        added = 0
        for lomba in lomba_list:
            link = lomba.get("link", "")
            if link and link not in existing_links and link != "Cek website":
                row = [
                    lomba.get("nama_lomba", ""),
                    lomba.get("deadline", "Cek website"),
                    link,
                    lomba.get("kategori", "IT / Teknologi"),
                    lomba.get("sumber", ""),
                    lomba.get("status", "Aktif"),
                    lomba.get("tanggal_scrape", datetime.now().strftime("%Y-%m-%d")),
                ]
                sheet.append_row(row)
                added += 1
        
        removed = 0
        today = datetime.now()
        rows_to_delete = []
        
        for i, row in enumerate(existing, start=2):
            try:
                deadline_str = row.get("Deadline", "")
                status = row.get("Status", "").lower()
                
                if status == "expired":
                    rows_to_delete.append(i)
                    continue
                
                if deadline_str and deadline_str != "Cek website":
                    try:
                        deadline = datetime.strptime(deadline_str, "%Y-%m-%d")
                        if (today - deadline).days > 30:
                            rows_to_delete.append(i)
                    except:
                        pass
            except:
                pass
        
        for row_idx in sorted(rows_to_delete, reverse=True):
            try:
                sheet.delete_rows(row_idx)
                removed += 1
            except:
                pass
        
        logger.info(f"Sheets: +{added} baru, -{removed} expired")
        return {"added": added, "removed": removed}
        
    except Exception as e:
        logger.error(f"Sheets sync gagal: {e}")
        raise


def get_active_lomba() -> List[Dict]:
    if not SPREADSHEET_ID:
        raise ValueError("GOOGLE_SHEETS_ID tidak di-set!")
    
    try:
        client = get_sheets_client()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        sheet = spreadsheet.worksheet("Lomba")
        records = sheet.get_all_records()
        
        results = []
        for row in records:
            if row.get("Status", "").lower() == "aktif":
                results.append({
                    "nama_lomba": row.get("Nama Lomba", ""),
                    "deadline": row.get("Deadline", "Cek website"),
                    "link": row.get("Link", ""),
                    "kategori": row.get("Kategori", "IT / Teknologi"),
                    "sumber": row.get("Sumber", ""),
                    "status": row.get("Status", "Aktif"),
                    "tanggal_scrape": row.get("Tanggal Scrape", ""),
                })
        
        return results
        
    except Exception as e:
        logger.error(f"Gagal ambil data Sheets: {e}")
        raise