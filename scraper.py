"""Selenium-based scraper for Metropoles categories.

Produces output.csv with columns: category,title,summary,url

Usage examples:
    python scraper.py --browser chrome --limit 5 --headless

Notes:
 - Uses webdriver-manager to auto-download drivers on first run.
 - For restricted environments, install driver manually and ensure it's on PATH.
"""

import argparse
import csv
import time
from typing import List, Dict, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

DEFAULT_LIMIT = 5
OUTPUT_CSV = "output.csv"
BASE_URL = "https://www.metropoles.com/"


def parse_args():
    p = argparse.ArgumentParser(description="Scrape Metropoles categories and aggregate top news into CSV (Selenium)")
    p.add_argument("--browser", choices=["chrome", "firefox"], default="chrome",
                   help="Browser to use: chrome or firefox")
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Max items per category")
    p.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    p.add_argument("--categories", type=str, default="",
                   help="Comma-separated list of category names or URLs to scrape")
    p.add_argument("--categories-file", type=str, default="",
                   help="Path to file with one category name or URL per line")
    return p.parse_args()


def init_driver(browser: str, headless: bool = True):
    if browser == "chrome":
        opts = ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
            opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        service = webdriver.chrome.service.Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
    else:
        opts = FirefoxOptions()
        if headless:
            opts.add_argument("-headless")
        service = webdriver.firefox.service.Service(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=opts)

    driver.set_page_load_timeout(30)
    return driver


def load_category_inputs(args) -> List[str]:
    items = []
    if args.categories:
        items.extend([s.strip() for s in args.categories.split(",") if s.strip()])
    if args.categories_file:
        try:
            with open(args.categories_file, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if s:
                        items.append(s)
        except FileNotFoundError:
            print(f"Categories file not found: {args.categories_file}")
    # default: use main categories names requested by user if none provided
    if not items:
        items = [
            "Últimas notícias",
            "Colunistas",
            "Brasil",
            "DF",
            "SP",
            "Mundo",
            "Entretenimento",
            "Vida & Estilo",
            "Saúde",
            "Ciência",
            "Esportes",
            "Especiais",
        ]
    return items


def find_category_url(driver, category_name: str) -> Optional[str]:
    """Try to find a category link on the homepage by matching link text (case-insensitive).

    If category_name is already a URL (starts with http), return it.
    """
    if category_name.lower().startswith("http"):
        return category_name

    driver.get(BASE_URL)
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except TimeoutException:
        pass

    # Normalize search term
    needle = category_name.strip().lower()

    anchors = driver.find_elements(By.TAG_NAME, "a")
    best = None
    for a in anchors:
        try:
            text = (a.text or "").strip()
            if not text:
                continue
            if needle in text.lower():
                href = a.get_attribute("href")
                if href:
                    return href
                best = None
        except Exception:
            continue

    return best


def extract_top_articles_on_category(driver, category_url: str, limit: int) -> List[Dict[str, str]]:
    rows = []
    try:
        driver.get(category_url)
    except WebDriverException:
        return rows

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except TimeoutException:
        pass

    # Look for article blocks first, then fallback to heading links
    candidates = []

    # Try <article> tags
    articles = driver.find_elements(By.TAG_NAME, "article")
    for art in articles:
        try:
            a = art.find_element(By.CSS_SELECTOR, "a[href]")
            href = a.get_attribute("href")
            title = a.text.strip() if a.text else None
            if not title:
                # try headers inside
                try:
                    title_el = art.find_element(By.CSS_SELECTOR, "h1, h2, h3")
                    title = title_el.text.strip()
                except Exception:
                    title = None
            candidates.append((title or href, href))
        except Exception:
            continue

    # Fallback: find heading links in the main content
    if not candidates:
        heading_links = driver.find_elements(By.XPATH, "//main//a[.//h1 or .//h2 or .//h3]")
        for a in heading_links:
            try:
                href = a.get_attribute("href")
                title = a.text.strip() or None
                candidates.append((title or href, href))
            except Exception:
                continue

    # Last fallback: any links with reasonably long text
    if not candidates:
        links = driver.find_elements(By.TAG_NAME, "a")
        for a in links:
            try:
                text = (a.text or "").strip()
                href = a.get_attribute("href")
                if text and href and len(text) > 20:
                    candidates.append((text, href))
            except Exception:
                continue

    seen = set()
    for title, href in candidates:
        if not href or href in seen:
            continue
        seen.add(href)
        summary = fetch_first_paragraph(driver, href)
        rows.append({"title": title, "summary": summary or "", "url": href})
        if len(rows) >= limit:
            break

    return rows


def fetch_first_paragraph(driver, url: str) -> Optional[str]:
    try:
        driver.get(url)
    except WebDriverException:
        return None

    try:
        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except TimeoutException:
        pass

    selectors = ["article p", ".entry-content p", ".post-content p", "main p", "p"]
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            text = el.text.strip()
            if text:
                # return the first sentence or up to ~300 chars
                return text.split("\n")[0][:1000]
        except NoSuchElementException:
            continue
        except Exception:
            continue
    return None


def write_csv(rows: List[Dict[str, str]], path: str = OUTPUT_CSV):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "title", "summary", "url"]) 
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main():
    args = parse_args()
    items = load_category_inputs(args)
    driver = init_driver(args.browser, headless=args.headless)
    aggregated = []

    try:
        for item in items:
            print(f"Processing category: {item}")
            url = None
            if item.lower().startswith("http"):
                url = item
            else:
                url = find_category_url(driver, item)
            if not url:
                print(f"Could not find URL for category '{item}', skipping.")
                continue

            rows = extract_top_articles_on_category(driver, url, args.limit)
            for r in rows:
                aggregated.append({
                    "category": item,
                    "title": r.get("title", ""),
                    "summary": r.get("summary", ""),
                    "url": r.get("url", ""),
                })

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    write_csv(aggregated)
    print(f"Wrote {len(aggregated)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
