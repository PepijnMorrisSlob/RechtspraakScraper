import pandas as pd
from memory_bank import LawCaseMemoryBank
import os

def main():
    """Simple interface for the law case memory bank"""
    print("=== Dutch Law Cases Memory Bank ===\n")
    
    # Initialize memory bank
    memory_bank = LawCaseMemoryBank()
    
    while True:
        print("\nOptions:")
        print("1. Load scraped data and vectorize")
        print("2. Search similar cases")
        print("3. Get case by ECLI code")
        print("4. Show statistics")
        print("5. Export all cases to CSV")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            if os.path.exists("run/scraped_cases.csv"):
                print("Loading scraped cases...")
                scraped_df = pd.read_csv("run/scraped_cases.csv")
                memory_bank.add_cases(scraped_df, source="scraper")
                memory_bank.vectorize_cases()
                print("✓ Data loaded and vectorized!")
            else:
                print("❌ No scraped data found. Run the scraper first.")
        
        elif choice == "2":
            query = input("Enter your search query: ").strip()
            if query:
                results = memory_bank.search_similar_cases(query, top_k=5)
                if results:
                    print(f"\nTop {len(results)} similar cases:")
                    for i, result in enumerate(results, 1):
                        print(f"\n{i}. {result['title']}")
                        print(f"   ECLI: {result['ecli_code']}")
                        print(f"   Court: {result['court']}")
                        print(f"   Date: {result['date']}")
                        print(f"   Similarity: {result['similarity']:.3f}")
                        print(f"   URL: {result['url']}")
                else:
                    print("No similar cases found.")
            else:
                print("Please enter a search query.")
        
        elif choice == "3":
            ecli_code = input("Enter ECLI code: ").strip()
            if ecli_code:
                case = memory_bank.get_case_by_ecli(ecli_code)
                if case:
                    print(f"\nCase found:")
                    print(f"Title: {case['title']}")
                    print(f"ECLI: {case['ecli_code']}")
                    print(f"Court: {case['court']}")
                    print(f"Date: {case['date']}")
                    print(f"URL: {case['url']}")
                    print(f"Content preview: {case['content'][:200]}...")
                else:
                    print("Case not found.")
            else:
                print("Please enter an ECLI code.")
        
        elif choice == "4":
            stats = memory_bank.get_statistics()
            print(f"\nMemory Bank Statistics:")
            print(f"Total cases: {stats['total_cases']}")
            print(f"Vectorized: {stats['vectorized']}")
            print(f"Data sources: {stats['data_sources']}")
            
            if stats['courts']:
                print(f"\nCourts represented:")
                for court, count in list(stats['courts'].items())[:10]:
                    print(f"  {court}: {count} cases")
            
            if stats['date_range']:
                print(f"\nDate range:")
                print(f"  Earliest: {stats['date_range']['earliest']}")
                print(f"  Latest: {stats['date_range']['latest']}")
        
        elif choice == "5":
            output_file = memory_bank.export_to_csv()
            if output_file:
                print(f"✓ Exported to: {output_file}")
        
        elif choice == "6":
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please enter 1-6.")

if __name__ == "__main__":
    main() 