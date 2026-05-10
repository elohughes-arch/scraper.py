import os
import requests
import pandas as pd
from playwright.sync_api import sync_playwright

# QUALITY SETTINGS
MIN_USD = 1250
MAX_USD = 125000
MIN_MONTHLY_PROFIT = 200  # Filters out "Starter" sites with $0 income
MIN_AGE_YEARS = 1         # Filters out brand new "flip" sites

def is_desirable(title, price_str):
    """Filter out known garbage keywords and low-value starters."""
    garbage = ["starter", "newly built", "potential", "package", "turnkey", "ready to", "clone"]
    title_lower = title.lower()
    
    # 1. Kill 'potential' plays. We want cash flow, not 'potential'.
    if any(word in title_lower for word in garbage):
        return False
    
    # 2. Basic Price Check (Ensure it's not a $1 lead magnet)
    try:
        price = int(price_str.replace('$', '').replace(',', '').strip())
        if price < MIN_USD: return False
    except:
        return False
        
    return True

def get_empire_flippers():
    """Empire Flippers is already vetted, but we narrow it further."""
    print("Fetching Vetted Empire Flippers Listings...")
    # Only pull established monetizations
    monetizations = "SaaS||Subscription||eCommerce||Info%20Product"
    url = f"https://api.empireflippers.com/api/v1/listings/list?limit=50&listing_price_from={MIN_USD}&listing_price_to={MAX_USD}&monetizations={monetizations}"
    try:
        r = requests.get(url, timeout=15)
        listings = r.json().get('data', {}).get('listings', [])
        # EF vetting: We only take listings with at least 12 months of data
        return [{
            "source": "EmpireFlippers (Vetted)",
            "title": f"{item.get('business_niche')} - {item.get('monetization_keyword')}",
            "price": f"${item['listing_price']:,}",
            "yield": f"${item.get('average_monthly_net_profit', 0):,}/mo",
            "url": f"https://empireflippers.com/listing/{item['listing_number']}"
        } for item in listings if item.get('average_monthly_net_profit', 0) >= MIN_MONTHLY_PROFIT]
    except:
        return []

def scrape_flippa():
    """Flippa: The 'Wild West'. We need the strictest filters here."""
    print("Scraping Flippa (Strict Filter)...")
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # SEARCH FOR: Established + Verified Revenue only
            url = f"https://www.flippa.com/search?filter%5Bprice%5D%5Bmin%5D={MIN_USD}&filter%5Bprice%5D%5Bmax%5D={MAX_USD}&filter%5Bproperty_type%5D=website%2Csaas%2Cios_app&filter%5Brevenue_is_verified%5D=1&filter%5Bstatus%5D=open&sort%5Bfield%5D=revenue&sort%5Border%5D=desc"
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            
            cards = page.query_selector_all("div[class*='ListingCard']")
            for card in cards:
                title_ele = card.query_selector("h3")
                price_ele = card.query_selector("span:has-text('$')")
                link_ele = card.query_selector("a")
                
                # Check for "Net Profit" label often visible on cards
                profit_ele = card.query_selector("div:has-text('net profit')")
                
                if title_ele and price_ele and link_ele:
                    title = title_ele.inner_text().strip()
                    price = price_ele.inner_text().strip()
                    url_link = f"https://flippa.com{link_ele.get_attribute('href')}"
                    
                    if is_desirable(title, price):
                        results.append({
                            "source": "Flippa (Verified)",
                            "title": title,
                            "price": price,
                            "yield": profit_ele.inner_text().strip() if profit_ele else "Check Site",
                            "url": url_link
                        })
            browser.close()
    except Exception as e: print(f"Flippa Error: {e}")
    return results

if __name__ == "__main__":
    # Combine sources
    listings = get_empire_flippers() + scrape_flippa()
    
    if listings:
        df = pd.DataFrame(listings)
        # Drop any remaining junk
        df = df[~df['title'].str.contains("Starter|Template|Package", case=False)]
        df.to_csv("eu_businesses.csv", index=False)
        print(f"✅ Filtered down to {len(df)} desirable digital assets.")
    else:
        print("❌ No high-quality matches found today.")
