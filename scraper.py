import os
import random
import time
import requests
import pandas as pd
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# £1,000 - £100,000 ($1,250 - $125,000 USD)
MIN_USD = 1250
MAX_USD = 125000

def get_empire_flippers():
    """Empire Flippers: Strictly filtering for 'For Sale' status."""
    print("Checking Empire Flippers for ACTIVE deals...")
    monet = "SaaS||Subscription||eCommerce||Content"
    # ADDED: listing_status=For%20Sale to the query string
    url = f"https://api.empireflippers.com/api/v1/listings/list?limit=100&listing_status=For%20Sale&listing_price_from={MIN_USD}&listing_price_to={MAX_USD}&monetizations={monet}"
    
    try:
        r = requests.get(url, timeout=10)
        data = r.json().get('data', {}).get('listings', [])
        
        results = []
        for item in data:
            # Secondary check: Empire Flippers API sometimes returns 'Pending Sold'
            if item.get('status') == 'For Sale':
                results.append({
                    "source": "EmpireFlippers",
                    "title": f"{item.get('business_niche')} - {item.get('monetization_keyword')}",
                    "price": f"${item['listing_price']:,}",
                    "url": f"https://empireflippers.com/listing/{item['listing_number']}"
                })
        return results
    except Exception as e:
        print(f"Empire Flippers API Error: {e}")
        return []

def scrape_stealth(url, site_name, card_selector):
    """Universal Scraper with 2026 Stealth Context."""
    print(f"Checking {site_name} in Stealth Mode...")
    results = []
    try:
        with Stealth().use_sync(sync_playwright()) as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(random.uniform(3, 7))
            
            cards = page.query_selector_all(card_selector)
            for card in cards:
                # REFINED SOLD FILTER: Checks for 'Sold' or 'Under Contract' in the entire card text
                card_text = card.inner_text().lower()
                if any(x in card_text for x in ["sold", "under contract", "reserved", "pending"]):
                    continue
                
                title_ele = card.query_selector("h3, h4")
                price_ele = card.query_selector("span:has-text('$'), div:has-text('$')")
                link_ele = card.query_selector("a")
                
                if title_ele and price_ele and link_ele:
                    results.append({
                        "source": site_name,
                        "title": title_ele.inner_text().strip(),
                        "price": price_ele.inner_text().strip(),
                        "url": link_ele.get_attribute("href") if link_ele.get_attribute("href").startswith("http") else f"{url.split('.com')[0]}.com{link_ele.get_attribute('href')}"
                    })
            browser.close()
    except Exception as e:
        print(f"Error on {site_name}: {e}")
    return results

if __name__ == "__main__":
    # Aggregating all data
    data = get_empire_flippers()
    
    # Adding Microns.io
    data += scrape_stealth("https://www.microns.io/explore", "Microns.io", ".card")
    
    # Adding Flippa (already filtered by 'open' status in URL)
    flippa_url = f"https://www.flippa.com/search?filter%5Bprice%5D%5Bmin%5D={MIN_USD}&filter%5Bprice%5D%5Bmax%5D={MAX_USD}&filter%5Bstatus%5D=open&filter%5Bproperty_type%5D=website%2Csaas"
    data += scrape_stealth(flippa_url, "Flippa", "div[class*='ListingCard']")
    
    # Adding SideProjectors
    data += scrape_stealth("https://www.sideprojectors.com/project/search?is_for_sale=true", "SideProjectors", ".project-item")

    if data:
        df = pd.DataFrame(data).drop_duplicates(subset=['url'])
        
        # Final safety filter: Remove any rows that still contain 'Sold' in the title
        df = df[~df['title'].str.contains("Sold|Pending|Contract", case=False)]
        
        # Sort by price (lowest first)
        df['p_val'] = df['price'].replace('[\$,]', '', regex=True).astype(float, errors='ignore')
        df = df.sort_values(by='p_val', ascending=True).drop(columns=['p_val'])
        
        df.to_csv("eu_businesses.csv", index=False)
        print(f"Success! {len(df)} ACTIVE digital assets found.")
    else:
        print("No active matches found today.")
