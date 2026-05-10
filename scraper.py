import os
import json
import requests
import pandas as pd
from playwright.sync_api import sync_playwright

def get_empire_flippers(min_p, max_p):
    """Empire Flippers API: The most reliable method."""
    print("Fetching Empire Flippers via API...")
    url = "https://api.empireflippers.com/api/v1/listings/list?limit=100"
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
        # High-quality User Agent to bypass basic bot detection
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        page = context.new_page()

        # --- TARGET 1: FLIPPA ---
        print("Scraping Flippa...")
        flippa_url = f"https://www.flippa.com/search?filter%5Blocation%5D%5B%5D=Europe&filter%5Bprice%5D%5Bmin%5D={min_p}&filter%5Bprice%5D%5Bmax%5D={max_p}"
        page.goto(flippa_url, wait_until="domcontentloaded")
        page.wait_for_timeout(5000) # Give extra time for JS to render
        
        # We target h3 tags which usually hold the Business Names
        listings = page.query_selector_all("h3") 
        for title_element in listings:
            title_text = title_element.inner_text().strip()
            # Try to find the associated link
            parent_link = title_element.query_selector("xpath=./ancestor::a")
            link_url = parent_link.get_attribute("href") if parent_link else ""
            
            if len(title_text) > 5: # Filters out tiny UI elements
                full_url = f"https://www.flippa.com{link_url}" if link_url.startswith('/') else link_url
                all_data.append({
                    "source": "Flippa", 
                    "title": title_text, 
                    "price": "Check Site", 
                    "url": full_url
                })

        # --- TARGET 2: ACQUIRE.COM (JSON-LD Trick) ---
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
    # Settings
    MIN_PRICE = 1000
    MAX_PRICE = 100000

    ef_results = get_empire_flippers(MIN_PRICE, MAX_PRICE)
    web_results = scrape_with_playwright(MIN_PRICE, MAX_PRICE)
    
    final_list = ef_results + web_results
    
    if final_list:
        df = pd.DataFrame(final_list)
        # Drop duplicates based on title to keep the CSV clean
        df = df.drop_duplicates(subset=['title'])
        df.to_csv("eu_businesses.csv", index=False)
        print(f"Success! {len(df)} businesses found and saved to eu_businesses.csv")
    else:
        print("No results found. Verify site access or selectors.")
