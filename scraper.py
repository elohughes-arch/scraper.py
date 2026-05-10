import os
import requests
import pandas as pd
from playwright.sync_api import sync_playwright

def get_empire_flippers(min_p, max_p):
    """Empire Flippers API: High quality established businesses."""
    print(f"Checking Empire Flippers for listings between ${min_p} and ${max_p}...")
    url = "https://api.empireflippers.com/api/v1/listings/list?limit=100"
    try:
        r = requests.get(url, timeout=10)
        data = r.json().get('data', {}).get('listings', [])
        # EF listings are usually expensive, we widen the check here
        found = [{
            "source": "EmpireFlippers",
            "title": f"Listing #{item['listing_number']} - {item.get('business_niche', 'Business')}",
            "price": f"${item['listing_price']}",
            "url": f"https://empireflippers.com/listing/{item['listing_number']}"
        } for item in data if min_p <= item['listing_price'] <= max_p]
        return found
    except:
        return []

def scrape_flippa(min_p, max_p):
    """Flippa Scraper: Uses specific price-card selectors to avoid ads."""
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Using a real browser 'User Agent' to prevent being blocked
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        page = context.new_page()
        
        # Search URL (Status: Open, Price Range as requested)
        url = f"https://www.flippa.com/search?filter%5Bprice%5D%5Bmin%5D={min_p}&filter%5Bprice%5D%5Bmax%5D={max_p}&filter%5Bstatus%5D=open"
        print(f"Opening Flippa: {url}")
        
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(5000) # Wait for listings to load

        # We target the listing "cards". If it doesn't have a price, it's a marketing banner.
        cards = page.query_selector_all("div[class*='ListingCard']")
        for card in cards:
            title_ele = card.query_selector("h3")
            price_ele = card.query_selector("span:has-text('$')") # Real listings must have a price
            link_ele = card.query_selector("a")
            
            if title_ele and price_ele and link_ele:
                title = title_ele.inner_text().strip()
                price = price_ele.inner_text().strip()
                link = link_ele.get_attribute("href")
                
                # Filter out those annoying "Premium" ads manually just in case
                if "Premium" in title or "Elevate Your" in title:
                    continue
                
                results.append({
                    "source": "Flippa",
                    "title": title,
                    "price": price,
                    "url": f"https://www.flippa.com{link}" if link.startswith('/') else link
                })
        browser.close()
    return results

if __name__ == "__main__":
    # Settings (Widened slightly to ensure you actually get results)
    MIN_PRICE = 1000
    MAX_PRICE = 250000 

    ef_data = get_empire_flippers(MIN_PRICE, MAX_PRICE)
    flippa_data = scrape_flippa(MIN_PRICE, MAX_PRICE)
    
    all_listings = ef_data + flippa_data
    
    df = pd.DataFrame(all_listings)
    if not df.empty:
        df = df.drop_duplicates(subset=['title'])
        df.to_csv("eu_businesses.csv", index=False)
        print(f"Done! Saved {len(df)} listings to CSV.")
    else:
        # Save an empty file with headers so the push doesn't fail
        pd.DataFrame(columns=["source", "title", "price", "url"]).to_csv("eu_businesses.csv", index=False)
        print("No listings found matching criteria today.")
