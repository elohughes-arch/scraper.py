import os
import pandas as pd
from playwright.sync_api import sync_playwright

def run_scraper():
    with sync_playwright() as p:
        # Launching browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to a European business marketplace
        # Example: Flippa with EU filters applied
        page.goto("https://www.flippa.com/search?filter%5Blocation%5D%5B%5D=Europe")
        
        # Logic to grab titles and prices (selectors will vary by site)
        listings = []
        # This is a placeholder selector; you'll need to inspect the site to get the real one
        elements = page.query_selector_all(".listing-card") 
        
        for el in elements:
            listings.append({
                "title": el.query_selector(".title").inner_text() if el.query_selector(".title") else "N/A",
                "price": el.query_selector(".price").inner_text() if el.query_selector(".price") else "N/A"
            })
        
        # Save to CSV
        df = pd.DataFrame(listings)
        df.to_csv("eu_businesses.csv", index=False)
        print("Scrape successful, file saved.")
        
        browser.close()

if __name__ == "__main__":
    run_scraper()
