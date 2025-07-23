import time
import pandas as pd
from tqdm import tqdm
from fake_useragent import UserAgent
import os
import re
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import config
import argparse
import random
import threading

stop_loading_flag = threading.Event()
stop_loading_flag.clear()  # Not stopping by default

class MassiveLawScraper:
    def __init__(self, proxies=None, start_url=None, subject=None):
        self.ua = UserAgent()
        self.data = []
        self.case_urls = []
        self.driver = None
        self.current_page = 1
        self.cases_found = 0
        self.proxies = proxies or []
        self.current_proxy_index = 0
        self.start_url = start_url
        self.subject = subject
        
        # Create output directory
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        
        # Initialize progress tracking
        self.progress_file = os.path.join(config.OUTPUT_DIR, "scraping_progress.json")
        self.load_progress()
    
    def load_progress(self):
        """Load progress from previous run"""
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                progress = json.load(f)
                self.current_page = progress.get('current_page', 1)
                self.cases_found = progress.get('cases_found', 0)
                print(f"Resuming from page {self.current_page} with {self.cases_found} cases already found")
    
    def save_progress(self):
        """Save current progress"""
        progress = {
            'current_page': self.current_page,
            'cases_found': self.cases_found,
            "proxy_index": self.current_proxy_index, # Add proxy index to progress
            'timestamp': datetime.now().isoformat()
        }
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f)

    def get_default_url(self):
        """Get the default URL with correct date range parameters"""
        return "https://uitspraken.rechtspraak.nl/resultaat?zoekterm=vreemdelingenrecht&inhoudsindicatie=zt0&publicatiestatus=ps1&sort=UitspraakDatumDesc&uitspraakdatumrange=tussen&uitspraakdatuma=03-03-1984&uitspraakdatumb=19-06-2025"
    
    def get_next_proxy(self):
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_proxy_index % len(self.proxies)]
        self.current_proxy_index += 1
        print(f"[Proxy] Using proxy: {proxy}")
        return proxy

    def setup_driver(self, proxy=None):
        """Setup Chrome driver with options"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'--user-agent={self.ua.random}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        if proxy:
            options.add_argument(f'--proxy-server={proxy}')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    def extract_rechtsgebieden(self):
        rechtsgebieden = []
        if not self.driver:
            print("[Error] WebDriver is not initialized when extracting rechtsgebieden.")
            return rechtsgebieden
        try:
            elems = self.driver.find_elements(By.CSS_SELECTOR, 'span.hl0')
            rechtsgebieden = [e.text.strip() for e in elems if e.text.strip()]
        except Exception as e:
            print(f"[Error] Could not extract rechtsgebieden: {e}")
        return rechtsgebieden

    def extract_case_content(self, url):
        if not self.driver:
            print("[Error] WebDriver is not initialized when extracting case content.")
            return None
        try:
            if not self.driver:
                print("[Error] WebDriver is not initialized before get().")
                return None
            self.driver.get(url)
            time.sleep(2)
            
            # Extract ECLI code from URL
            ecli_match = re.search(r'ECLI:([^&]+)', url)
            ecli_code = ecli_match.group(1) if ecli_match else ""
            
            # Extract title
            title = ""
            title_selectors = [
                "h2.rs-panel-title",
                "h1",
                ".title",
                ".case-title"
            ]
            for selector in title_selectors:
                try:
                    if not self.driver:
                        continue
                    title_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip()
                    if title:
                        break
                except:
                    continue
            
            # Extract content with multiple methods
            content = ""
            content_selectors = [
                "div.rnl-detail-uitspraaktekst.printthis.ng-star-inserted",
                ".rnl-detail-uitspraaktekst--content",
                ".uitspraak",
                ".content",
                ".case-content",
                "main",
                ".uitspraak-tekst",
                ".case-text"
            ]
            
            for selector in content_selectors:
                try:
                    if not self.driver:
                        continue
                    content_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    content = content_elem.text.strip()
                    if len(content) > 100:  # Ensure we got meaningful content
                        break
                except:
                    continue
            
            # If no content found, try getting all text from body
            if not content or len(content) < 100:
                try:
                    if not self.driver:
                        pass
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    content = body.text.strip()
                except:
                    pass
            
            # Extract court information
            court = ""
            court_selectors = [
                "//label[contains(text(), 'Instantie')]/following-sibling::span",
                "//label[contains(text(), 'Rechter')]/following-sibling::span",
                ".court",
                ".rechter"
            ]
            
            for selector in court_selectors:
                try:
                    if not self.driver:
                        continue
                    if selector.startswith("//"):
                        court_elem = self.driver.find_element(By.XPATH, selector)
                    else:
                        court_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    court = court_elem.text.strip()
                    if court:
                        break
                except:
                    continue
            
            # Extract date uitspraak
            date_uitspraak = ""
            try:
                date_uitspraak_elem = self.driver.find_element(By.XPATH, "//label[contains(text(), 'Datum uitspraak')]/following-sibling::span")
                date_uitspraak = date_uitspraak_elem.text.strip()
            except:
                pass
            # Extract date publicatie
            date_publicatie = ""
            try:
                date_publicatie_elem = self.driver.find_element(By.XPATH, "//label[contains(text(), 'Datum publicatie')]/following-sibling::span")
                date_publicatie = date_publicatie_elem.text.strip()
            except:
                pass
            
            # Extract date (main date)
            date = ""
            date_selectors = [
                "//label[contains(text(), 'Datum')]/following-sibling::span",
                ".date",
                ".datum"
            ]
            
            for selector in date_selectors:
                try:
                    if not self.driver:
                        continue
                    if selector.startswith("//"):
                        date_elem = self.driver.find_element(By.XPATH, selector)
                    else:
                        date_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    date = date_elem.text.strip()
                    if date:
                        break
                except:
                    continue
            
            # Extract inhoudsindicatie
            inhoudsindicatie = ""
            try:
                inhoudsindicatie_elem = self.driver.find_element(By.XPATH, "//label[contains(text(), 'Inhoudsindicatie')]/following-sibling::span")
                inhoudsindicatie = inhoudsindicatie_elem.text.strip()
            except:
                pass
            
            # Extract rechtsgebieden
            rechtsgebieden = self.extract_rechtsgebieden()
            
            # Check if this case matches our subject
            if self.subject and rechtsgebieden:
                subject_found = False
                for rechtsgebied in rechtsgebieden:
                    if self.subject.lower() in rechtsgebied.lower():
                        subject_found = True
                        break
                if not subject_found:
                    print(f"[Filter] Skipping case - subject '{self.subject}' not found in rechtsgebieden: {rechtsgebieden}")
                    return None
            
            case_data = {
                'ecli_code': ecli_code,
                'title': title,
                'court': court,
                'date': date,
                'date_uitspraak': date_uitspraak,
                'date_publicatie': date_publicatie,
                'inhoudsindicatie': inhoudsindicatie,
                'content': content,
                'url': url,
                'rechtsgebieden': ', '.join(rechtsgebieden) if rechtsgebieden else ''
            }
            
            # Add random delay between case extractions (3.00 to 3.50 seconds)
            delay = random.uniform(3.00, 3.50)
            print(f"[Stealth] Sleeping for {delay:.2f} seconds after extracting a case...")
            time.sleep(delay)
            
            return case_data
            
        except Exception as e:
            print(f"[Error] Failed to extract case content from {url}: {e}")
            return None

    def scrape_search_page(self, page):
        """Scrape search results page and yield case URLs"""
        if not self.driver:
            print("[Error] WebDriver is not initialized when scraping search page.")
            return
        
        # Construct URL with date range - continue from oldest date (19-06-2025) to 03-03-1984
        url = self.start_url or "https://uitspraken.rechtspraak.nl/resultaat?zoekterm=vreemdelingenrecht&inhoudsindicatie=zt0&publicatiestatus=ps1&sort=UitspraakDatumDesc&uitspraakdatumrange=tussen&uitspraakdatuma=03-03-1984&uitspraakdatumb=19-06-2025"
        
        try:
            print(f"[Page {page}] Loading search results...")
            self.driver.get(url)
            time.sleep(3)
            
            # Click "Load More" button in batches
            batch_size = 500  # Increased from 100 to 500 clicks
            total_clicks = 0
            
            while True:
                try:
                    # Check if user wants to stop loading more results
                    if stop_loading_flag.is_set():
                        print("[User] Stopping loading more results as requested.")
                        break
                    
                    # Look for "Laad meer resultaten" button with more comprehensive selectors
                    load_more_button = None
                    button_selectors = [
                        "//button[contains(text(), 'Laad meer resultaten')]",
                        "//button[contains(text(), 'Load more results')]",
                        "//button[contains(text(), 'Laad meer')]",
                        "//button[contains(text(), 'Load more')]",
                        "//a[contains(text(), 'Laad meer resultaten')]",
                        "//a[contains(text(), 'Load more results')]",
                        "//a[contains(text(), 'Laad meer')]",
                        "//a[contains(text(), 'Load more')]",
                        "button#lib-rnl-lib-rnl-laadMeerBtn",
                        ".load-more",
                        ".load-more-results",
                        "[data-testid='load-more']",
                        ".btn-load-more",
                        "button[type='button']",
                        "//button[@class='btn btn-primary']",
                        "//button[@class='btn btn-secondary']"
                    ]
                    
                    print(f"[Page {page}] Looking for 'Load More' button...")
                    for i, selector in enumerate(button_selectors):
                        try:
                            if selector.startswith("//"):
                                elements = self.driver.find_elements(By.XPATH, selector)
                            else:
                                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    button_text = element.text.strip().lower()
                                    if any(keyword in button_text for keyword in ['laad meer', 'load more', 'meer', 'more']):
                                        load_more_button = element
                                        print(f"[Page {page}] Found 'Load More' button with selector {i}: '{element.text}'")
                                        break
                            
                            if load_more_button:
                                break
                        except Exception as e:
                            print(f"[Debug] Selector {i} failed: {e}")
                            continue
                    
                    if not load_more_button:
                        print(f"[Page {page}] No 'Load More' button found. Checking page content...")
                        # Debug: print all buttons on the page
                        try:
                            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                            print(f"[Debug] Found {len(all_buttons)} buttons on page:")
                            for i, btn in enumerate(all_buttons[:10]):  # Show first 10 buttons
                                if btn.is_displayed():
                                    print(f"  Button {i}: '{btn.text}' (class: {btn.get_attribute('class')})")
                        except:
                            pass
                        print(f"[Page {page}] No more 'Load More' button found. All results loaded.")
                        break
                    
                    # Click the button
                    print(f"[Page {page}] Clicking 'Load More' button...")
                    self.driver.execute_script("arguments[0].click();", load_more_button)
                    total_clicks += 1
                    print(f"[Page {page}] Clicked 'Load More' button ({total_clicks} clicks so far)")
                    
                    # Wait a bit for content to load
                    time.sleep(2)
                    
                    # Check if we've reached the batch size
                    if total_clicks % batch_size == 0:
                        print(f"[Page {page}] Completed batch of {batch_size} clicks. Scraping current results...")
                        break
                        
                except Exception as e:
                    print(f"[Error] Failed to click 'Load More' button: {e}")
                    break
            
            # Extract case URLs from the loaded page
            case_links = []
            link_selectors = [
                "//a[contains(@href, 'details?id=ECLI')]",
                "//a[contains(@href, 'uitspraken.rechtspraak.nl')]",
                ".case-link",
                ".result-link",
                "a[href*='ECLI']",
                "a[href*='details']"
            ]
            
            print(f"[Page {page}] Extracting case URLs...")
            for selector in link_selectors:
                try:
                    if selector.startswith("//"):
                        links = self.driver.find_elements(By.XPATH, selector)
                    else:
                        links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for link in links:
                        href = link.get_attribute('href')
                        if href and 'ECLI' in href:
                            case_links.append(href)
                    
                    if case_links:
                        print(f"[Page {page}] Found {len(case_links)} case URLs with selector: {selector}")
                        break
                except Exception as e:
                    print(f"[Debug] Link selector failed: {e}")
                    continue
            
            print(f"[Page {page}] Total unique case URLs found: {len(set(case_links))}")
            
            # Yield each case URL
            for case_url in set(case_links):  # Remove duplicates
                yield case_url
                
        except Exception as e:
            print(f"[Error] Failed to scrape search page {page}: {e}")

    def update_url_with_oldest_date(self):
        """Update the start URL with the oldest date from previous scrapes"""
        try:
            # Find the oldest date from previous scrapes
            oldest_date = None
            
            # Check the most recent metadata file for the oldest date
            metadata_files = [f for f in os.listdir(config.OUTPUT_DIR) if f.startswith('cases_metadata_Vreemdelingenrecht_') and f.endswith('.csv')]
            
            if metadata_files:
                # Sort by modification time to get the most recent
                metadata_files.sort(key=lambda x: os.path.getmtime(os.path.join(config.OUTPUT_DIR, x)), reverse=True)
                latest_file = metadata_files[0]
                
                # Read the file to find the oldest date
                filepath = os.path.join(config.OUTPUT_DIR, latest_file)
                try:
                    df = pd.read_csv(filepath)
                    if 'date' in df.columns:
                        dates = df['date'].dropna().tolist()
                        if dates:
                            # Parse dates and find the oldest
                            parsed_dates = []
                            for date_str in dates:
                                if date_str and '-' in date_str:
                                    try:
                                        day, month, year = date_str.split('-')
                                        parsed_dates.append((int(year), int(month), int(day)))
                                    except:
                                        continue
                            
                            if parsed_dates:
                                oldest_parsed = min(parsed_dates)
                                oldest_date = f"{oldest_parsed[2]:02d}-{oldest_parsed[1]:02d}-{oldest_parsed[0]}"
                                print(f"[URL Update] Found oldest date from previous scrape: {oldest_date}")
                except Exception as e:
                    print(f"[Warning] Could not read metadata file to find oldest date: {e}")
            
            # If no oldest date found, use the default
            if not oldest_date:
                oldest_date = "19-06-2025"  # Default from previous scrape
                print(f"[URL Update] Using default oldest date: {oldest_date}")
            
            # Update the start URL with the correct date range parameters
            base_url = "https://uitspraken.rechtspraak.nl/resultaat?zoekterm=vreemdelingenrecht&inhoudsindicatie=zt0&publicatiestatus=ps1&sort=UitspraakDatumDesc"
            self.start_url = f"{base_url}&uitspraakdatumrange=tussen&uitspraakdatuma=03-03-1984&uitspraakdatumb={oldest_date}"
            
            print(f"[URL Update] Updated start URL with date range: 03-03-1984 to {oldest_date}")
            
        except Exception as e:
            print(f"[Error] Failed to update URL with oldest date: {e}")
            # Fallback to default URL with correct parameters
            self.start_url = "https://uitspraken.rechtspraak.nl/resultaat?zoekterm=vreemdelingenrecht&inhoudsindicatie=zt0&publicatiestatus=ps1&sort=UitspraakDatumDesc&uitspraakdatumrange=tussen&uitspraakdatuma=03-03-1984&uitspraakdatumb=19-06-2025"

    def save_to_txt(self):
        """Save scraped data to text file"""
        if not self.data:
            print("[Warning] No data to save")
            return
        
        # Determine date range
        dates = [case['date'] for case in self.data if case.get('date')]
        if dates:
            # Parse dates in DD-MM-YYYY format
            try:
                parsed_dates = []
                for date_str in dates:
                    if date_str and '-' in date_str:
                        day, month, year = date_str.split('-')
                        parsed_dates.append(f"{year}{month}{day}")
                
                if parsed_dates:
                    min_date = min(parsed_dates)
                    max_date = max(parsed_dates)
                    date_range = f"{min_date[:4]}{min_date[4:6]}{min_date[6:8]}_{max_date[:4]}{max_date[4:6]}{max_date[6:8]}"
                else:
                    date_range = datetime.now().strftime("%Y%m%d_%Y%m%d")
            except:
                date_range = datetime.now().strftime("%Y%m%d_%Y%m%d")
        else:
            date_range = datetime.now().strftime("%Y%m%d_%Y%m%d")
        
        subject_name = self.subject or "Vreemdelingenrecht"
        filename = f"all_cases_{subject_name}_{date_range}.txt"
        filepath = os.path.join(config.OUTPUT_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for case in self.data:
                f.write(f"ECLI Code: {case.get('ecli_code', '')}\n")
                f.write(f"Title: {case.get('title', '')}\n")
                f.write(f"Court: {case.get('court', '')}\n")
                f.write(f"Date: {case.get('date', '')}\n")
                f.write(f"Date Uitspraak: {case.get('date_uitspraak', '')}\n")
                f.write(f"Date Publicatie: {case.get('date_publicatie', '')}\n")
                f.write(f"Inhoudsindicatie: {case.get('inhoudsindicatie', '')}\n")
                f.write(f"Rechtsgebieden: {case.get('rechtsgebieden', '')}\n")
                f.write(f"URL: {case.get('url', '')}\n")
                f.write(f"Content:\n{case.get('content', '')}\n")
                f.write("-" * 80 + "\n\n")
        
        print(f"[Save] Saved {len(self.data)} cases to {filepath}")

    def save_metadata_csv(self):
        """Save metadata to CSV file"""
        if not self.data:
            print("[Warning] No data to save")
            return
        
        # Determine date range
        dates = [case['date'] for case in self.data if case.get('date')]
        if dates:
            try:
                parsed_dates = []
                for date_str in dates:
                    if date_str and '-' in date_str:
                        day, month, year = date_str.split('-')
                        parsed_dates.append(f"{year}{month}{day}")
                
                if parsed_dates:
                    min_date = min(parsed_dates)
                    max_date = max(parsed_dates)
                    date_range = f"{min_date[:4]}{min_date[4:6]}{min_date[6:8]}_{max_date[:4]}{max_date[4:6]}{max_date[6:8]}"
                else:
                    date_range = datetime.now().strftime("%Y%m%d_%Y%m%d")
            except:
                date_range = datetime.now().strftime("%Y%m%d_%Y%m%d")
        else:
            date_range = datetime.now().strftime("%Y%m%d_%Y%m%d")
        
        subject_name = self.subject or "Vreemdelingenrecht"
        filename = f"cases_metadata_{subject_name}_{date_range}.csv"
        filepath = os.path.join(config.OUTPUT_DIR, filename)
        
        df = pd.DataFrame(self.data)
        df.to_csv(filepath, index=False, encoding='utf-8')
        print(f"[Save] Saved metadata for {len(self.data)} cases to {filepath}")

    def run(self):
        """Main scraping loop"""
        print(f"[Start] Starting massive scraping for {self.subject or 'Vreemdelingenrecht'}")
        
        # Set the URL properly - either from start_url or default
        if not self.start_url:
            self.start_url = self.get_default_url()
        
        # Only update URL with oldest date if we're starting fresh (no progress file exists)
        # or if we're resuming from a stopped session
        if not os.path.exists(self.progress_file):
            print("[New Session] No progress file found. Updating URL with oldest date from previous scrapes...")
            self.update_url_with_oldest_date()
        else:
            print("[Resume] Progress file found. Continuing with existing URL and progress.")
            # Ensure we have a valid URL when resuming
            if not self.start_url:
                self.start_url = self.get_default_url()
        
        print(f"[URL] Using URL: {self.start_url}")
        print(f"[Batch Size] 500 clicks per batch before extracting cases")
        
        try:
            self.setup_driver()
            
            page = self.current_page
            while page <= config.MAX_PAGES:
                print(f"\n[Page {page}] Starting to scrape page {page}")
                
                # Scrape search page and get case URLs
                case_urls = list(self.scrape_search_page(page))
                
                if not case_urls:
                    print(f"[Page {page}] No case URLs found. Moving to next page.")
                    page += 1
                    continue
                
                print(f"[Page {page}] Found {len(case_urls)} case URLs. Starting extraction...")
                
                # Extract content from each case
                for i, case_url in enumerate(case_urls, 1):
                    print(f"[Page {page}] Extracting case {i}/{len(case_urls)}: {case_url}")
                    
                    case_data = self.extract_case_content(case_url)
                    if case_data:
                        self.data.append(case_data)
                        self.cases_found += 1
                        print(f"[Page {page}] Successfully extracted case {self.cases_found}")
                    else:
                        print(f"[Page {page}] Failed to extract case data")
                
                # Save progress after each page
                self.save_progress()
                
                # Save data periodically
                if page % 5 == 0 or page == config.MAX_PAGES:
                    self.save_to_txt()
                    self.save_metadata_csv()
                
                page += 1
                self.current_page = page
                
                # Check if we should continue to next page
                if page > config.MAX_PAGES:
                    print(f"[Complete] Reached maximum pages ({config.MAX_PAGES})")
                    break
            
            # Final save
            self.save_to_txt()
            self.save_metadata_csv()
            
            print(f"[Complete] Scraping completed. Total cases found: {self.cases_found}")
            
        except KeyboardInterrupt:
            print("\n[Interrupt] Scraping interrupted by user")
            self.save_progress()
            self.save_to_txt()
            self.save_metadata_csv()
        except Exception as e:
            print(f"[Error] Scraping failed: {e}")
            self.save_progress()
            self.save_to_txt()
            self.save_metadata_csv()
        finally:
            if self.driver:
                self.driver.quit()

def main():
    parser = argparse.ArgumentParser(description='Massive Law Case Scraper')
    parser.add_argument('--subject', default='Vreemdelingenrecht', help='Subject to search for')
    parser.add_argument('--url', help='Custom start URL')
    parser.add_argument('--proxies', nargs='+', help='List of proxy servers')
    parser.add_argument('--fresh', action='store_true', help='Start fresh (ignore progress)')
    
    args = parser.parse_args()
    
    # Clear progress if fresh start requested
    if args.fresh:
        progress_file = os.path.join(config.OUTPUT_DIR, "scraping_progress.json")
        if os.path.exists(progress_file):
            os.remove(progress_file)
            print("[Fresh] Cleared previous progress")
    
    # Start interactive thread for user commands
    def check_user_input():
        while True:
            try:
                user_input = input()
                if user_input.strip().lower() == 's':
                    stop_loading_flag.set()
                    print("[User] Stop loading flag set. Will stop loading more results after current batch.")
            except EOFError:
                break
    
    input_thread = threading.Thread(target=check_user_input, daemon=True)
    input_thread.start()
    
    # Create and run scraper
    scraper = MassiveLawScraper(
        proxies=args.proxies,
        start_url=args.url,
        subject=args.subject
    )
    
    scraper.run()

if __name__ == "__main__":
    main() 