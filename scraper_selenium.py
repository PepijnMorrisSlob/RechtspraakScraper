import time
import pandas as pd
from tqdm import tqdm
from fake_useragent import UserAgent
import os
import re
import random
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Configurable output path
OUTPUT_CSV = r"run\scraped_cases.csv"  # Save to run folder

# Base URLs
SEARCH_URL = "https://uitspraken.rechtspraak.nl/resultaat?zoekterm=Aanbestedingsrecht&inhoudsindicatie=zt0&publicatiestatus=ps1&sort=UitspraakDatumDesc"
BASE_URL = "https://uitspraken.rechtspraak.nl"

# User-Agent rotation
ua = UserAgent()

# Placeholder for results
data = []

# Example: Scrape first N pages (update as needed)
N_PAGES = 2

# Create run directory if it doesn't exist
os.makedirs("run", exist_ok=True)
os.makedirs("debug", exist_ok=True)

def fetch_free_proxies():
    """Fetch a list of free proxies from a public source"""
    print("Fetching free proxies...")
    url = "https://www.proxy-list.download/api/v1/get?type=https"
    try:
        resp = requests.get(url, timeout=10)
        proxies = resp.text.strip().split('\n')
        proxies = [p for p in proxies if p]
        print(f"Found {len(proxies)} proxies.")
        return proxies
    except Exception as e:
        print(f"Failed to fetch proxies: {e}")
        return []

def setup_driver(proxy=None):
    """Setup Chrome driver with options and optional proxy"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in background
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--user-agent={ua.random}')
    if proxy:
        options.add_argument(f'--proxy-server=https://{proxy}')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def extract_case_details(driver, url):
    """Extract detailed information from a case page using Selenium"""
    try:
        driver.get(url)
        time.sleep(2)  # Wait for page to load
        
        # Extract ECLI code from URL
        ecli_match = re.search(r'ECLI:([^&]+)', url)
        ecli_code = ecli_match.group(1) if ecli_match else ""
        
        # Extract case title
        try:
            title_elem = driver.find_element(By.CSS_SELECTOR, "h2.rs-panel-title")
            title = title_elem.text.strip()
        except:
            title = ""
        
        # Extract case content
        try:
            content_elem = driver.find_element(By.CSS_SELECTOR, "div.rnl-detail-uitspraaktekst.printthis.ng-star-inserted")
            content = content_elem.text.strip()
        except:
            content = ""
        
        # Extract court information
        try:
            court_elem = driver.find_element(By.XPATH, "//label[contains(text(), 'Instantie')]/following-sibling::span")
            court = court_elem.text.strip()
        except:
            court = ""
        
        # Extract date information
        try:
            date_elem = driver.find_element(By.XPATH, "//label[contains(text(), 'Datum uitspraak')]/following-sibling::span")
            date = date_elem.text.strip()
        except:
            date = ""
        
        return {
            "ecli_code": ecli_code,
            "title": title,
            "court": court,
            "date": date,
            "content": content[:2000],  # Limit content length
            "url": url
        }
        
    except Exception as e:
        print(f"Error extracting details from {url}: {e}")
        return None

def main():
    proxies = fetch_free_proxies()
    proxy_idx = 0
    driver = None
    
    # Try proxies until one works
    while proxy_idx < len(proxies):
        proxy = proxies[proxy_idx]
        print(f"Trying proxy: {proxy}")
        try:
            driver = setup_driver(proxy=proxy)
            driver.set_page_load_timeout(20)
            driver.get(SEARCH_URL)
            time.sleep(5)
            if "Rechtspraak" in driver.title:
                print(f"Proxy {proxy} works!")
                break
            else:
                print(f"Proxy {proxy} failed (wrong title)")
                driver.quit()
        except Exception as e:
            print(f"Proxy {proxy} failed: {e}")
            if driver:
                driver.quit()
        proxy_idx += 1
    else:
        print("No working proxy found. Exiting.")
        return
    
    try:
        # Step 1: Get case URLs from search results
        case_urls = []
        
        for page in tqdm(range(1, N_PAGES + 1), desc="Scraping search pages"):
            url = f"{SEARCH_URL}&page={page}"
            driver.get(url)
            time.sleep(5)
            print(f"\nPage {page}: Loading results...")
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='details']"))
                )
            except:
                print("No case links found, trying alternative selectors...")
            case_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='details']")
            if not case_links:
                case_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='ECLI']")
            print(f"Found {len(case_links)} potential case links on page {page}")
            for link in case_links:
                href = link.get_attribute('href')
                if href and ('details?id=' in href or 'ECLI' in href):
                    if href not in case_urls:
                        case_urls.append(href)
                        print(f"  - Found case URL: {href}")
            time.sleep(2)  # Be polite to the server
        print(f"\nTotal unique case URLs found: {len(case_urls)}")
        # Step 2: Extract details from each case page
        for i, case_url in enumerate(tqdm(case_urls, desc="Extracting case details")):
            case_data = extract_case_details(driver, case_url)
            if case_data:
                data.append(case_data)
                print(f"  - Extracted: {case_data['ecli_code']} - {case_data['title'][:50]}...")
            time.sleep(1)  # Be polite to the server
        # Save to CSV
        if data:
            df = pd.DataFrame(data)
            df.to_csv(OUTPUT_CSV, index=False)
            print(f"\nSaved {len(data)} cases to {OUTPUT_CSV}")
        else:
            print("\nNo cases found. Check the website structure or selectors.")
    finally:
        driver.quit()

if __name__ == "__main__":
    main() 