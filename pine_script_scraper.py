import time
import json
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, unquote
from selenium.common.exceptions import NoSuchElementException, TimeoutException

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class PineScriptScraper:
    def __init__(self, max_workers=5):
        self.base_url = "https://www.tradingview.com/pine-script-reference/v5/"
        self.type_mappings = {
            "#var_": "Variable",
            "#const_": "Constant",
            "#fun_": "Function",
            "#kw_": "Keyword",
            "#type_": "Type",
            "#op_": "Operator",
            "#an_": "Annotation"
        }
        self.max_workers = max_workers
        self.data = []

    def create_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        return webdriver.Chrome(options=chrome_options)

    def extract_section_content(self, container, header_text):
        try:
            header = container.find_element(By.XPATH, f".//div[contains(@class, 'tv-pine-reference-item__sub-header') and contains(., '{header_text}')]")
            content_elements = []
            next_element = header.find_element(By.XPATH, 'following-sibling::*[1]')
            while next_element and 'tv-pine-reference-item__sub-header' not in next_element.get_attribute('class'):
                content_elements.append(next_element)
                try:
                    next_element = next_element.find_element(By.XPATH, 'following-sibling::*[1]')
                except NoSuchElementException:
                    break
            content_texts = []
            for elem in content_elements:
                text = elem.get_attribute('textContent').strip()
                if text:
                    content_texts.append(text)
            return '\n'.join(content_texts).strip()
        except NoSuchElementException:
            return ''

    def extract_example_code(self, container):
        try:
            header = container.find_element(By.XPATH, f".//div[contains(@class, 'tv-pine-reference-item__sub-header') and contains(., 'Example')]")
            pre_element = header.find_element(By.XPATH, 'following-sibling::pre[1]')
            code_element = pre_element.find_element(By.XPATH, './/code')
            code_text = code_element.get_attribute('textContent').strip()
            return code_text
        except NoSuchElementException:
            return "No example found"

    def extract_content(self, driver, url):
        try:
            # Wait for the main content container
            container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "tv-pine-reference-item--selected"))
            )
            
            # Try to get the full title from the h3 header
            try:
                title_element = container.find_element(By.CLASS_NAME, "tv-pine-reference-item__header")
                full_title = title_element.text.strip()
                
                # Get the type from URL since we still need it for the title format
                fragment = unquote(urlparse(url).fragment)
                code_type = None
                for pattern, type_name in self.type_mappings.items():
                    if pattern.replace('#', '') in fragment:
                        code_type = type_name
                        break
                
                if code_type:
                    full_title = f"{code_type}: {full_title}"
                else:
                    logging.warning(f"Could not determine code type for URL: {url}")
                    return None
                    
            except NoSuchElementException:
                logging.warning(f"Could not find title element for URL: {url}")
                return None

            description = ""
            try:
                description_elem = container.find_element(By.CLASS_NAME, "tv-pine-reference-item__text")
                description = description_elem.text.strip()
            except NoSuchElementException:
                pass

            # Extract type
            type_text = self.extract_section_content(container, 'Type')

            # Extract syntax
            syntax = self.extract_section_content(container, 'Syntax')

            # Extract example
            example = self.extract_example_code(container)

            # Extract remarks
            remarks_text = self.extract_section_content(container, 'Remarks')
            remarks = remarks_text.split('\n') if remarks_text else []

            # Extract related topics
            related_topics = []
            try:
                see_also = container.find_element(By.CLASS_NAME, "tv-pine-reference-item__see-also")
                topics = see_also.find_elements(By.CLASS_NAME, "tv-tag-label")
                related_topics = [topic.text.strip() for topic in topics if topic.text.strip()]
            except NoSuchElementException:
                pass

            return {
                "title": full_title,
                "type": type_text,
                "description": description,
                "syntax": syntax,
                "example": example,
                "remarks": remarks,
                "related_topics": related_topics
            }

        except Exception as e:
            logging.error(f"Error extracting content from {url}: {str(e)}")
            return None

    def find_specific_links(self):
        driver = self.create_driver()
        try:
            driver.get(self.base_url)
            time.sleep(5)
            
            all_links = []
            for pattern in self.type_mappings.keys():
                elements = driver.find_elements(
                    By.CSS_SELECTOR, 
                    f"a[href*='{pattern}']"
                )
                pattern_links = [elem.get_attribute('href') for elem in elements]
                logging.info(f"Found {len(pattern_links)} links for pattern {pattern}")
                # Limit to 3 per type for testing
                all_links.extend(pattern_links[:3])  
            
            # Remove duplicates
            all_links = list(set(all_links))
            logging.info(f"Total unique links found: {len(all_links)}")
            return all_links
        finally:
            driver.quit()

    def scrape_page(self, url):
        driver = self.create_driver()
        try:
            driver.get(url)
            time.sleep(3)
            data = self.extract_content(driver, url)
            if data:
                logging.info(f"Scraped {data['title']}")
            return data
        finally:
            driver.quit()

    def scrape_all(self):
        links = self.find_specific_links()
        logging.info(f"Found {len(links)} links to scrape")
        
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self.scrape_page, links))
                
        self.data.extend([result for result in results if result])

    def save_to_json(self, filename="pine_script_reference.json"):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            logging.info(f"Data saved to {filename}")
        except Exception as e:
            logging.error(f"Error saving JSON: {str(e)}")

def main():
    scraper = PineScriptScraper(max_workers=5)
    scraper.scrape_all()
    scraper.save_to_json()

if __name__ == "__main__":
    main()