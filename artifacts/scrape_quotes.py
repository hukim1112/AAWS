import os
import json
import time
import logging
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

BASE_URL = "http://quotes.toscrape.com/page/{page}/"
OUTPUT_PATH = "/mnt/c/Users/hyoun/Desktop/working_project/working_on_dir/instructor/artifacts/notebooks/generated/quotes_sample_result.json"

def scrape_quotes(start_page=1, end_page=3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    quotes_data = []

    for page in range(start_page, end_page + 1):
        url = BASE_URL.format(page=page)
        logging.info(f"Scraping page {page}: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except Exception as e:
            logging.error(f"Failed to fetch page {page}: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        quote_elements = soup.select("div.quote")
        logging.info(f"Page {page}: found {len(quote_elements)} quotes")

        for el in quote_elements:
            text_el = el.select_one("span.text")
            author_el = el.select_one("small.author")
            tag_els = el.select("div.tags a.tag")

            text = text_el.get_text(strip=True) if text_el else ""
            author = author_el.get_text(strip=True) if author_el else ""
            tags = [tag.get_text(strip=True) for tag in tag_els]

            quotes_data.append({
                "text": text,
                "author": author,
                "tags": tags
            })

        # Rate limiting delay
        time.sleep(0.5)

    # Make sure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(quotes_data, f, ensure_ascii=False, indent=2)

    logging.info(f"Successfully saved {len(quotes_data)} quotes to {OUTPUT_PATH}")
    return quotes_data

if __name__ == "__main__":
    scrape_quotes(1, 3)
