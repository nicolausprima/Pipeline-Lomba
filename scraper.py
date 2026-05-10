"""
scraper.py — Scraping lomba IT dari berbagai sumber web
Sumber: Website lomba IT umum (dapat dikustomisasi)
"""

import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# KONFIGURASI SUMBER WEBSITE
# Tambah atau hapus URL sesuai kebutuhan
# ──────────────────────────────────────────────
SOURCES = [
    # Yang sudah ada sebelumnya...

    # ── INTERNASIONAL ──
    {"name": "Kaggle",       "url": "https://www.kaggle.com/competitions",              "parser": "parse_generic"},
    {"name": "HackerEarth",  "url": "https://www.hackerearth.com/challenges",           "parser": "parse_generic"},
    {"name": "AICrowd",      "url": "https://www.aicrowd.com/challenges",               "parser": "parse_generic"},
    {"name": "DrivenData",   "url": "https://www.drivendata.org/competitions",          "parser": "parse_generic"},
    {"name": "MLH",          "url": "https://mlh.io/seasons/2025/events",               "parser": "parse_generic"},
    {"name": "Topcoder",     "url": "https://www.topcoder.com/challenges",              "parser": "parse_generic"},
    {"name": "Codeforces",   "url": "https://codeforces.com/contests",                  "parser": "parse_generic"},
    {"name": "AtCoder",      "url": "https://atcoder.jp/contests",                      "parser": "parse_generic"},

    # ── NASIONAL ──
    {"name": "Gemastik",     "url": "https://gemastik.kemdikbud.go.id",                 "parser": "parse_generic"},
    {"name": "COMPFEST UI",  "url": "https://compfest.id",                              "parser": "parse_generic"},
    {"name": "Arkavidia ITB","url": "https://arkavidia.itb.ac.id",                      "parser": "parse_generic"},
    {"name": "JOINTS UGM",   "url": "https://joints.ugm.ac.id",                         "parser": "parse_generic"},
    {"name": "Schematics ITS","url":"https://schematics.its.ac.id",                     "parser": "parse_generic"},
    {"name": "Info Lomba",   "url": "https://www.infolombasiswa.com/kategori/teknologi", "parser": "parse_generic"},
    {"name": "Beasiswa-id",  "url": "https://beasiswa.id/lomba-it",                     "parser": "parse_generic"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

KEYWORDS = [
    "hackathon", "data science", "programming", "coding",
    "IT", "teknologi", "software", "machine learning",
    "artificial intelligence", "AI", "web", "mobile", "app",
    "akademik", "mahasiswa", "universitas",
]


# ──────────────────────────────────────────────
# HELPER
# ──────────────────────────────────────────────

def fetch_page(url: str, timeout: int = 15) -> Optional[BeautifulSoup]:
    """Ambil halaman dan kembalikan BeautifulSoup object."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        logger.warning(f"Gagal fetch {url}: {e}")
        return None


def matches_keywords(text: str) -> bool:
    """Cek apakah teks mengandung keyword yang relevan."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in KEYWORDS)


def clean_text(text: str) -> str:
    return " ".join(text.split()).strip()


# ──────────────────────────────────────────────
# PARSERS
# ──────────────────────────────────────────────

def parse_devpost(soup: BeautifulSoup, source_name: str) -> list[dict]:
    """Parser khusus untuk Devpost."""
    results = []
    cards = soup.select("article.challenge-listing")

    for card in cards:
        try:
            title_el = card.select_one("h2")
            link_el = card.select_one("a[href]")
            deadline_el = card.select_one(".submission-period, .dates")

            title = clean_text(title_el.get_text()) if title_el else "Tidak diketahui"
            link = link_el["href"] if link_el else ""
            if link and not link.startswith("http"):
                link = "https://devpost.com" + link
            deadline = clean_text(deadline_el.get_text()) if deadline_el else "Cek website"

            if not matches_keywords(title):
                continue

            results.append({
                "nama_lomba": title,
                "deadline": deadline,
                "link": link,
                "kategori": "Hackathon",
                "sumber": source_name,
                "status": "Aktif",
                "tanggal_scrape": datetime.now().strftime("%Y-%m-%d"),
            })
        except Exception as e:
            logger.debug(f"Skip card devpost: {e}")

    return results


def parse_generic(soup: BeautifulSoup, source_name: str) -> list[dict]:
    """Parser generik — mencari artikel/post yang relevan."""
    results = []

    # Coba berbagai selector umum untuk blog/listing site
    candidates = (
        soup.select("article")
        or soup.select(".post")
        or soup.select(".entry")
        or soup.select("li.item")
        or soup.select(".card")
    )

    for item in candidates:
        try:
            # Ambil judul
            title_el = (
                item.select_one("h1, h2, h3, h4")
                or item.select_one(".title, .entry-title, .post-title")
            )
            if not title_el:
                continue
            title = clean_text(title_el.get_text())

            if not matches_keywords(title):
                continue

            # Ambil link
            link_el = item.select_one("a[href]")
            link = link_el["href"] if link_el else ""

            # Ambil tanggal / deadline (best-effort)
            date_el = item.select_one("time, .date, .deadline, .published")
            deadline = clean_text(date_el.get_text()) if date_el else "Cek website"

            results.append({
                "nama_lomba": title,
                "deadline": deadline,
                "link": link,
                "kategori": "IT / Teknologi",
                "sumber": source_name,
                "status": "Aktif",
                "tanggal_scrape": datetime.now().strftime("%Y-%m-%d"),
            })
        except Exception as e:
            logger.debug(f"Skip item generic: {e}")

    return results


# ──────────────────────────────────────────────
# MAIN SCRAPER
# ──────────────────────────────────────────────

def scrape_all() -> list[dict]:
    """Jalankan semua scraper dan gabungkan hasilnya."""
    all_results = []

    parser_map = {
        "parse_devpost": parse_devpost,
        "parse_generic": parse_generic,
    }

    for source in SOURCES:
        logger.info(f"Scraping: {source['name']} — {source['url']}")
        soup = fetch_page(source["url"])

        if soup is None:
            logger.warning(f"Lewati {source['name']} (gagal fetch)")
            continue

        parser_fn = parser_map.get(source["parser"], parse_generic)
        results = parser_fn(soup, source["name"])
        logger.info(f"  → {len(results)} lomba ditemukan dari {source['name']}")
        all_results.extend(results)

        time.sleep(2)  # Jeda antar request (sopan ke server)

    logger.info(f"Total raw: {len(all_results)} lomba sebelum filter")
    return all_results


if __name__ == "__main__":
    data = scrape_all()
    for d in data:
        print(d)