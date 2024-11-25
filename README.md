# Pine Script Reference Scraper

A web scraper designed to extract documentation from TradingView's Pine Script Reference v5. The scraper captures function definitions, types, variables, constants, keywords, operators, and annotations.

## Versions

There are two versions of the scraper:

### 1. Sample Scraper (`pine_script_scraper_sample.py`)
- Scrapes only 3 examples of each type for testing purposes
- Faster execution time
- Useful for testing and development
- Example output will contain ~21 items (3 items × 7 types)
- Code modification: Contains `all_links.extend(pattern_links[:3])` in the `find_specific_links()` method

### 2. Full Scraper (`pine_script_scraper.py`)
- Scrapes all available documentation
- Longer execution time
- Comprehensive documentation capture
- Will contain hundreds of items
- Code modification: Contains `all_links.extend(pattern_links)` in the `find_specific_links()` method#   C o l i n - C a v a l a n c i a  
 