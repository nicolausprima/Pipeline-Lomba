"""
scraper.py — Scraping lomba IT dari berbagai sumber web
Versi 2.0 — Dengan API resmi & parser spesifik
"""

import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime
from typing import Optional
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# KONFIGURASI
# ──────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

KEYWORDS = [
    "hackathon", "data science", "programming", "coding",
    "IT", "teknologi", "software", "machine learning",
    "artificial intelligence", "AI", "web", "mobile", "app",
    "akademik", "mahasiswa", "universitas", "competition",
    "contest", "challenge", "lomba",
]


# ──────────────────────────────────────────────
# HELPER
# ──────────────────────────────────────────────

def fetch_page(url: str, timeout: int = 20) -> Optional[BeautifulSoup]:
    """Ambil halaman dan kembalikan BeautifulSoup object."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        logger.warning(f"Gagal fetch {url}: {e}")
        return None


def fetch_json(url: str, timeout: int = 20) -> Optional[dict]:
    """Ambil JSON dari API."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"Gagal fetch JSON {url}: {e}")
        return None


def matches_keywords(text: str) -> bool:
    """Cek apakah teks mengandung keyword yang relevan."""
    if not text:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in KEYWORDS)


def clean_text(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.split()).strip()


def safe_link(link: str, base_url: str) -> str:
    """Pastikan link absolute."""
    if not link:
        return base_url
    if link.startswith("http"):
        return link
    if link.startswith("/"):
        from urllib.parse import urljoin
        return urljoin(base_url, link)
    return link


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def create_item(name: str, deadline: str, link: str, kategori: str, sumber: str) -> dict:
    """Buat item lomba standar."""
    return {
        "nama_lomba": clean_text(name) or "Tidak diketahui",
        "deadline": clean_text(deadline) or "Cek website",
        "link": link,
        "kategori": kategori,
        "sumber": sumber,
        "status": "Aktif",
        "tanggal_scrape": now_str(),
    }


# ──────────────────────────────────────────────
# API PARSERS (Lebih Reliable)
# ──────────────────────────────────────────────

def parse_codeforces_api() -> list[dict]:
    """Ambil kontes dari Codeforces API."""
    data = fetch_json("https://codeforces.com/api/contest.list")
    if not data or data.get("status") != "OK":
        return []
    
    results = []
    for contest in data.get("result", []):
        if contest.get("phase") != "BEFORE":
            continue
        
        name = contest.get("name", "")
        # Codeforces contest = programming, selalu relevan
        deadline_ts = contest.get("startTimeSeconds", 0)
        deadline = datetime.fromtimestamp(deadline_ts).strftime("%Y-%m-%d %H:%M") if deadline_ts else "Cek website"
        
        cid = contest.get("id", "")
        link = f"https://codeforces.com/contest/{cid}"
        
        results.append(create_item(
            name=name,
            deadline=deadline,
            link=link,
            kategori="Programming Contest",
            sumber="Codeforces"
        ))
    
    logger.info(f"  → {len(results)} lomba dari Codeforces API")
    return results


def parse_atcoder_api() -> list[dict]:
    """Ambil kontes dari AtCoder API (unofficial tapi stabil)."""
    data = fetch_json("https://kenkoooo.com/atcoder/resources/contests.json")
    if not data:
        return []
    
    results = []
    now = datetime.now()
    
    for contest in data:
        start_time_str = contest.get("start_epoch_second", 0)
        if not start_time_str:
            continue
        
        start_time = datetime.fromtimestamp(start_time_str)
        if start_time < now:
            continue  # Skip kontes yang sudah lewat
        
        name = contest.get("title", "")
        cid = contest.get("id", "")
        link = f"https://atcoder.jp/contests/{cid}"
        deadline = start_time.strftime("%Y-%m-%d %H:%M")
        
        results.append(create_item(
            name=name,
            deadline=deadline,
            link=link,
            kategori="Programming Contest",
            sumber="AtCoder"
        ))
    
    logger.info(f"  → {len(results)} lomba dari AtCoder API")
    return results


def parse_mlh_api() -> list[dict]:
    """Ambil hackathon dari MLH API."""
    # MLH sometimes has a JSON endpoint, try scraping their events page with better selectors
    soup = fetch_page("https://mlh.io/seasons/2026/events")
    if not soup:
        # Fallback to 2025
        soup = fetch_page("https://mlh.io/seasons/2025/events")
    
    if not soup:
        return []
    
    results = []
    # MLH events are usually in specific containers
    events = soup.select(".event") or soup.select("[class*='event']") or soup.select("a[href*='/events/']")
    
    for event in events:
        try:
            title_el = event.select_one("h3, .event-name, [class*='name']")
            if not title_el:
                continue
            
            title = clean_text(title_el.get_text())
            link_el = event if event.name == "a" else event.select_one("a[href]")
            link = safe_link(link_el["href"] if link_el else "", "https://mlh.io") if link_el else "https://mlh.io"
            
            date_el = event.select_one(".event-date, [class*='date'], time")
            date = clean_text(date_el.get_text()) if date_el else "Cek website"
            
            results.append(create_item(
                name=title,
                deadline=date,
                link=link,
                kategori="Hackathon",
                sumber="MLH"
            ))
        except Exception as e:
            logger.debug(f"Skip MLH event: {e}")
    
    logger.info(f"  → {len(results)} lomba dari MLH")
    return results


# ──────────────────────────────────────────────
# HTML PARSERS (Spesifik per Situs)
# ──────────────────────────────────────────────

def parse_kaggle(soup: BeautifulSoup) -> list[dict]:
    """Parser khusus untuk Kaggle Competitions."""
    results = []
    
    # Kaggle competitions page structure (check current structure)
    # Usually competitions are in list items or specific divs
    competitions = soup.select("[data-testid='competition-item']") or \
                 soup.select(".competition-item") or \
                 soup.select("[class*='competition']")
    
    if not competitions:
        # Fallback: look for any links to /competitions/
        links = soup.select("a[href*='/competitions/']")
        seen = set()
        for link in links:
            href = link.get("href", "")
            if href in seen or not href.startswith("/c/"):
                continue
            seen.add(href)
            
            title = clean_text(link.get_text())
            if not title or len(title) < 5:
                continue
            
            full_link = f"https://www.kaggle.com{href}"
            results.append(create_item(
                name=title,
                deadline="Cek website",
                link=full_link,
                kategori="Data Science / AI",
                sumber="Kaggle"
            ))
    
    logger.info(f"  → {len(results)} lomba dari Kaggle")
    return results


def parse_devpost(soup: BeautifulSoup) -> list[dict]:
    """Parser khusus untuk Devpost."""
    results = []
    cards = soup.select("article.challenge-listing") or soup.select("[data-testid='challenge-card']")
    
    for card in cards:
        try:
            title_el = card.select_one("h2, h3, .title")
            link_el = card.select_one("a[href]")
            deadline_el = card.select_one(".submission-period, .dates, [class*='deadline']")
            
            title = clean_text(title_el.get_text()) if title_el else "Tidak diketahui"
            link = safe_link(link_el["href"] if link_el else "", "https://devpost.com")
            deadline = clean_text(deadline_el.get_text()) if deadline_el else "Cek website"
            
            if not matches_keywords(title):
                continue
            
            results.append(create_item(
                name=title,
                deadline=deadline,
                link=link,
                kategori="Hackathon",
                sumber="Devpost"
            ))
        except Exception as e:
            logger.debug(f"Skip card devpost: {e}")
    
    logger.info(f"  → {len(results)} lomba dari Devpost")
    return results


def parse_hackerearth(soup: BeautifulSoup) -> list[dict]:
    """Parser untuk HackerEarth."""
    results = []
    # HackerEarth challenges are usually in specific cards
    cards = soup.select(".challenge-card") or soup.select("[class*='challenge']") or soup.select(".event")
    
    for card in cards:
        try:
            title_el = card.select_one("h3, .title, [class*='title']")
            if not title_el:
                continue
            
            title = clean_text(title_el.get_text())
            link_el = card.select_one("a[href]")
            link = safe_link(link_el["href"] if link_el else "", "https://www.hackerearth.com")
            
            date_el = card.select_one(".date, [class*='date'], time")
            date = clean_text(date_el.get_text()) if date_el else "Cek website"
            
            results.append(create_item(
                name=title,
                deadline=date,
                link=link,
                kategori="Programming / Hackathon",
                sumber="HackerEarth"
            ))
        except Exception as e:
            logger.debug(f"Skip HackerEarth card: {e}")
    
    logger.info(f"  → {len(results)} lomba dari HackerEarth")
    return results


def parse_aicrowd(soup: BeautifulSoup) -> list[dict]:
    """Parser untuk AICrowd."""
    results = []
    challenges = soup.select(".challenge-card") or soup.select("[class*='challenge']") or soup.select("article")
    
    for challenge in challenges:
        try:
            title_el = challenge.select_one("h2, h3, .title")
            if not title_el:
                continue
            
            title = clean_text(title_el.get_text())
            link_el = challenge.select_one("a[href]")
            link = safe_link(link_el["href"] if link_el else "", "https://www.aicrowd.com")
            
            date_el = challenge.select_one(".deadline, [class*='deadline'], time")
            date = clean_text(date_el.get_text()) if date_el else "Cek website"
            
            results.append(create_item(
                name=title,
                deadline=date,
                link=link,
                kategori="AI / Data Science",
                sumber="AICrowd"
            ))
        except Exception as e:
            logger.debug(f"Skip AICrowd card: {e}")
    
    logger.info(f"  → {len(results)} lomba dari AICrowd")
    return results


def parse_drivendata(soup: BeautifulSoup) -> list[dict]:
    """Parser untuk DrivenData."""
    results = []
    competitions = soup.select(".competition") or soup.select("[class*='competition']") or soup.select("article")
    
    for comp in competitions:
        try:
            title_el = comp.select_one("h2, h3, .title")
            if not title_el:
                continue
            
            title = clean_text(title_el.get_text())
            link_el = comp.select_one("a[href]")
            link = safe_link(link_el["href"] if link_el else "", "https://www.drivendata.org")
            
            date_el = comp.select_one(".deadline, [class*='deadline'], time")
            date = clean_text(date_el.get_text()) if date_el else "Cek website"
            
            results.append(create_item(
                name=title,
                deadline=date,
                link=link,
                kategori="Data Science",
                sumber="DrivenData"
            ))
        except Exception as e:
            logger.debug(f"Skip DrivenData card: {e}")
    
    logger.info(f"  → {len(results)} lomba dari DrivenData")
    return results


def parse_topcoder(soup: BeautifulSoup) -> list[dict]:
    """Parser untuk Topcoder."""
    results = []
    challenges = soup.select(".challenge") or soup.select("[class*='challenge']") or soup.select("article")
    
    for challenge in challenges:
        try:
            title_el = challenge.select_one("h2, h3, .title")
            if not title_el:
                continue
            
            title = clean_text(title_el.get_text())
            link_el = challenge.select_one("a[href]")
            link = safe_link(link_el["href"] if link_el else "", "https://www.topcoder.com")
            
            date_el = challenge.select_one(".deadline, [class*='deadline'], time")
            date = clean_text(date_el.get_text()) if date_el else "Cek website"
            
            results.append(create_item(
                name=title,
                deadline=date,
                link=link,
                kategori="Programming / Design",
                sumber="Topcoder"
            ))
        except Exception as e:
            logger.debug(f"Skip Topcoder card: {e}")
    
    logger.info(f"  → {len(results)} lomba dari Topcoder")
    return results


# ──────────────────────────────────────────────
# FALLBACK GENERIC (Untuk situs yang tidak punya parser spesifik)
# ──────────────────────────────────────────────

def parse_generic(soup: BeautifulSoup, source_name: str, base_url: str) -> list[dict]:
    """Parser generik — last resort."""
    results = []
    
    candidates = (
        soup.select("article")
        or soup.select(".post")
        or soup.select(".entry")
        or soup.select("li.item")
        or soup.select(".card")
        or soup.select("[class*='item']")
        or soup.select("[class*='card']")
    )
    
    for item in candidates:
        try:
            title_el = (
                item.select_one("h1, h2, h3, h4")
                or item.select_one(".title, .entry-title, .post-title")
            )
            if not title_el:
                continue
            
            title = clean_text(title_el.get_text())
            if len(title) < 5:
                continue
            
            link_el = item.select_one("a[href]")
            link = safe_link(link_el["href"] if link_el else "", base_url)
            
            date_el = item.select_one("time, .date, .deadline, .published")
            deadline = clean_text(date_el.get_text()) if date_el else "Cek website"
            
            results.append(create_item(
                name=title,
                deadline=deadline,
                link=link,
                kategori="IT / Teknologi",
                sumber=source_name
            ))
        except Exception as e:
            logger.debug(f"Skip item generic: {e}")
    
    logger.info(f"  → {len(results)} lomba dari {source_name} (generic)")
    return results


# ──────────────────────────────────────────────
# MAIN SCRAPER
# ──────────────────────────────────────────────

def scrape_all() -> list[dict]:
    """Jalankan semua scraper dan gabungkan hasilnya."""
    all_results = []
    
    # ── API-based sources (paling reliable) ──
    logger.info("STEP 1: Scraping dari API resmi...")
    all_results.extend(parse_codeforces_api())
    time.sleep(1)
    all_results.extend(parse_atcoder_api())
    time.sleep(1)
    
    # ── HTML-based sources ──
    logger.info("STEP 2: Scraping dari HTML...")
    
    # Kaggle
    logger.info("Scraping: Kaggle")
    soup = fetch_page("https://www.kaggle.com/competitions")
    if soup:
        all_results.extend(parse_kaggle(soup))
    time.sleep(2)
    
    # MLH
    logger.info("Scraping: MLH")
    all_results.extend(parse_mlh_api())
    time.sleep(2)
    
    # HackerEarth (might get 403, handle gracefully)
    logger.info("Scraping: HackerEarth")
    soup = fetch_page("https://www.hackerearth.com/challenges")
    if soup:
        all_results.extend(parse_hackerearth(soup))
    time.sleep(2)
    
    # AICrowd
    logger.info("Scraping: AICrowd")
    soup = fetch_page("https://www.aicrowd.com/challenges")
    if soup:
        all_results.extend(parse_aicrowd(soup))
    time.sleep(2)
    
    # DrivenData
    logger.info("Scraping: DrivenData")
    soup = fetch_page("https://www.drivendata.org/competitions")
    if soup:
        all_results.extend(parse_drivendata(soup))
    time.sleep(2)
    
    # Topcoder
    logger.info("Scraping: Topcoder")
    soup = fetch_page("https://www.topcoder.com/challenges")
    if soup:
        all_results.extend(parse_topcoder(soup))
    time.sleep(2)
    
    # ── NASIONAL (perlu cek URL yang benar) ──
    # NOTE: Domain berikut perlu dicek ulang karena DNS gagal di log
    
    # COMPFEST UI (coba URL alternatif)
    logger.info("Scraping: COMPFEST UI")
    soup = fetch_page("https://compfest.id")
    if soup:
        all_results.extend(parse_generic(soup, "COMPFEST UI", "https://compfest.id"))
    else:
        # Coba subdomain atau tahun tertentu
        soup = fetch_page("https://compfest.id/competition")
        if soup:
            all_results.extend(parse_generic(soup, "COMPFEST UI", "https://compfest.id"))
    time.sleep(2)
    
    logger.info(f"Total raw: {len(all_results)} lomba sebelum filter")
    return all_results


if __name__ == "__main__":
    data = scrape_all()
    print(f"\n{'='*50}")
    print(f"TOTAL LOMBA DITEMUKAN: {len(data)}")
    print(f"{'='*50}")
    for d in data[:10]:  # Print first 10
        print(f"\n• {d['nama_lomba']}")
        print(f"  Sumber: {d['sumber']} | Deadline: {d['deadline']}")
        print(f"  Link: {d['link']}")