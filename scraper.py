"""
scraper.py — Scraping lomba IT & Data Science
Versi 3.0 — Seimbang IT vs DS
"""

import requests
from bs4 import BeautifulSoup
import time
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

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
    "contest", "challenge", "lomba", "ctf", "capture the flag",
    "datathon", "code", "developer", "dev",
]


def fetch_page(url: str, timeout: int = 20) -> Optional[BeautifulSoup]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        logger.warning(f"Gagal fetch {url}: {e}")
        return None


def fetch_page_playwright(url: str, timeout: int = 30) -> Optional[BeautifulSoup]:
    if not PLAYWRIGHT_AVAILABLE:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers(HEADERS)
            page.set_viewport_size({"width": 1280, "height": 720})
            page.goto(url, wait_until="networkidle", timeout=timeout*1000)
            time.sleep(3)
            html = page.content()
            browser.close()
            return BeautifulSoup(html, "html.parser")
    except Exception as e:
        logger.warning(f"Gagal fetch Playwright {url}: {e}")
        return None


def fetch_json(url: str, timeout: int = 20) -> Optional[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"Gagal fetch JSON {url}: {e}")
        return None


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = " ".join(text.split())
    text = re.sub(r'(HackerEarth|Live|Join Now|Add to Calendar|0+|Loading\.\.\.|Read more)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def safe_link(link: str, base_url: str) -> str:
    if not link:
        return base_url
    if link.startswith("http"):
        return link
    if link.startswith("/"):
        return urljoin(base_url, link)
    if link.startswith("#"):
        return base_url
    return urljoin(base_url, link)


def clean_url_params(url: str) -> str:
    if "?" not in url:
        return url
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def is_noise_link(title: str, link: str, sumber: str) -> bool:
    title_lower = title.lower().strip()
    
    noise_words = [
        "prizes", "freebies", "about us", "contact us", "faq", 
        "terms of service", "privacy policy", "all challenges",
        "all events", "how it works", "pricing", "blog", "careers",
        "opportunities", "search", "login", "register", "home",
        "learn more", "read more", "view all", "see all", "explore",
        "loading", "sponsors", "partners", "schedule", "venue",
        "rules", "judges", "mentors", "resources", "community",
        "host", "organize", "create", "manage", "dashboard",
        "profile", "settings", "logout", "sign up", "sign in",
        "forgot password", "reset password", "verify email",
        "round 2: completed", "round 1: completed", "completed",
        "closed", "ended", "final", "winner", "results",
        "archive", "past", "previous", "old", "expired",
    ]
    
    for word in noise_words:
        if word in title_lower:
            return True
    
    if len(title_lower) < 10 and title_lower in ["events", "challenges", "competitions", "hackathons"]:
        return True
    
    homepages = {
        "AICrowd": ["https://www.aicrowd.com/challenges"],
        "MLH": ["https://www.mlh.io/events", "https://mlh.io/events"],
        "Kaggle": ["https://www.kaggle.com/competitions"],
        "Topcoder": ["https://www.topcoder.com/challenges"],
        "Devpost": ["https://devpost.com/hackathons"],
        "Hackathon.io": ["https://www.hackathon.io/events"],
        "Unstop": ["https://unstop.com/hackathons"],
    }
    
    if sumber in homepages:
        if link in homepages[sumber]:
            return True
    
    return False


def create_item(name: str, deadline: str, link: str, kategori: str, sumber: str) -> dict:
    return {
        "nama_lomba": clean_text(name) or "Tidak diketahui",
        "deadline": clean_text(deadline) or "Cek website",
        "link": link,
        "kategori": kategori,
        "sumber": sumber,
        "status": "Aktif",
        "tanggal_scrape": datetime.now().strftime("%Y-%m-%d"),
    }


# ═══════════════════════════════════════════════
# DATA SCIENCE SOURCES
# ═══════════════════════════════════════════════

def parse_codeforces_api() -> list[dict]:
    data = fetch_json("https://codeforces.com/api/contest.list")
    if not data or data.get("status") != "OK":
        return []
    results = []
    for contest in data.get("result", []):
        if contest.get("phase") != "BEFORE":
            continue
        name = contest.get("name", "")
        deadline_ts = contest.get("startTimeSeconds", 0)
        deadline = datetime.fromtimestamp(deadline_ts).strftime("%Y-%m-%d %H:%M") if deadline_ts else "Cek website"
        cid = contest.get("id", "")
        link = f"https://codeforces.com/contest/{cid}"
        results.append(create_item(name, deadline, link, "Programming Contest", "Codeforces"))
    logger.info(f"  → {len(results)} lomba dari Codeforces API")
    return results


def parse_atcoder_page() -> list[dict]:
    soup = fetch_page("https://atcoder.jp/contests")
    if not soup:
        return []
    results = []
    upcoming_table = soup.select_one("#contest-table-upcoming")
    if upcoming_table:
        rows = upcoming_table.select("tbody tr")
        for row in rows:
            try:
                cells = row.select("td")
                if len(cells) < 2:
                    continue
                time_cell = cells[0].select_one("a")
                start_time = clean_text(time_cell.get_text()) if time_cell else "Cek website"
                name_cell = cells[1].select_one("a")
                if not name_cell:
                    continue
                name = clean_text(name_cell.get_text())
                href = name_cell.get("href", "")
                link = f"https://atcoder.jp{href}" if href.startswith("/") else href
                results.append(create_item(name, start_time, link, "Programming Contest", "AtCoder"))
            except Exception as e:
                logger.debug(f"Skip AtCoder row: {e}")
    logger.info(f"  → {len(results)} lomba dari AtCoder")
    return results


def parse_drivendata(soup: BeautifulSoup) -> list[dict]:
    results = []
    seen = set()
    competitions = soup.select(".competition") or soup.select("[class*='competition']") or soup.select("article")
    for comp in competitions:
        try:
            title_el = comp.select_one("h2, h3, .title")
            if not title_el:
                continue
            title = clean_text(title_el.get_text())
            link_el = comp.select_one("a[href]")
            if not link_el:
                continue
            href = link_el.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            link = safe_link(href, "https://www.drivendata.org")
            if link in ["https://www.drivendata.org", "https://www.drivendata.org/"]:
                continue
            date_el = comp.select_one(".deadline, [class*='deadline'], time")
            date = clean_text(date_el.get_text()) if date_el else "Cek website"
            results.append(create_item(title, date, link, "Data Science", "DrivenData"))
        except Exception as e:
            logger.debug(f"Skip DrivenData: {e}")
    logger.info(f"  → {len(results)} lomba dari DrivenData")
    return results


def parse_kaggle_playwright() -> list[dict]:
    soup = fetch_page_playwright("https://www.kaggle.com/competitions")
    if not soup:
        return []
    results = []
    seen = set()
    for link_el in soup.find_all("a", href=True):
        href = link_el["href"]
        is_competition = ("/c/" in href or "/competitions/" in href)
        if not is_competition:
            continue
        title = clean_text(link_el.get_text())
        if not title or len(title) < 5:
            continue
        if title.lower() in ["competitions", "all competitions", "featured", "search", "datasets"]:
            continue
        link = f"https://www.kaggle.com{href}" if href.startswith("/") else href
        if link in seen:
            continue
        seen.add(link)
        if is_noise_link(title, link, "Kaggle"):
            continue
        deadline = "Cek website"
        parent = link_el.find_parent()
        if parent:
            time_el = parent.select_one("time, [class*='deadline'], [class*='date']")
            if time_el:
                deadline = clean_text(time_el.get_text())
        results.append(create_item(title, deadline, link, "Data Science / AI", "Kaggle"))
    logger.info(f"  → {len(results)} lomba dari Kaggle")
    return results


def parse_aicrowd_playwright() -> list[dict]:
    soup = fetch_page_playwright("https://www.aicrowd.com/challenges")
    if not soup:
        return []
    results = []
    seen = set()
    for link_el in soup.find_all("a", href=True):
        href = link_el["href"]
        if "challenge" not in href.lower():
            continue
        title = clean_text(link_el.get_text())
        if not title or len(title) < 5:
            continue
        link = clean_url_params(safe_link(href, "https://www.aicrowd.com"))
        if link in seen:
            continue
        seen.add(link)
        if is_noise_link(title, link, "AICrowd"):
            continue
        deadline = "Cek website"
        parent = link_el.find_parent()
        if parent:
            date_el = parent.select_one("time, .deadline, [class*='deadline']")
            if date_el:
                deadline = clean_text(date_el.get_text())
        results.append(create_item(title, deadline, link, "AI / Data Science", "AICrowd"))
    logger.info(f"  → {len(results)} lomba dari AICrowd")
    return results


def parse_zindi_api() -> list[dict]:
    data = fetch_json("https://zindi.africa/api/competitions")
    if not data:
        return []
    results = []
    for comp in data.get("results", []):
        try:
            title = comp.get("title", "")
            deadline_str = comp.get("deadline", "")
            slug = comp.get("slug", "")
            link = f"https://zindi.africa/competitions/{slug}"
            deadline = "Cek website"
            if deadline_str:
                try:
                    dt = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
                    deadline = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    deadline = deadline_str
            results.append(create_item(title, deadline, link, "Data Science", "Zindi"))
        except Exception as e:
            logger.debug(f"Skip Zindi: {e}")
    logger.info(f"  → {len(results)} lomba dari Zindi")
    return results


def parse_analytics_vidhya() -> list[dict]:
    soup = fetch_page("https://www.analyticsvidhya.com/blog/category/hackathon/")
    if not soup:
        return []
    results = []
    seen = set()
    articles = soup.select("article") or soup.select(".post") or soup.select("[class*='post']")
    for article in articles:
        try:
            title_el = article.select_one("h2, h3, .entry-title, .post-title")
            if not title_el:
                continue
            title = clean_text(title_el.get_text())
            if not any(kw in title.lower() for kw in ["hackathon", "competition", "challenge", "data science"]):
                continue
            link_el = article.select_one("a[href]")
            if not link_el:
                continue
            href = link_el.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            link = safe_link(href, "https://www.analyticsvidhya.com")
            date_el = article.select_one("time, .date, .published")
            date = clean_text(date_el.get_text()) if date_el else "Cek website"
            results.append(create_item(title, date, link, "Data Science", "Analytics Vidhya"))
        except Exception as e:
            logger.debug(f"Skip Analytics Vidhya: {e}")
    logger.info(f"  → {len(results)} lomba dari Analytics Vidhya")
    return results


# ═══════════════════════════════════════════════
# HACKATHON / IT SOURCES
# ═══════════════════════════════════════════════

def parse_devpost() -> list[dict]:
    soup = fetch_page("https://devpost.com/hackathons")
    if not soup:
        return []
    results = []
    seen = set()
    cards = soup.select("article.challenge-listing") or soup.select("[data-testid='challenge-card']") or soup.select(".challenge-listing")
    for card in cards:
        try:
            title_el = card.select_one("h2, h3, .title")
            if not title_el:
                continue
            title = clean_text(title_el.get_text())
            link_el = card.select_one("a[href]")
            if not link_el:
                continue
            href = link_el.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            link = safe_link(href, "https://devpost.com")
            deadline_el = card.select_one(".submission-period, .dates, [class*='deadline']")
            deadline = clean_text(deadline_el.get_text()) if deadline_el else "Cek website"
            results.append(create_item(title, deadline, link, "Hackathon", "Devpost"))
        except Exception as e:
            logger.debug(f"Skip Devpost: {e}")
    logger.info(f"  → {len(results)} lomba dari Devpost")
    return results


def parse_hackathon_io() -> list[dict]:
    soup = fetch_page("https://www.hackathon.io/events")
    if not soup:
        return []
    results = []
    seen = set()
    events = soup.select(".event") or soup.select("[class*='event']") or soup.select("article")
    for event in events:
        try:
            title_el = event.select_one("h2, h3, .title, [class*='title']")
            if not title_el:
                continue
            title = clean_text(title_el.get_text())
            link_el = event.select_one("a[href]")
            if not link_el:
                continue
            href = link_el.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            link = safe_link(href, "https://www.hackathon.io")
            date_el = event.select_one("time, .date, [class*='date']")
            date = clean_text(date_el.get_text()) if date_el else "Cek website"
            results.append(create_item(title, date, link, "Hackathon", "Hackathon.io"))
        except Exception as e:
            logger.debug(f"Skip Hackathon.io: {e}")
    logger.info(f"  → {len(results)} lomba dari Hackathon.io")
    return results


def parse_unstop() -> list[dict]:
    soup = fetch_page("https://unstop.com/hackathons")
    if not soup:
        return []
    results = []
    seen = set()
    cards = soup.select(".opp-card") or soup.select("[class*='card']") or soup.select("article")
    for card in cards:
        try:
            title_el = card.select_one("h2, h3, .title, [class*='title']")
            if not title_el:
                continue
            title = clean_text(title_el.get_text())
            if not any(kw in title.lower() for kw in ["hackathon", "coding", "competition", "challenge"]):
                continue
            link_el = card.select_one("a[href]")
            if not link_el:
                continue
            href = link_el.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            link = safe_link(href, "https://unstop.com")
            date_el = card.select_one("time, .date, [class*='date']")
            date = clean_text(date_el.get_text()) if date_el else "Cek website"
            results.append(create_item(title, date, link, "Hackathon / IT", "Unstop"))
        except Exception as e:
            logger.debug(f"Skip Unstop: {e}")
    logger.info(f"  → {len(results)} lomba dari Unstop")
    return results


def parse_hackerearth_playwright() -> list[dict]:
    urls = ["https://www.hackerearth.com/challenges/", "https://www.hackerearth.com/practice/"]
    soup = None
    for url in urls:
        soup = fetch_page_playwright(url)
        if soup:
            break
    if not soup:
        return []
    results = []
    seen = set()
    for link_el in soup.find_all("a", href=True):
        href = link_el["href"]
        title = clean_text(link_el.get_text())
        if not title or len(title) < 5:
            continue
        if title.lower() in ["learn more", "read more", "view all", "see all", "explore"]:
            continue
        if any(skip in href.lower() for skip in ["/recruit/", "/practice/", "/blog/", "/about/"]):
            continue
        is_challenge = any(kw in href.lower() for kw in ["challenge", "compete", "contest", "hackathon", "coding"])
        is_challenge_title = any(kw in title.lower() for kw in KEYWORDS)
        if not is_challenge and not is_challenge_title:
            continue
        link = clean_url_params(safe_link(href, "https://www.hackerearth.com"))
        if link in seen:
            continue
        seen.add(link)
        if is_noise_link(title, link, "HackerEarth"):
            continue
        deadline = "Cek website"
        parent = link_el.find_parent()
        if parent:
            date_el = parent.select_one("time, .date, [class*='date']")
            if date_el:
                deadline = clean_text(date_el.get_text())
        results.append(create_item(title, deadline, link, "Programming / Hackathon", "HackerEarth"))
    logger.info(f"  → {len(results)} lomba dari HackerEarth")
    return results


def parse_mlh_playwright() -> list[dict]:
    urls = ["https://mlh.io/seasons/2026/events", "https://mlh.io/seasons/2025/events", "https://mlh.io/events"]
    soup = None
    for url in urls:
        soup = fetch_page_playwright(url)
        if soup:
            break
    if not soup:
        return []
    results = []
    seen = set()
    for link_el in soup.find_all("a", href=True):
        href = link_el["href"]
        if "/events/" not in href:
            continue
        title = clean_text(link_el.get_text())
        if not title or len(title) < 3:
            continue
        if title.lower() in ["events", "all events", "hackathons"]:
            continue
        link = clean_url_params(safe_link(href, "https://mlh.io"))
        if link in seen:
            continue
        seen.add(link)
        if is_noise_link(title, link, "MLH"):
            continue
        deadline = "Cek website"
        parent = link_el.find_parent()
        if parent:
            date_el = parent.select_one("time, .date, [class*='date']")
            if date_el:
                deadline = clean_text(date_el.get_text())
        results.append(create_item(title, deadline, link, "Hackathon", "MLH"))
    logger.info(f"  → {len(results)} lomba dari MLH")
    return results


def parse_topcoder_playwright() -> list[dict]:
    if not PLAYWRIGHT_AVAILABLE:
        return []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers(HEADERS)
            page.set_viewport_size({"width": 1280, "height": 720})
            page.goto("https://www.topcoder.com/challenges", wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            html = page.content()
            browser.close()
            soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        logger.warning(f"Gagal fetch Topcoder: {e}")
        return []
    results = []
    seen = set()
    for link_el in soup.find_all("a", href=True):
        href = link_el["href"]
        if "challenge" not in href.lower():
            continue
        title = clean_text(link_el.get_text())
        if not title or len(title) < 5:
            continue
        link = clean_url_params(safe_link(href, "https://www.topcoder.com"))
        if link in seen:
            continue
        seen.add(link)
        if is_noise_link(title, link, "Topcoder"):
            continue
        results.append(create_item(title, "Cek website", link, "Programming / Design", "Topcoder"))
    logger.info(f"  → {len(results)} lomba dari Topcoder")
    return results


# ═══════════════════════════════════════════════
# NASIONAL / LOKAL INDONESIA
# ═══════════════════════════════════════════════

def parse_compfest() -> list[dict]:
    soup = fetch_page("https://compfest.id")
    if not soup:
        return []
    results = []
    seen_links = set()
    items = soup.select("a[href]")
    for item in items:
        try:
            href = item.get("href", "")
            if not href or href in seen_links:
                continue
            seen_links.add(href)
            skip_patterns = ["/about", "/contact", "/faq", "#", "javascript:", "mailto:", "/assets/"]
            if any(skip in href.lower() for skip in skip_patterns):
                continue
            title = clean_text(item.get_text())
            if not title or len(title) < 10:
                continue
            competition_keywords = ["competition", "lomba", "event", "ctf", "hackathon", "compfest"]
            is_competition = any(kw in href.lower() for kw in competition_keywords)
            if not is_competition and not any(kw in title.lower() for kw in KEYWORDS):
                continue
            link = safe_link(href, "https://compfest.id")
            results.append(create_item(title, "Cek website", link, "IT / Teknologi", "COMPFEST UI"))
        except Exception as e:
            logger.debug(f"Skip COMPFEST: {e}")
    logger.info(f"  → {len(results)} lomba dari COMPFEST UI")
    return results


# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════

def scrape_all() -> list[dict]:
    all_results = []
    
    # DATA SCIENCE SOURCES
    logger.info("═══ DATA SCIENCE SOURCES ═══")
    all_results.extend(parse_codeforces_api())
    time.sleep(1)
    all_results.extend(parse_atcoder_page())
    time.sleep(1)
    
    soup = fetch_page("https://www.drivendata.org/competitions")
    if soup:
        all_results.extend(parse_drivendata(soup))
    time.sleep(1)
    
    all_results.extend(parse_zindi_api())
    time.sleep(1)
    
    soup = fetch_page("https://www.analyticsvidhya.com/blog/category/hackathon/")
    if soup:
        all_results.extend(parse_analytics_vidhya())
    time.sleep(1)
    
    if PLAYWRIGHT_AVAILABLE:
        all_results.extend(parse_kaggle_playwright())
        time.sleep(2)
        all_results.extend(parse_aicrowd_playwright())
        time.sleep(2)
    
    # HACKATHON / IT SOURCES
    logger.info("═══ HACKATHON / IT SOURCES ═══")
    all_results.extend(parse_devpost())
    time.sleep(1)
    all_results.extend(parse_hackathon_io())
    time.sleep(1)
    all_results.extend(parse_unstop())
    time.sleep(1)
    all_results.extend(parse_compfest())
    time.sleep(1)
    
    if PLAYWRIGHT_AVAILABLE:
        all_results.extend(parse_hackerearth_playwright())
        time.sleep(2)
        all_results.extend(parse_mlh_playwright())
        time.sleep(2)
        all_results.extend(parse_topcoder_playwright())
        time.sleep(2)
    
    # CLEANING
    logger.info("═══ MEMBERSIHKAN DATA ═══")
    seen = set()
    unique_results = []
    for item in all_results:
        key = (clean_text(item["nama_lomba"]).lower(), item["sumber"])
        if key not in seen:
            seen.add(key)
            unique_results.append(item)
    
    ds_count = sum(1 for r in unique_results if any(kw in r["kategori"].lower() for kw in ["data", "ai", "analytics", "machine learning"]))
    it_count = len(unique_results) - ds_count
    logger.info(f"Total: {len(unique_results)} lomba | DS/AI: {ds_count} | IT/Programming: {it_count}")
    
    return unique_results


if __name__ == "__main__":
    data = scrape_all()
    print(f"\n{'='*60}")
    print(f"TOTAL LOMBA DITEMUKAN: {len(data)}")
    print(f"{'='*60}")
    for d in data[:20]:
        print(f"\n• {d['nama_lomba']}")
        print(f"  Sumber: {d['sumber']} | Kategori: {d['kategori']}")
        print(f"  Deadline: {d['deadline']} | Link: {d['link']}")