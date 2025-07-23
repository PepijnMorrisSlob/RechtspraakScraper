import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Test URL
url = "https://uitspraken.rechtspraak.nl/resultaat?zoekterm=Aanbestedingsrecht&inhoudsindicatie=zt0&publicatiestatus=ps1&sort=UitspraakDatumDesc"

ua = UserAgent()
headers = {"User-Agent": ua.random}

try:
    with httpx.Client(headers=headers, timeout=30) as client:
        resp = client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        
        print("=== HTML Structure Analysis ===")
        print(f"Status: {resp.status_code}")
        print(f"Title: {soup.title.get_text() if soup.title else 'No title'}")
        
        # Test the case number selector you provided
        case_numbers = soup.select("h2.rs-panel-title")
        print(f"\nCase numbers found with 'h2.rs-panel-title': {len(case_numbers)}")
        for i, case in enumerate(case_numbers[:3]):  # Show first 3
            print(f"  {i+1}. {case.get_text(strip=True)}")
        
        # Look for case links (clickable elements)
        case_links = soup.select("a[href*='details']")
        print(f"\nCase links with 'details' in href: {len(case_links)}")
        for i, link in enumerate(case_links[:3]):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            print(f"  {i+1}. {text[:50]}... -> {href}")
        
        # Look for panel containers (might contain case info)
        panels = soup.select(".rs-panel")
        print(f"\nPanels found with '.rs-panel': {len(panels)}")
        
        # Look for any elements with 'rs-' classes
        rs_elements = soup.select("[class*='rs-']")
        rs_classes = set()
        for elem in rs_elements:
            for class_name in elem.get('class', []):
                if class_name.startswith('rs-'):
                    rs_classes.add(class_name)
        print(f"\nAll 'rs-' classes found: {list(rs_classes)}")
        
        # Look for common patterns
        patterns = [
            "a[href*='ECLI']",
            ".resultaat",
            ".search-result", 
            ".case-item",
            ".panel",
            "h1", "h2", "h3",
            ".title",
            ".content"
        ]
        
        print(f"\n=== Testing Common Selectors ===")
        for pattern in patterns:
            elements = soup.select(pattern)
            if elements:
                print(f"'{pattern}': {len(elements)} elements found")
                if len(elements) <= 3:
                    for elem in elements:
                        text = elem.get_text(strip=True)[:50]
                        print(f"  - {text}...")
        
        # Save full HTML for manual inspection
        with open("debug/full_page.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print("\nFull HTML saved to debug/full_page.html")
        
except Exception as e:
    print(f"Error: {e}") 