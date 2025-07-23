import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent

def debug_search():
    """Debug the search to see what's happening"""
    ua = UserAgent()
    
    # Setup driver
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--user-agent={ua.random}')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # Test different search URLs
        search_urls = [
            "https://uitspraken.rechtspraak.nl/resultaat?zoekterm=Bestuursrecht&inhoudsindicatie=&publicatiestatus=ps1&sort=UitspraakDatumDesc",
            "https://uitspraken.rechtspraak.nl/resultaat?zoekterm=Bestuursrecht&inhoudsindicatie=zt0&publicatiestatus=ps1&sort=UitspraakDatumDesc",
            "https://uitspraken.rechtspraak.nl/resultaat?zoekterm=Bestuursrecht&publicatiestatus=ps1&sort=UitspraakDatumDesc",
            "https://uitspraken.rechtspraak.nl/resultaat?zoekterm=Bestuursrecht"
        ]
        
        for i, url in enumerate(search_urls, 1):
            print(f"\n=== Testing URL {i} ===")
            print(f"URL: {url}")
            
            driver.get(url)
            time.sleep(5)
            
            # Check page title
            title = driver.title
            print(f"Page title: {title}")
            
            # Look for result count
            try:
                result_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='result']")
                print(f"Elements with 'result' in class: {len(result_elements)}")
                
                # Look for any text mentioning number of results
                page_text = driver.find_element(By.TAG_NAME, "body").text
                if "resultaten" in page_text.lower():
                    print("Found 'resultaten' in page text")
                
                # Count case links
                case_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='details']")
                print(f"Case links found: {len(case_links)}")
                
                if case_links:
                    print("First few case URLs:")
                    for link in case_links[:3]:
                        href = link.get_attribute('href')
                        print(f"  - {href}")
                
            except Exception as e:
                print(f"Error analyzing page: {e}")
            
            print("-" * 50)
    
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_search() 