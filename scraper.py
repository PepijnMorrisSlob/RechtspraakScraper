import httpx
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm
from fake_useragent import UserAgent
import time
import os
import re

# Configurable output path
OUTPUT_CSV = r"run\scraped_cases.csv"  # Save to run folder

# Proxy support (set to None if not using)
PROXIES = None  # Example: {'http://': 'http://proxy:port', 'https://': 'http://proxy:port'}

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

def extract_case_details(url, headers):
    """Extract detailed information from a case page using correct selectors"""
    try:
        with httpx.Client(proxy=PROXIES, headers=headers, timeout=30) as client:
            resp = client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            
            # Extract ECLI code from URL
            ecli_match = re.search(r'ECLI:([^&]+)', url)
            ecli_code = ecli_match.group(1) if ecli_match else ""
            
            # Extract case title using the correct selector
            title_elem = soup.select_one("h2.rs-panel-title")
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Extract case content using the correct selector
            content_elem = soup.select_one("div.rnl-detail-uitspraaktekst.printthis.ng-star-inserted")
            content = content_elem.get_text(strip=True) if content_elem else ""
            
            # Extract court information using the correct selector
            court_elem = soup.select_one("div.rnl-details.printthis.ng-star-inserted div.rnl-detail.row:has(label:text('Instantie')) span.rnl-details-value")
            if not court_elem:
                # Fallback: look for any element containing court info
                court_elem = soup.find("label", text=lambda x: x and "Instantie" in str(x))
                if court_elem and court_elem.find_next_sibling():
                    court_elem = court_elem.find_next_sibling()
            court = court_elem.get_text(strip=True) if court_elem else ""
            
            # Extract date information using the correct selector
            date_elem = soup.select_one("div.rnl-details.printthis.ng-star-inserted div.rnl-detail.row:has(label:text('Datum uitspraak')) span.rnl-details-value")
            if not date_elem:
                # Fallback: look for any element containing date info
                date_elem = soup.find("label", text=lambda x: x and "Datum uitspraak" in str(x))
                if date_elem and date_elem.find_next_sibling():
                    date_elem = date_elem.find_next_sibling()
            date = date_elem.get_text(strip=True) if date_elem else ""
            
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

# Step 1: Get case URLs from search results
case_urls = []

for page in tqdm(range(1, N_PAGES + 1), desc="Scraping search pages"):
    url = f"{SEARCH_URL}&page={page}"
    headers = {"User-Agent": ua.random}
    try:
        with httpx.Client(proxy=PROXIES, headers=headers, timeout=30) as client:
            resp = client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            
            print(f"\nPage {page}: Status {resp.status_code}")
            
            # Use the correct selector for case links
            case_links = soup.select("div.rnl-details.printthis.ng-star-inserted a.koopUitspraak")
            if not case_links:
                # Fallback: look for any links with ECLI or details
                case_links = soup.select("a[href*='details?id=']")
            if not case_links:
                case_links = soup.select("a[href*='ECLI']")
                
            print(f"Found {len(case_links)} potential case links on page {page}")
            
            for link in case_links:
                href = link.get('href', '')
                if isinstance(href, str) and ('details?id=' in href or 'ECLI' in href):
                    full_url = BASE_URL + href if href.startswith('/') else href
                    if full_url not in case_urls:
                        case_urls.append(full_url)
                        print(f"  - Found case URL: {full_url}")
                        
        time.sleep(1)  # Be polite to the server
    except Exception as e:
        print(f"Error on page {page}: {e}")

print(f"\nTotal unique case URLs found: {len(case_urls)}")

# Step 2: Extract details from each case page
for i, case_url in enumerate(tqdm(case_urls, desc="Extracting case details")):
    headers = {"User-Agent": ua.random}
    case_data = extract_case_details(case_url, headers)
    
    if case_data:
        data.append(case_data)
        print(f"  - Extracted: {case_data['ecli_code']} - {case_data['title'][:50]}...")
    
    time.sleep(0.5)  # Be polite to the server

# Save to CSV
if data:
    df = pd.DataFrame(data)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved {len(data)} cases to {OUTPUT_CSV}")
else:
    print("\nNo cases found. Check the website structure or selectors.")
    # Save debug info if we have any response
    if 'resp' in locals():
        with open("debug/search_page_content.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print("Saved page content to debug/search_page_content.html for inspection") 