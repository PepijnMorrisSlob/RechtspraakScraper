import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import os
import json
from datetime import datetime
import re

class LawCaseMemoryBank:
    """Memory bank for storing and analyzing Dutch law cases"""
    
    def __init__(self, data_dir="memory_bank"):
        self.data_dir = data_dir
        self.cases_file = os.path.join(data_dir, "cases.csv")
        self.vectors_file = os.path.join(data_dir, "case_vectors.pkl")
        self.metadata_file = os.path.join(data_dir, "metadata.json")
        self.vectorizer_file = os.path.join(data_dir, "vectorizer.pkl")
        
        # Create directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize data structures
        self.cases_df = None
        self.vectorizer = None
        self.case_vectors = None
        self.metadata = self._load_metadata()
        
        # Load existing data
        self._load_data()
    
    def _load_metadata(self):
        """Load or create metadata"""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_cases": 0,
                "vectorized": False,
                "search_terms": [],
                "data_sources": []
            }
    
    def _save_metadata(self):
        """Save metadata"""
        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata["total_cases"] = len(self.cases_df) if self.cases_df is not None else 0
        
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
    
    def _load_data(self):
        """Load existing cases and vectors"""
        # Load cases
        if os.path.exists(self.cases_file):
            self.cases_df = pd.read_csv(self.cases_file)
            print(f"Loaded {len(self.cases_df)} existing cases")
        else:
            self.cases_df = pd.DataFrame()
            print("No existing cases found, starting fresh")
        
        # Load vectors if they exist
        if os.path.exists(self.vectors_file) and os.path.exists(self.vectorizer_file):
            with open(self.vectors_file, 'rb') as f:
                self.case_vectors = pickle.load(f)
            with open(self.vectorizer_file, 'rb') as f:
                self.vectorizer = pickle.load(f)
            self.metadata["vectorized"] = True
            print("Loaded existing vectors")
    
    def add_cases(self, new_cases_df, source="scraper"):
        """Add new cases to the memory bank"""
        if self.cases_df is None or self.cases_df.empty:
            self.cases_df = new_cases_df
        else:
            # Remove duplicates based on ECLI code
            combined_df = pd.concat([self.cases_df, new_cases_df], ignore_index=True)
            self.cases_df = combined_df.drop_duplicates(subset=['ecli_code'], keep='last')
        
        # Update metadata
        self.metadata["data_sources"].append({
            "source": source,
            "date": datetime.now().isoformat(),
            "cases_added": len(new_cases_df)
        })
        
        # Save data
        self.cases_df.to_csv(self.cases_file, index=False)
        self._save_metadata()
        
        # Reset vectors since we have new data
        self.metadata["vectorized"] = False
        self.case_vectors = None
        self.vectorizer = None
        
        print(f"Added {len(new_cases_df)} new cases. Total cases: {len(self.cases_df)}")
    
    def vectorize_cases(self, max_features=5000):
        """Create TF-IDF vectors for case content"""
        if self.cases_df is None or self.cases_df.empty:
            print("No cases to vectorize")
            return
        
        # Combine title and content for vectorization
        texts = []
        for _, case in self.cases_df.iterrows():
            title = case.get('title', '')
            content = case.get('content', '')
            combined_text = f"{title} {content}"
            texts.append(combined_text)
        
        # Create TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95
        )
        
        # Fit and transform
        self.case_vectors = self.vectorizer.fit_transform(texts)
        
        # Save vectors and vectorizer
        with open(self.vectors_file, 'wb') as f:
            pickle.dump(self.case_vectors, f)
        with open(self.vectorizer_file, 'wb') as f:
            pickle.dump(self.vectorizer, f)
        
        self.metadata["vectorized"] = True
        self._save_metadata()
        
        print(f"Vectorized {len(texts)} cases with {self.case_vectors.shape[1]} features")
    
    def search_similar_cases(self, query, top_k=5):
        """Search for cases similar to the query"""
        if not self.metadata["vectorized"]:
            print("Cases not vectorized yet. Running vectorization...")
            self.vectorize_cases()
        
        # Transform query
        query_vector = self.vectorizer.transform([query])
        
        # Calculate similarities
        similarities = cosine_similarity(query_vector, self.case_vectors).flatten()
        
        # Get top matches
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            case = self.cases_df.iloc[idx]
            results.append({
                'ecli_code': case['ecli_code'],
                'title': case['title'],
                'court': case['court'],
                'date': case['date'],
                'similarity': float(similarities[idx]),
                'url': case['url']
            })
        
        return results
    
    def get_case_by_ecli(self, ecli_code):
        """Get a specific case by ECLI code"""
        if self.cases_df is None:
            return None
        
        case = self.cases_df[self.cases_df['ecli_code'] == ecli_code]
        if not case.empty:
            return case.iloc[0].to_dict()
        return None
    
    def get_statistics(self):
        """Get memory bank statistics"""
        stats = {
            "total_cases": len(self.cases_df) if self.cases_df is not None else 0,
            "vectorized": self.metadata["vectorized"],
            "courts": {},
            "date_range": {},
            "data_sources": len(self.metadata["data_sources"])
        }
        
        if self.cases_df is not None and not self.cases_df.empty:
            # Court statistics
            court_counts = self.cases_df['court'].value_counts()
            stats["courts"] = court_counts.to_dict()
            
            # Date range
            if 'date' in self.cases_df.columns:
                dates = pd.to_datetime(self.cases_df['date'], errors='coerce')
                valid_dates = dates.dropna()
                if not valid_dates.empty:
                    stats["date_range"] = {
                        "earliest": valid_dates.min().strftime('%Y-%m-%d'),
                        "latest": valid_dates.max().strftime('%Y-%m-%d')
                    }
        
        return stats
    
    def export_to_csv(self, output_file=None):
        """Export all cases to CSV"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"run/law_cases_export_{timestamp}.csv"
        
        if self.cases_df is not None:
            self.cases_df.to_csv(output_file, index=False)
            print(f"Exported {len(self.cases_df)} cases to {output_file}")
            return output_file
        else:
            print("No cases to export")
            return None

# Example usage
if __name__ == "__main__":
    # Initialize memory bank
    memory_bank = LawCaseMemoryBank()
    
    # Check if we have scraped data to load
    if os.path.exists("run/scraped_cases.csv"):
        print("Loading scraped cases...")
        scraped_df = pd.read_csv("run/scraped_cases.csv")
        memory_bank.add_cases(scraped_df, source="initial_scraper")
        
        # Vectorize the cases
        memory_bank.vectorize_cases()
        
        # Show statistics
        stats = memory_bank.get_statistics()
        print("\nMemory Bank Statistics:")
        print(f"Total cases: {stats['total_cases']}")
        print(f"Vectorized: {stats['vectorized']}")
        print(f"Data sources: {stats['data_sources']}")
        
        if stats['courts']:
            print("\nCourts represented:")
            for court, count in list(stats['courts'].items())[:5]:
                print(f"  {court}: {count} cases")
    
    else:
        print("No scraped data found. Run the scraper first.") 