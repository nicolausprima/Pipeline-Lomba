"""
filter_dedup.py — Filter keyword & deduplikasi data lomba IT
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# KONFIGURASI
# ──────────────────────────────────────────────

KEYWORDS_INCLUDE = [
    "hackathon", "data science", "programming", "coding",
    "software", "machine learning", "artificial intelligence",
    "ai ", " ai", "web development", "mobile", "app",
    "akademik", "mahasiswa", "universitas", "lomba it",
    "lomba teknologi", "kompetisi", "competition",
]

KEYWORDS_EXCLUDE = [
    "desain grafis", "fotografi", "cerpen", "puisi",
    "memasak", "fashion", "olahraga", "musik",
]


# ──────────────────────────────────────────────
# NORMALISASI
# ──────────────────────────────────────────────

def normalize_title(title: str) -> str:
    """Normalisasi judul untuk perbandingan duplikat."""
    t = title.lower().strip()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def parse_deadline(deadline_str: str) -> Optional[datetime]:
    """Coba parse berbagai format tanggal deadline."""
    formats = [
        "%d %B %Y", "%B %d, %Y", "%d-%m-%Y",
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
        "%d %b %Y",
    ]
    # Bersihkan prefix umum
    clean = re.sub(r"(deadline|submit by|ends|tutup)[:\s]*", "", deadline_str, flags=re.IGNORECASE).strip()

    for fmt in formats:
        try:
            return datetime.strptime(clean, fmt)
        except ValueError:
            continue
    return None


# ──────────────────────────────────────────────
# FILTER
# ──────────────────────────────────────────────

def is_relevant(lomba: dict) -> bool:
    """Kembalikan True jika lomba relevan dengan IT/teknologi."""
    text = f"{lomba.get('nama_lomba', '')} {lomba.get('kategori', '')}".lower()

    # Harus ada minimal 1 keyword include
    has_include = any(kw in text for kw in KEYWORDS_INCLUDE)

    # Tidak boleh ada keyword exclude
    has_exclude = any(kw in text for kw in KEYWORDS_EXCLUDE)

    return has_include and not has_exclude


def is_expired(lomba: dict, grace_days: int = 0) -> bool:
    """Kembalikan True jika deadline sudah lewat."""
    deadline_str = lomba.get("deadline", "")
    dt = parse_deadline(deadline_str)
    if dt is None:
        return False  # Tidak bisa parse → anggap masih aktif (jangan hapus)
    cutoff = datetime.now() - timedelta(days=grace_days)
    return dt < cutoff


# ──────────────────────────────────────────────
# DEDUPLIKASI
# ──────────────────────────────────────────────

def deduplicate(data: list[dict]) -> list[dict]:
    """
    Hapus duplikat berdasarkan:
    1. URL yang sama persis
    2. Judul yang sangat mirip (normalized match)
    """
    seen_links: set[str] = set()
    seen_titles: set[str] = set()
    unique = []

    for lomba in data:
        link = lomba.get("link", "").strip().rstrip("/")
        norm_title = normalize_title(lomba.get("nama_lomba", ""))

        if link and link in seen_links:
            logger.debug(f"Duplikat link: {link}")
            continue

        if norm_title and norm_title in seen_titles:
            logger.debug(f"Duplikat judul: {norm_title}")
            continue

        if link:
            seen_links.add(link)
        if norm_title:
            seen_titles.add(norm_title)

        unique.append(lomba)

    return unique


# ──────────────────────────────────────────────
# MAIN PIPELINE
# ──────────────────────────────────────────────

def process(raw_data: list[dict]) -> list[dict]:
    """
    Jalankan full filter + dedup pipeline.
    Return: daftar lomba bersih yang siap disimpan.
    """
    logger.info(f"Input: {len(raw_data)} lomba")

    # 1. Filter relevansi
    relevant = [d for d in raw_data if is_relevant(d)]
    logger.info(f"Setelah filter keyword: {len(relevant)}")

    # 2. Hapus yang sudah expired
    active = [d for d in relevant if not is_expired(d)]
    logger.info(f"Setelah hapus expired: {len(active)}")

    # 3. Deduplikasi
    unique = deduplicate(active)
    logger.info(f"Setelah deduplikasi: {len(unique)}")

    # 4. Urutkan: yang bisa di-parse deadline duluan
    def sort_key(lomba):
        dt = parse_deadline(lomba.get("deadline", ""))
        return dt if dt else datetime.max

    unique.sort(key=sort_key)

    return unique


if __name__ == "__main__":
    # Test sederhana
    sample = [
        {"nama_lomba": "Hackathon AI 2025", "deadline": "31 Desember 2025", "link": "https://example.com/1", "kategori": "AI", "sumber": "Test", "status": "Aktif", "tanggal_scrape": "2025-01-01"},
        {"nama_lomba": "Hackathon AI 2025", "deadline": "31 Desember 2025", "link": "https://example.com/1", "kategori": "AI", "sumber": "Test2", "status": "Aktif", "tanggal_scrape": "2025-01-01"},  # duplikat
        {"nama_lomba": "Lomba Memasak Nusantara", "deadline": "15 Januari 2026", "link": "https://example.com/2", "kategori": "Kuliner", "sumber": "Test", "status": "Aktif", "tanggal_scrape": "2025-01-01"},  # tidak relevan
        {"nama_lomba": "Data Science Competition", "deadline": "01 Maret 2025", "link": "https://example.com/3", "kategori": "Data Science", "sumber": "Test", "status": "Aktif", "tanggal_scrape": "2025-01-01"},  # expired
    ]
    result = process(sample)
    print(f"Hasil: {len(result)} lomba")
    for r in result:
        print(f"  - {r['nama_lomba']}")