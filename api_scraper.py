"""
api_scrapers.py — Scraping lomba IT via API resmi
Semua sumber di sini tidak butuh JavaScript dan tidak diblokir GitHub Actions.

Yang TIDAK butuh setup apapun (langsung jalan):
  - Codeforces
  - AtCoder
  - HackerRank (public API)
  - Devpost
  - DrivenData

Yang butuh akun tapi gratis:
  - Kaggle (download kaggle.json dari akun kamu)
"""

import requests
import logging
from datetime import datetime, timezone
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
TODAY  = datetime.now(timezone.utc)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fmt_date(dt: Optional[datetime]) -> str:
    if dt is None:
        return "Cek website"
    return dt.strftime("%d %B %Y")


def is_active(dt: Optional[datetime]) -> bool:
    if dt is None:
        return True
    return dt > TODAY


def make_entry(nama, deadline, link, kategori, sumber, status="Aktif") -> dict:
    return {
        "nama_lomba":     nama,
        "deadline":       deadline,
        "link":           link,
        "kategori":       kategori,
        "sumber":         sumber,
        "status":         status,
        "tanggal_scrape": TODAY.strftime("%Y-%m-%d"),
    }


# ── 1. CODEFORCES ────────────────────────────

def scrape_codeforces() -> list[dict]:
    try:
        resp = requests.get(
            "https://codeforces.com/api/contest.list?gym=false",
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK":
            return []

        results = []
        for c in data.get("result", []):
            if c.get("phase") not in ("BEFORE", "CODING"):
                continue

            start_ts   = c.get("startTimeSeconds", 0)
            duration_s = c.get("durationSeconds", 0)
            start_dt   = datetime.fromtimestamp(start_ts, tz=timezone.utc) if start_ts else None
            end_dt     = datetime.fromtimestamp(start_ts + duration_s, tz=timezone.utc) if start_ts else None

            if not is_active(end_dt):
                continue

            type_map = {"CF": "CF style", "IOI": "IOI style", "ICPC": "ICPC style"}
            ctype    = type_map.get(c.get("type", "CF"), "CF style")

            results.append(make_entry(
                nama     = c.get("name", "Codeforces Contest"),
                deadline = start_dt.strftime("%d %B %Y, %H:%M UTC") if start_dt else "Cek website",
                link     = f"https://codeforces.com/contests/{c.get('id')}",
                kategori = f"Competitive Programming ({ctype})",
                sumber   = "Codeforces",
                status   = "Aktif" if c.get("phase") == "CODING" else "Upcoming",
            ))

        logger.info(f"Codeforces: {len(results)} contest")
        return results
    except Exception as e:
        logger.error(f"Codeforces error: {e}")
        return []


# ── 2. ATCODER ───────────────────────────────

def scrape_atcoder() -> list[dict]:
    try:
        resp = requests.get(
            "https://atcoder.jp/contests/?lang=en",
            headers=HEADERS, timeout=15
        )
        resp.raise_for_status()
        soup    = BeautifulSoup(resp.text, "html.parser")
        results = []

        for div_id in ("contest-table-upcoming", "contest-table-action"):
            table = soup.find("div", id=div_id)
            if not table:
                continue
            for row in table.select("tbody tr"):
                cols = row.select("td")
                if len(cols) < 2:
                    continue
                start   = cols[0].get_text(strip=True)
                name_el = cols[1].select_one("a")
                if not name_el:
                    continue
                results.append(make_entry(
                    nama     = name_el.get_text(strip=True),
                    deadline = start,
                    link     = "https://atcoder.jp" + name_el["href"],
                    kategori = "Competitive Programming (AtCoder)",
                    sumber   = "AtCoder",
                    status   = "Upcoming",
                ))

        logger.info(f"AtCoder: {len(results)} contest")
        return results
    except Exception as e:
        logger.error(f"AtCoder error: {e}")
        return []


# ── 3. HACKERRANK ────────────────────────────

def scrape_hackerrank() -> list[dict]:
    try:
        resp = requests.get(
            "https://www.hackerrank.com/rest/contests/upcoming?limit=20&offset=0",
            headers=HEADERS, timeout=15
        )
        resp.raise_for_status()
        data    = resp.json()
        results = []

        for c in data.get("models", []):
            end_time = c.get("epoch_endtime", 0)
            end_dt   = datetime.fromtimestamp(end_time, tz=timezone.utc) if end_time else None
            if not is_active(end_dt):
                continue
            slug = c.get("slug", "")
            results.append(make_entry(
                nama     = c.get("name", "HackerRank Contest"),
                deadline = fmt_date(end_dt),
                link     = f"https://www.hackerrank.com/contests/{slug}",
                kategori = "Programming Contest",
                sumber   = "HackerRank",
            ))

        logger.info(f"HackerRank: {len(results)} contest")
        return results
    except Exception as e:
        logger.error(f"HackerRank error: {e}")
        return []


# ── 4. DEVPOST ───────────────────────────────

def scrape_devpost() -> list[dict]:
    try:
        resp = requests.get(
            "https://devpost.com/hackathons?challenge_type=online&status=upcoming",
            headers=HEADERS, timeout=15
        )
        resp.raise_for_status()
        soup    = BeautifulSoup(resp.text, "html.parser")
        results = []

        for card in soup.select("article.challenge-listing"):
            title_el    = card.select_one("h2")
            link_el     = card.select_one("a[href]")
            deadline_el = card.select_one(".submission-period, .dates, time")
            if not title_el:
                continue
            link = link_el["href"] if link_el else ""
            if link and not link.startswith("http"):
                link = "https://devpost.com" + link
            results.append(make_entry(
                nama     = title_el.get_text(strip=True),
                deadline = deadline_el.get_text(strip=True) if deadline_el else "Cek website",
                link     = link,
                kategori = "Hackathon",
                sumber   = "Devpost",
            ))

        logger.info(f"Devpost: {len(results)} hackathon")
        return results
    except Exception as e:
        logger.error(f"Devpost error: {e}")
        return []


# ── 5. DRIVENDATA ────────────────────────────

def scrape_drivendata() -> list[dict]:
    try:
        resp = requests.get(
            "https://www.drivendata.org/competitions/",
            headers=HEADERS, timeout=15
        )
        resp.raise_for_status()
        soup    = BeautifulSoup(resp.text, "html.parser")
        results = []

        for card in soup.select(".competition-card, .challenge-card, article"):
            title_el    = card.select_one("h3, h4, .competition-title")
            link_el     = card.select_one("a[href]")
            deadline_el = card.select_one(".deadline, time, .date")
            if not title_el:
                continue
            link = link_el["href"] if link_el else ""
            if link and not link.startswith("http"):
                link = "https://www.drivendata.org" + link
            results.append(make_entry(
                nama     = title_el.get_text(strip=True),
                deadline = deadline_el.get_text(strip=True) if deadline_el else "Cek website",
                link     = link,
                kategori = "Data Science / AI for Good",
                sumber   = "DrivenData",
            ))

        logger.info(f"DrivenData: {len(results)} kompetisi")
        return results
    except Exception as e:
        logger.error(f"DrivenData error: {e}")
        return []


# ── 6. KAGGLE ────────────────────────────────

def scrape_kaggle(max_results: int = 30) -> list[dict]:
    """
    Butuh setup sekali:
      1. kaggle.com → Account → API → Create New Token → download kaggle.json
      2. Mac/Linux: ~/.kaggle/kaggle.json
         Windows: C:\\Users\\NAMA\\.kaggle\\kaggle.json
      3. Di GitHub: tambah secret KAGGLE_USERNAME dan KAGGLE_KEY
    """
    try:
        from kaggle.api.kaggle_api_extended import KaggleApiExtended
        api = KaggleApiExtended()
        api.authenticate()

        competitions = api.competitions_list(sort_by="deadline")
        results      = []

        for comp in competitions[:max_results]:
            deadline_dt = None
            if hasattr(comp, "deadline") and comp.deadline:
                if isinstance(comp.deadline, datetime):
                    deadline_dt = comp.deadline.replace(tzinfo=timezone.utc)
                else:
                    try:
                        deadline_dt = datetime.fromisoformat(str(comp.deadline)).replace(tzinfo=timezone.utc)
                    except Exception:
                        pass

            if not is_active(deadline_dt):
                continue

            tags = str(getattr(comp, "tags", "")).lower()
            if "nlp" in tags or "text" in tags:
                kategori = "NLP / Text"
            elif "vision" in tags or "image" in tags:
                kategori = "Computer Vision"
            else:
                kategori = "Data Science / ML"

            ref = getattr(comp, "ref", "")
            results.append(make_entry(
                nama     = getattr(comp, "title", "Kaggle Competition"),
                deadline = fmt_date(deadline_dt),
                link     = f"https://www.kaggle.com/competitions/{ref}",
                kategori = kategori,
                sumber   = "Kaggle",
            ))

        logger.info(f"Kaggle: {len(results)} kompetisi aktif")
        return results

    except ImportError:
        logger.warning("Kaggle library tidak ada — skip")
        return []
    except Exception as e:
        logger.error(f"Kaggle error: {e}")
        return []


# ── GABUNGKAN SEMUA ──────────────────────────

def scrape_all_api() -> list[dict]:
    all_results = []
    scrapers = [
        ("Codeforces", scrape_codeforces),
        ("AtCoder",    scrape_atcoder),
        ("HackerRank", scrape_hackerrank),
        ("Devpost",    scrape_devpost),
        ("DrivenData", scrape_drivendata),
        ("Kaggle",     scrape_kaggle),
    ]
    for name, fn in scrapers:
        logger.info(f"Scraping: {name}...")
        try:
            results = fn()
            logger.info(f"  → {len(results)} item dari {name}")
            all_results.extend(results)
        except Exception as e:
            logger.error(f"  ✗ {name} gagal: {e}")

    logger.info(f"Total: {len(all_results)} lomba dari semua sumber")
    return all_results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    data = scrape_all_api()
    print(f"\nTotal: {len(data)} lomba\n")
    for d in data:
        print(f"  [{d['sumber']}] {d['nama_lomba']} | {d['deadline']}")