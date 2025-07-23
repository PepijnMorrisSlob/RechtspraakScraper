# RechtspraakScraper

A powerful web scraper for Dutch law cases from https://uitspraken.rechtspraak.nl/

## Purpose
This project automates the extraction of legal case data from the Dutch Rechtspraak website, supporting research, data analysis, and legal tech applications.

## Features
- Scrapes thousands of cases in batches (e.g., 5000 at a time)
- Supports all major Dutch law categories (configurable)
- Handles session persistence and proxy integration
- Randomized delays to avoid detection
- Saves results in both TXT and CSV formats, named by subject and date range
- Progress tracking and resume support

## Setup
1. **Clone the repository:**
   ```sh
   git clone https://github.com/PepijnMorrisSlob/RechtspraakScraper.git
   cd RechtspraakScraper
   ```
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
3. **(Optional) Configure Google Drive or other integrations as needed.**

## Usage
- **Run the massive scraper:**
  ```sh
  python scraper_massive.py --subject Vreemdelingenrecht
  ```
- **Change law category:**
  Edit `config.py` or use the `--subject` argument.
- **Batch scraping:**
  The scraper will click "Load More" 500 times per batch, saving after each batch, and continue until all cases are scraped.

## Security
- **Do NOT commit credentials** (e.g., Google Cloud JSON files) to the repository.
- Add sensitive files to `.gitignore`.

## Collaboration
- Fork or clone the repo, create branches, and submit pull requests for changes.

## License
MIT License (add your license text here) 