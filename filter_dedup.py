"""
filter_dedup.py — Filter keyword & deduplikasi
"""

import logging
import re
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger("filter_dedup")

KEYWORDS = [
    "hackathon", "data science", "programming", "coding",
    "IT", "teknologi", "software", "machine learning",
    "artificial intelligence", "AI", "web", "mobile", "app",
    "akademik", "mahasiswa", "universitas", "competition",
    "contest", "challenge", "lomba", "ctf", "capture the flag",
    "datathon", "code", "developer", "dev",
]


def parse_deadline(deadline_str: str) -> str:
    if not deadline_str or deadline_str == "Cek website":
        return "Cek website"
    
    text = deadline_str.strip()
    
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    patterns = [
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{2}/\d{2}/\d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                date_str = match.group(1)
                if "-" in date_str:
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                elif "/" in date_str:
                    dt = datetime.strptime(date_str, "%d/%m/%Y")
                return dt.strftime("%Y-%m-%d")
            except:
                pass
    
    return "Cek website"


def process(raw_data: List[Dict]) -> List[Dict]:
    if not raw_data:
        return []
    
    filtered = []
    seen = set()
    
    for item in raw_data:
        nama = item.get("nama_lomba", "")
        if not nama:
            continue
        
        nama_lower = nama.lower()
        if not any(kw.lower() in nama_lower for kw in KEYWORDS):
            continue
        
        key = (nama.lower().strip(), item.get("sumber", "").lower().strip())
        if key in seen:
            continue
        seen.add(key)
        
        raw_deadline = item.get("deadline", "Cek website")
        clean_deadline = parse_deadline(raw_deadline)
        
        clean_item = {
            "nama_lomba": nama,
            "deadline": clean_deadline,
            "link": item.get("link", ""),
            "kategori": item.get("kategori", "IT / Teknologi"),
            "sumber": item.get("sumber", ""),
            "status": item.get("status", "Aktif"),
            "tanggal_scrape": item.get("tanggal_scrape", datetime.now().strftime("%Y-%m-%d")),
        }
        
        filtered.append(clean_item)
    
    logger.info(f"Filter: {len(raw_data)} → {len(filtered)} lomba")
    return filtered