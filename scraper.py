import os
import random
import time
import requests
import pandas as pd
from playwright.sync_api import sync_playwright
# Using the v2.0+ class structure
from playwright_stealth import Stealth

MIN_USD = 1250
MAX_USD = 125000

def get_empire_flippers():
    print("Checking Empire Flippers...")
    monet = "SaaS||Subscription||eCommerce||Content"
    url = f"https://api.empireflippers.com/api/v1/listings/list?limit=50&listing_price_from={MIN_USD}&listing_price_to={MAX_USD}&monetizations={monet}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json().get('data', {}).get('listings', [])
        return [{"source": "EmpireFlippers", "title": f"{item.get('business_niche')}", "price": f"${item['listing_price']:,}", "url": f"https://empireflippers.com/listing/{item['listing_number']}"} for item in data]
    except: return []

def scrape_stealth(url, site_name, card_selector):
    print(f"Checking {site_name} in Stealth Mode...")
    results = []
    try:
        # The 'Stealth().use_sync' pattern patches the browser context automatically
        with Stealth().use_sync(sync_playwright()) as p:
            browser = p.chromium.launch(headless=True)
            
            # Use random real-world agents to avoid fingerprinting
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            ]
            
            context = browser.new_context(user_agent=random.choice(user_agents))
            page = context.new_page()
            
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(random.uniform(3, 7)) # Human behavior delay
            
            cards = page.query_selector_all(card_selector)
            for card in cards:
                text = card.inner_text()
                if any(x in text for x in ["Sold", "Under Contract", "Reserved"]):
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
    data += scrape_stealth("https://www.microns.io/explore", "Microns.io", ".card")
    
    flippa_url = f"https://www.flippa.com/search?filter%5Bprice%5D%5Bmin%5D={MIN_USD}&filter%5Bprice%5D%5Bmax%5D={MAX_USD}&filter%5Bstatus%5D=open&filter%5Bproperty_type%5D=website%2Csaas"
    data += scrape_stealth(flippa_url, "Flippa", "div[class*='ListingCard']")
    
    data += scrape_stealth("https://www.sideprojectors.com/project/search?is_for_sale=true", "SideProjectors", ".project-item")

    if data:
        df = pd.DataFrame(data).drop_duplicates(subset=['url'])
        # Sort so the £1,000 (lowest price) assets are first
        df['p_val'] = df['price'].replace('[\$,]', '', regex=True).astype(float, errors='ignore')
        df = df.sort_values(by='p_val', ascending=True).drop(columns=['p_val'])
        
        df.to_csv("eu_businesses.csv", index=False)
        print(f"Successfully processed {len(df)} available digital assets.")
    else:
        print("No matches found today.")
