import os
import json
import requests
import pandas as pd
from playwright.sync_api import sync_playwright

def get_empire_flippers(min_p, max_p):
    """Empire Flippers API: The most reliable method."""
    print("Fetching Empire Flippers via API...")
    url = f"https://api.empireflippers.com/api/v1/listings/list?limit=100"
    try:
        r = requests.get(url, timeout=10)
        data = r.json().get('data', {}).get('listings', [])
        return [{
            "source": "EmpireFlippers",
            "title": f"Listing #{item['listing_number']}",
            "price": f"${item['listing_price']}",
            "url": f"https://empireflippers.com/listing/{item['listing_number']}"
        } for item in data if min_p <= item['listing_price'] <= max_p]
    except Exception as e:
        print(f"EF API Error: {e}")
        return []

def scrape_with_playwright(min_p, max_p):
    """Scrapes Flippa and Acquire using browser automation."""
    all_data = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use a high-quality User Agent to avoid being blocked
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        page = context.new_page()

        # --- TARGET 1: FLIPPA ---
        print("Scraping Flippa...")
        flippa_url = f"https://www.flippa.com/search?filter%5Blocation%5D%5B%5D=Europe&filter%5Bprice%5D%5Bmin%5D={min_p}&filter%5Bprice%5D%5Bmax%5D={max_p}"
        page.goto(flippa_url, wait_until="domcontentloaded")
        page.wait_for_timeout(3000) # Give it a second to render
        
        # New 2026 selector logic: look for cards or links containing prices
        listings = page.query_selector_all("a[href*='/buy/']")
        for link in listings:
            text = link.inner_text().replace('\n', ' ')
            if "£" in text or "$" in text:
                all_data.append({"source": "Flippa", "title": text[:50] + "...", "price": "Check Site", "url": link.get_attribute("href")})

        # --- TARGET 2: ACQUIRE.COM (JSON-LD Trick) ---
        # Note: Acquire usually requires login for full data, 
        # but public teasers are often in script tags for SEO.
        print("Scraping Acquire.com Teasers...")
        page.goto("https://acquire.com/listings/", wait_until="networkidle")
        scripts = page.query_selector_all("script[type='application/ld+json']")
        for s in scripts:
            try:
                content = json.loads(s.inner_text())
                if isinstance(content, dict) and content.get('@type') == 'Product':
                    all_data.append({
                        "source": "Acquire",
                        "title": content.get('name'),
                        "price": content.get('offers', {}).get('price'),
                        "url": "https://acquire.com/listings/"
                    })
            except: continue

        browser.close()
    return all_data

if __name__ == "__main__":
    # Your Criteria
    MIN_PRICE = 1000
    MAX_PRICE = 100000

    ef_results = get_empire_flippers(MIN_PRICE, MAX_PRICE)
    web_results = scrape_with_playwright(MIN_PRICE, MAX_PRICE)
    
    final_list = ef_results + web_results
    
    if final_list:
        df = pd.DataFrame(final_list).drop_duplicates(subset=['title'])
        df.to_csv("eu_businesses.csv", index=False)
        print(f"Success! {len(df)} businesses found.")
    else:
        print("No results found. Check site availability or selectors.")
