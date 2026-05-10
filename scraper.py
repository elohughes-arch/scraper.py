import os
import random
import time
import requests
import pandas as pd
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_async, stealth_sync

# £1,000 - £100,000 ($1,250 - $125,000 USD)
MIN_USD = 1250
MAX_USD = 125000

def get_empire_flippers():
    """Empire Flippers: API is public and safe."""
    print("Checking Empire Flippers...")
    monet = "SaaS||Subscription||eCommerce||Content"
    url = f"https://api.empireflippers.com/api/v1/listings/list?limit=50&listing_price_from={MIN_USD}&listing_price_to={MAX_USD}&monetizations={monet}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json().get('data', {}).get('listings', [])
        return [{"source": "EmpireFlippers", "title": f"{item.get('business_niche')}", "price": f"${item['listing_price']:,}", "url": f"https://empireflippers.com/listing/{item['listing_number']}"} for item in data]
    except: return []

def scrape_stealth(url, site_name, card_selector):
    """Universal Stealth Scraper to avoid IP bans."""
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Use a random real-world User Agent
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            ]
            context = browser.new_context(user_agent=random.choice(user_agents))
            page = context.new_page()
            
            # 1. APPLY STEALTH
            stealth_sync(page)
            
            # 2. NAVIGATE & WAIT
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(random.uniform(3, 7)) # Human delay
            
            # 3. HUMAN SCROLL
            page.mouse.wheel(0, 400)
            
            cards = page.query_selector_all(card_selector)
            for card in cards:
                # SKIP SOLD
                if "Sold" in card.inner_text(): continue
                
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
    # 1. Empire Flippers (API)
    data = get_empire_flippers()
    
    # 2. Microns.io (Micro-SaaS focused)
    data += scrape_stealth("https://www.microns.io/explore", "Microns.io", ".card")
    
    # 3. Flippa (Broad Digital)
    flippa_url = f"https://www.flippa.com/search?filter%5Bprice%5D%5Bmin%5D={MIN_USD}&filter%5Bprice%5D%5Bmax%5D={MAX_USD}&filter%5Bstatus%5D=open&filter%5Bproperty_type%5D=website%2Csaas"
    data += scrape_stealth(flippa_url, "Flippa", "div[class*='ListingCard']")
    
    # 4. SideProjectors (Indie Projects)
    data += scrape_stealth("https://www.sideprojectors.com/project/search?is_for_sale=true", "SideProjectors", ".project-item")

    if data:
        df = pd.DataFrame(data).drop_duplicates(subset=['url'])
        # Sort by price to show £1,000 listings at the top
        df['p_val'] = df['price'].replace('[\$,]', '', regex=True).astype(float, errors='ignore')
        df = df.sort_values(by='p_val', ascending=True).drop(columns=['p_val'])
        
        df.to_csv("eu_businesses.csv", index=False)
        print(f"Success! {len(df)} available digital assets found.")
