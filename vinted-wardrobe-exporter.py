#!/usr/bin/env python3
import json
import logging
import re
import time
import random
import requests
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from tqdm import tqdm
from bs4 import BeautifulSoup
from requests import HTTPError

def load_cookies_from_file() -> dict[str, str]:
    default_path = Path(__file__).parent / "cookies.json"
    prompt = f"Path to cookies JSON file [{default_path.name}]: "
    path_input = input(prompt).strip() or default_path.name
    cookie_file = Path(path_input)
    if not cookie_file.exists():
        logging.error("Cookie file not found: %s", cookie_file)
        raise SystemExit(1)
    raw = cookie_file.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logging.error("Failed to parse JSON from %s", cookie_file)
        raise SystemExit(1)
    cookies = data.get("Request Cookies", data)
    logging.info("Loaded %d cookies from %s", len(cookies), cookie_file.name)
    return cookies

def make_session(base_url: str, cookies: dict[str, str]) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": base_url,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ),
    })
    domain = urlparse(base_url).hostname
    for name, value in cookies.items():
        session.cookies.set(name, value, domain=domain)
    return session

def fetch_wardrobe(session: requests.Session, base_url: str, profile_id: str) -> list[dict]:
    items = []
    page, per_page = 1, 50
    while True:
        url = f"{base_url}/web/api/core/wardrobe/{profile_id}/items"
        resp = session.get(url, params={"page": page, "per_page": per_page, "order": "newest_first"}, timeout=30)
        resp.raise_for_status()
        batch = resp.json().get("items", [])
        if not batch:
            break
        items.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return items

def get_item_details(session: requests.Session, base_url: str, item_path: str) -> dict:
    url = f"{base_url}/web/api/core/wardrobe{item_path}"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    detail = data.get("item", {})
    # merge root-level stats and URL into detail
    for key in ("view_count", "favourite_count", "url"):
        if key in data:
            detail[key] = data[key]
    return detail

def enrich_detail_with_html(session: requests.Session, base_url: str, detail: dict, item_path: str) -> dict:
    html_url = detail.get("url") or f"{base_url}{item_path}"
    resp = session.get(html_url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Description
    desc = soup.find("div", attrs={"itemprop": "description"})
    if desc:
        detail["description"] = desc.get_text("\n", strip=True)

    # Price
    price = soup.find(attrs={"data-testid": "item-price"})
    if price and price.p:
        detail["price"] = price.p.get_text(strip=True)

    # Size
    size = soup.find(attrs={"data-testid": "item-attributes-size"})
    if size:
        sp = size.find(attrs={"itemprop": "size"})
        if sp:
            detail["size"] = sp.get_text(strip=True)

    # Measurements
    meas = soup.find(attrs={"data-testid": "item-attributes-measurements"})
    if meas:
        mp = meas.find(attrs={"itemprop": "measurements"})
        if mp:
            detail["measurements"] = mp.get_text(strip=True)

    # Condition
    cond = soup.find(attrs={"data-testid": "item-attributes-status"})
    if cond:
        st = cond.find(attrs={"itemprop": "status"})
        if st:
            detail["status"] = st.get_text(strip=True)

    # Colour
    color = soup.find(attrs={"data-testid": "item-attributes-color"})
    if color:
        cp = color.find(attrs={"itemprop": "color"})
        if cp:
            detail["color"] = cp.get_text(strip=True)

    # Upload date
    upl = soup.find(attrs={"data-testid": "item-attributes-upload_date"})
    if upl:
        up = upl.find(attrs={"itemprop": "upload_date"})
        if up:
            detail["upload_date"] = up.get_text(strip=True)

    # Category (breadcrumbs)
    bc = soup.find("nav", attrs={"aria-label": "breadcrumb"})
    if bc:
        cats = [a.get_text(strip=True) for a in bc.find_all("a")]
        detail["category"] = " > ".join(cats)

    return detail

def download_image(session: requests.Session, url: str, dest: Path) -> None:
    resp = session.get(url, stream=True, timeout=30)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(1024):
            f.write(chunk)

def write_summary(detail: dict, item_dir: Path) -> None:
    summary_file = item_dir / "summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        url = detail.get("url")
        if url:
            f.write(f"URL: {url}\n\n")

        # Note draft in summary
        if detail.get("is_draft"):
            f.write("**DRAFT** – HTML enrichment skipped\n\n")

        fields = [
            ("Title", detail.get("title")),
            ("Category", detail.get("category")),
            ("Brand", detail.get("brand")),
            ("Size", detail.get("size")),
            ("Colour", detail.get("color")),
            ("Condition", detail.get("status")),
            ("Price", detail.get("price")),
            ("Measurements", detail.get("measurements")),
            ("Description", detail.get("description")),
        ]
        for label, value in fields:
            if not value:
                continue
            if label == "Description":
                desc = re.sub(r'\n+(#\S+)', r' \1', value)
                f.write(f"{label}:\n{desc}\n\n")
            else:
                if isinstance(value, (list, dict)):
                    f.write(f"{label}:\n{json.dumps(value, ensure_ascii=False, indent=2)}\n\n")
                else:
                    f.write(f"{label}: {value}\n")

def write_stats(detail: dict, item_dir: Path) -> None:
    stats_file = item_dir / "stats.txt"
    with open(stats_file, "w", encoding="utf-8") as f:
        if detail.get("upload_date"):
            f.write(f"Uploaded: {detail['upload_date']}\n")
        if detail.get("view_count") is not None:
            f.write(f"Views: {detail['view_count']}\n")
        if detail.get("favourite_count") is not None:
            f.write(f"Favourites: {detail['favourite_count']}\n")

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    logging.info("⚠️  Ensure cookies.json is fresh before running.")
    logging.info(
        "   In DevTools: Network → filter 'items?' → select request → "
        "Cookies tab → 'Request Cookies' → Copy all → paste into cookies.json"
    )
    cookies = load_cookies_from_file()

    profile_url = input("Vinted profile URL (e.g. vinted.cz/member/...): ").strip()
    if not profile_url.startswith(("http://", "https://")):
        profile_url = "https://" + profile_url
    parsed = urlparse(profile_url)
    base_url = f"{parsed.scheme}://{parsed.hostname}"
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        logging.error("Unexpected profile URL path: %s", parsed.path)
        return
    profile_id = parts[1].split("-")[0]

    session = make_session(base_url, cookies)
    logging.info("Scanning wardrobe for profile %s…", profile_id)
    items = fetch_wardrobe(session, base_url, profile_id)
    logging.info("Found %d items", len(items))

    default_zip = f"wardrobe_{profile_id}.zip"
    zip_name = input(f"Output ZIP filename [{default_zip}]: ").strip() or default_zip

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        for item in tqdm(items, desc="Processing items"):
            path = item.get("path")
            if not path:
                continue

            detail = None
            try:
                detail = get_item_details(session, base_url, path)
            except HTTPError as e:
                logging.warning("API fetch failed for %s: %s", path, e)
                continue

            # skip closed listings entirely
            if detail.get("is_closed"):
                logging.info("Skipping closed item %s", path)
                continue

            # enrich HTML only if not draft
            if not detail.get("is_draft"):
                delay = random.uniform(2, 4.0)
                try:
                    detail = enrich_detail_with_html(session, base_url, detail, path)
                except HTTPError as e:
                    code = e.response.status_code if e.response else None
                    if code == 404:
                        logging.warning("HTML not found for %s; skipping enrichment", path)
                    elif code == 429:
                        logging.warning("Too many requests for %s; backing off; skipping enrichment", path)
                        time.sleep(delay*2) # additional delay
                    else:
                        logging.warning("Error fetching HTML for %s: %s; skipping enrichment", path, e)

                time.sleep(delay)
            else:
                logging.info("Draft item %s; skipping HTML enrichment", path)

            item_id = detail.get("id", "unknown")
            item_dir = tmp_path / str(item_id)
            item_dir.mkdir(exist_ok=True)

            # full raw metadata
            (item_dir / "metadata.json").write_text(
                json.dumps(detail, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            # user-friendly summary
            write_summary(detail, item_dir)

            # user stats
            write_stats(detail, item_dir)

            # photos
            for photo in detail.get("photos", []):
                url = photo.get("full_size_url") or photo.get("url")
                if not url:
                    continue
                fname = f"{photo.get('id')}.jpg"
                download_image(session, url, item_dir / fname)

        # bundle
        with zipfile.ZipFile(zip_name, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in tmp_path.rglob("*"):
                zf.write(f, arcname=str(f.relative_to(tmp_path)))

    logging.info("Exported to %s", zip_name)

if __name__ == "__main__":
    main()
