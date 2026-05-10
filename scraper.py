import os
import requests
import pandas as pd
from playwright.sync_api import sync_playwright

# SETTINGS: £1,000 - £100,000 (Approx $1,250 - $125,000 USD)
MIN_USD = 1250
MAX_USD = 125000

def get_empire_flippers():
    print("Fetching Empire Flippers (Digital Only)...")
    monetizations = "Affiliate||Amazon%20FBA||Display%20Advertising||eCommerce||SaaS||Subscription"
    url = f"https://api.empireflippers.com/api/v1/listings/list?limit=50&listing_price_from={MIN_USD}&listing_price_to={MAX_USD}&monetizations={monetizations}"
    try:
        r = requests.get(url, timeout=15)
        listings = r.json().get('data', {}).get('listings', [])
        return [{
            "source": "EmpireFlippers",
            "title": f"{item.get('business_niche')} - #{item['listing_number']}",
            "price": f"${item['listing_price']:,}",
            "url": f"https://empireflippers.com/listing/{item['listing_number']}"
        } for item in listings]
    except Exception as e:
        print(f"Empire Flippers error: {e}")
        return []

def scrape_flippa():
    print("Scraping Flippa...")
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            url = f"https://www.flippa.com/search?filter%5Bprice%5D%5Bmin%5D={MIN_USD}&filter%5Bprice%5D%5Bmax%5D={MAX_USD}&filter%5Bproperty_type%5D=website%2Cios_app%2Candroid_app%2Csaas&filter%5Bstatus%5D=open"
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            
            cards = page.query_selector_all("div[class*='ListingCard']")
            for card in cards:
                title = card.query_selector("h3")
                price = card.query_selector("span:has-text('$')")
                link = card.query_selector("a")
                if title and price and link:
                    t_text = title.inner_text().strip()
                    if any(x in t_text for x in ["Premium", "Promoted", "$"]): continue
                    results.append({
                        "source": "Flippa",
                        "title": t_text,
                        "price": price.inner_text().strip(),
                        "url": f"https://flippa.com{link.get_attribute('href')}"
                    })
            browser.close()
    except Exception as e:
        print(f"Flippa error: {e}")
    return results

def scrape_sideprojectors():
    print("Scraping SideProjectors...")
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # Faster wait condition + longer timeout
            page.goto("https://www.sideprojectors.com/project/search?is_for_sale=true", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            
            items = page.query_selector_all(".project-item")
            for item in items:
                title = item.query_selector("h4")
                price_raw = item.query_selector(".text-success")
                link = item.query_selector("a")
                if title and price_raw and link:
                    p_text = price_raw.inner_text().replace('$', '').replace(',', '').strip()
                    try:
                        p_val = int(p_text)
                        if MIN_USD <= p_val <= MAX_USD:
                            results.append({
                                "source": "SideProjectors",
                                "title": title.inner_text().strip(),
                                "price": f"${p_val:,}",
                                "url": f"https://www.sideprojectors.com{link.get_attribute('href')}"
                            })
                    except: continue
            browser.close()
    except Exception as e:
        print(f"SideProjectors error: {e}")
    return results

if __name__ == "__main__":
    # Gather data from all sources independently
    ef = get_empire_flippers()
    fl = scrape_flippa()
    sp = scrape_sideprojectors()
    
    all_data = ef + fl + sp
    
    if all_data:
        df = pd.DataFrame(all_data).drop_duplicates(subset=['url'])
        # Optional: Convert USD prices back to a GBP display estimate
        df.to_csv("eu_businesses.csv", index=False)
        print(f"Successfully cooked {len(df)} digital assets.")
    else:
        print("No data found today.")
