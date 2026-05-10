import os
import json
import requests
import pandas as pd
from playwright.sync_api import sync_playwright

def get_empire_flippers(min_p, max_p):
    print(f"Checking Empire Flippers ($ {min_p} - $ {max_p})...")
    url = "https://api.empireflippers.com/api/v1/listings/list?limit=100"
    try:
        r = requests.get(url, timeout=10)
        data = r.json().get('data', {}).get('listings', [])
        found = [{
            "source": "EmpireFlippers",
            "title": f"Listing #{item['listing_number']} - {item.get('business_niche', 'Business')}",
            "price": f"${item['listing_price']}",
            "url": f"https://empireflippers.com/listing/{item['listing_number']}"
        } for item in data if min_p <= item['listing_price'] <= max_p]
        print(f"Empire Flippers found: {len(found)} listings.")
        return found
    except Exception as e:
        print(f"EF API Error: {e}")
        return []

def scrape_with_playwright(min_p, max_p):
    all_data = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        page = context.new_page()

        # REMOVED Europe filter to ensure we get results first
        print("Scraping Flippa (Global Search)...")
        flippa_url = f"https://www.flippa.com/search?filter%5Bprice%5D%5Bmin%5D={min_p}&filter%5Bprice%5D%5Bmax%5D={max_p}&filter%5Bstatus%5D=open"
        page.goto(flippa_url, wait_until="networkidle")
        page.wait_for_timeout(5000) 
        
        # This targets only the text inside actual listing titles
        listings = page.query_selector_all("h3")
        
        for item in listings:
            title_text = item.inner_text().strip()
            
            # STRENGTHENED AD FILTER
            ad_keywords = ["Premium", "Promoted", "Elevate Your", "$", "Search", "Filter"]
            if any(x in title_text for x in ad_keywords) or len(title_text) < 5:
                continue
            
            parent_link = item.query_selector("xpath=./ancestor::a")
            link_url = parent_link.get_attribute("href") if parent_link else ""
            full_url = f"https://www.flippa.com{link_url}" if link_url.startswith('/') else link_url
            
            all_data.append({
                "source": "Flippa", 
                "title": title_text, 
                "price": "Check Site", 
                "url": full_url
            })

        browser.close()
    print(f"Flippa found: {len(all_data)} listings.")
    return all_data

if __name__ == "__main__":
    # Settings: Widened range to catch more listings
    MIN_PRICE = 5000
    MAX_PRICE = 200000

    ef_data = get_empire_flippers(MIN_PRICE, MAX_PRICE)
    web_data = scrape_with_playwright(MIN_PRICE, MAX_PRICE)
    
    final_list = ef_data + web_data
    
    if final_list:
        df = pd.DataFrame(final_list)
        df = df.drop_duplicates(subset=['title'])
        df.to_csv("eu_businesses.csv", index=False)
        print(f"Success! CSV saved with {len(df)} rows.")
    else:
        # Create an empty CSV with headers so the Git Push doesn't fail
        pd.DataFrame(columns=["source", "title", "price", "url"]).to_csv("eu_businesses.csv", index=False)
        print("No listings found. CSV cleared.")
