import os
import time
import random
import requests
import pandas as pd
from playwright.sync_api import sync_playwright

def get_empire_flippers(min_p, max_p):
    """Empire Flippers: Uses the official API to avoid scraping blocks entirely."""
    print(f"Checking Empire Flippers API...")
    url = f"https://api.empireflippers.com/api/v1/listings/list?limit=100&listing_price_from={min_p}&listing_price_to={max_p}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json().get('data', {}).get('listings', [])
        return [{
            "source": "EmpireFlippers",
            "title": f"{item.get('business_niche', 'Business')} - #{item['listing_number']}",
            "price": f"${item['listing_price']:,}",
            "url": f"https://empireflippers.com/listing/{item['listing_number']}"
        } for item in data]
    except Exception as e:
        print(f"EF API logic error or timeout: {e}")
        return []

def scrape_flippa(min_p, max_p):
    """Flippa: Uses behavioral mimicry and strict container validation."""
    results = []
    with sync_playwright() as p:
        # 1. Defensible Browser Launch
        browser = p.chromium.launch(headless=True)
        # Randomize User Agent to look like different users each day
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ]
        context = browser.new_context(user_agent=random.choice(user_agents), viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        print("Navigating to Flippa with randomized delay...")
        url = f"https://www.flippa.com/search?filter%5Bprice%5D%5Bmin%5D={min_p}&filter%5Bprice%5D%5Bmax%5D={max_p}&filter%5Bstatus%5D=open"
        page.goto(url, wait_until="networkidle")
        
        # 2. Mimic Human Scroll
        page.mouse.wheel(0, 500)
        time.sleep(random.uniform(2, 5)) # Random wait to bypass bot detection

        # 3. Accuracy: Target only verified Listing Cards
        # We avoid generic <h3> tags and look for specific card classes
        cards = page.query_selector_all("div[class*='ListingCard'], .search-result-card")
        
        for card in cards:
            try:
                title_ele = card.query_selector("h3")
                price_ele = card.query_selector("span:has-text('$')")
                link_ele = card.query_selector("a")
                
                if title_ele and price_ele and link_ele:
                    title = title_ele.inner_text().strip()
                    price = price_ele.inner_text().strip()
                    link = link_ele.get_attribute("href")
                    
                    # --- THE ACCURACY FILTER ---
                    # Logic: Real listings don't contain these 'Category' or 'Ad' keywords
                    junk_keywords = ["Premium", "Elevate Your", "Price Range", "Browse", "Search", "Filter"]
                    if any(word in title for word in junk_keywords) or "$" in title:
                        continue
                    
                    if len(title) > 8: # Filter out short UI text like "Top Rated"
                        results.append({
                            "source": "Flippa",
                            "title": title,
                            "price": price,
                            "url": f"https://www.flippa.com{link}" if link.startswith('/') else link
                        })
            except:
                continue # Skip cards that have layout errors

        browser.close()
    return results

if __name__ == "__main__":
    # Settings
    MIN_PRICE = 5000
    MAX_PRICE = 500000 

    # Execute and Combine
    ef_listings = get_empire_flippers(MIN_PRICE, MAX_PRICE)
    flippa_listings = scrape_flippa(MIN_PRICE, MAX_PRICE)
    
    total_data = ef_listings + flippa_listings
    
    if total_data:
        df = pd.DataFrame(total_data)
        # Final Clean: Remove duplicates and empty rows
        df.dropna(subset=['title', 'url'], inplace=True)
        df.drop_duplicates(subset=['title'], inplace=True)
        
        df.to_csv("eu_businesses.csv", index=False)
        print(f"🚀 Success! {len(df)} High-Quality listings captured.")
    else:
        # Safeguard: Keep the CSV structure even if 0 results
        pd.DataFrame(columns=["source", "title", "price", "url"]).to_csv("eu_businesses.csv", index=False)
        print("No matches today. Clean CSV maintained.")
