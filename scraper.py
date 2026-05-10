import os
import json
import requests
import pandas as pd
from playwright.sync_api import sync_playwright

def get_empire_flippers(min_p, max_p):
    """Empire Flippers API: High-stability source."""
    print("Fetching Empire Flippers listings...")
    url = "https://api.empireflippers.com/api/v1/listings/list?limit=100"
    try:
        r = requests.get(url, timeout=10)
        data = r.json().get('data', {}).get('listings', [])
        return [{
            "source": "EmpireFlippers",
            "title": f"Listing #{item['listing_number']} - {item.get('business_niche', 'Business')}",
            "price": f"${item['listing_price']}",
            "url": f"https://empireflippers.com/listing/{item['listing_number']}"
        } for item in data if min_p <= item['listing_price'] <= max_p]
    except Exception as e:
        print(f"EF API Error: {e}")
        return []

def scrape_with_playwright(min_p, max_p):
    """Scrapes Flippa with precision card targeting to avoid banners."""
    all_data = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        page = context.new_page()

        # Target 1: Flippa (Filtered for Europe and Price Range)
        print("Scraping Flippa Listings...")
        flippa_url = f"https://www.flippa.com/search?filter%5Blocation%5D%5B%5D=Europe&filter%5Bprice%5D%5Bmin%5D={min_p}&filter%5Bprice%5D%5Bmax%5D={max_p}"
        page.goto(flippa_url, wait_until="networkidle")
        page.wait_for_timeout(5000) 
        
        # Target only listing cards, ignoring marketing headers/banners
        listing_cards = page.query_selector_all("div[class*='ListingCard'], .search-result")
        
        for card in listing_cards:
            title_element = card.query_selector("h3, .title")
            link_element = card.query_selector("a")
            
            if title_element:
                title_text = title_element.inner_text().strip()
                
                # Filter out the marketing banner you saw in previous runs
                if any(x in title_text for x in ["Flippa Premium", "Elevate Your", "Promoted"]):
                    continue
                
                link_url = link_element.get_attribute("href") if link_element else ""
                full_url = f"https://www.flippa.com{link_url}" if link_url.startswith('/') else link_url
                
                all_data.append({
                    "source": "Flippa", 
                    "title": title_text, 
                    "price": "Check Site", 
                    "url": full_url
                })

        browser.close()
    return all_data

if __name__ == "__main__":
    # USER PREFERENCES: Price Range $1k - $100k
    MIN_PRICE = 1000
    MAX_PRICE = 100000

    ef_data = get_empire_flippers(MIN_PRICE, MAX_PRICE)
    web_data = scrape_with_playwright(MIN_PRICE, MAX_PRICE)
    
    final_list = ef_data + web_data
    
    if final_list:
        df = pd.DataFrame(final_list)
        # Clean data: remove short non-business titles and duplicates
        df = df[df['title'].str.len() > 10]
        df = df.drop_duplicates(subset=['title'])
        df.to_csv("eu_businesses.csv", index=False)
        print(f"Success! Found {len(df)} real listings.")
    else:
        print("No real listings found. Check filters.")
