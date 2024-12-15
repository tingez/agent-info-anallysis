import logging
import json
import time
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin
from dataclasses import dataclass, asdict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from pyquery import PyQuery as pq

logger = logging.getLogger(__name__)

@dataclass
class Agent:
    name: str
    url: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    source_url: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        self.tags = self.tags or []
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class AIDirectoryScraper:
    def __init__(self, base_url: str = "https://aiagentsdirectory.com"):
        self.base_url = base_url
        self.driver = None
        self._setup_logging()
        self.stats = {
            "total_categories": 0,
            "total_agents": 0,
            "agents_with_details": 0,
            "failed_details": 0
        }
    
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'ai_agents_scraper_{int(time.time())}.log'),
                logging.StreamHandler()
            ]
        )
    
    def _init_selenium(self):
        if not self.driver:
            logger.info("Initializing Selenium WebDriver...")
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(5)
    
    def get_categories(self) -> Dict[str, str]:
        """Get all categories from the directory"""
        logger.info("Starting category extraction...")
        self._init_selenium()
        self.driver.get(self.base_url)
        time.sleep(2)
        
        doc = pq(self.driver.page_source)
        categories = {}
        
        # Find category links
        for elem in doc('a[href^="/category"]').items():
            href = elem.attr('href')
            logger.info(f"Found href: {href}")
            if href and not any(skip in href.lower() for skip in ['/blog', '/sponsor', '/submit', '/login']):
                name = elem.text().strip() or href.split('/')[-1].replace('-', ' ').title()
                categories[name] = urljoin(self.base_url, href)
                logger.info(f"Found category: {name}")
        
        self.stats["total_categories"] = len(categories)
        logger.info(f"Found {len(categories)} categories")
        return categories
    
    def get_agents_from_category(self, category_url: str) -> List[Agent]:
        """Get all agents from a category page"""
        logger.info(f"Processing category: {category_url}")
        self._init_selenium()
        self.driver.get(category_url)
        time.sleep(2)
        
        agents = []
        seen_urls = set()
        page = 1
        
        while True:
            # Log page source for debugging
            page_source = self.driver.page_source
            logger.debug(f"Page source length: {len(page_source)}")
            logger.debug(f"First 500 chars of page source: {page_source[:500]}")
            
            doc = pq(page_source)
            # Try different selectors
            all_links = list(doc('a').items())
            logger.debug(f"Total links found: {len(all_links)}")
            logger.debug(f"Sample of links: {[a.attr('href') for a in all_links[:5]]}")
            
            # Updated selector to match the actual structure
            blocks = list(doc('a[href*="/agent/"]').items())
            current_count = len(blocks)
            
            logger.info(f"Page {page}: Found {current_count} agent blocks")
            if current_count == 0:
                logger.debug("No agent blocks found, trying alternative selectors...")
                blocks = list(doc('a[href*="/tools/"]').items())
                logger.debug(f"Alternative selector found {len(blocks)} blocks")
            
            # Process new blocks
            new_agents = 0
            for block in blocks:
                try:
                    name = block.text().strip()
                    url = urljoin(self.base_url, block.attr('href'))
                    logger.debug(f"Processing block - Name: {name}, URL: {url}")
                    if name and url and url not in seen_urls:
                        agents.append(Agent(name=name, url=url, source_url=category_url))
                        seen_urls.add(url)
                        new_agents += 1
                except Exception as e:
                    logger.error(f"Error processing agent block: {e}")
            
            logger.info(f"Added {new_agents} new agents from page {page}")
            
            # Try to load more
            try:
                load_more = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Load More')]"))
                )
                if not load_more.is_displayed() or not load_more.is_enabled():
                    logger.info("Load More button not available")
                    break
                    
                load_more.click()
                time.sleep(2)
                page += 1
                
                if len(seen_urls) == current_count:
                    logger.info("No new agents found after loading more")
                    break
                
            except TimeoutException:
                logger.info("No Load More button found")
                break
        
        logger.info(f"Total agents found in category: {len(agents)}")
        self.stats["total_agents"] += len(agents)
        return agents
    
    def get_agent_details(self, url: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an agent"""
        logger.info(f"Getting details for agent: {url}")
        self._init_selenium()
        self.driver.get(url)
        time.sleep(2)
        
        try:
            # Try to click "more" button if present
            try:
                more = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'More')]"))
                )
                if more.is_displayed() and more.is_enabled():
                    more.click()
                    time.sleep(1)
                    logger.debug("Clicked 'More' button")
            except TimeoutException:
                logger.debug("No 'More' button found")
            
            doc = pq(self.driver.page_source)
            details = {}
            
            # Extract basic info
            name = doc('h1, h2, [class*="title"]').eq(0).text().strip()
            if not name:
                logger.warning(f"No name found for agent: {url}")
                self.stats["failed_details"] += 1
                return None
            
            details['name'] = name
            details['description'] = doc('p, [class*="description"]').text().strip()
            
            # Extract image
            img = doc('img[src]:not([class*="icon"])').eq(0)
            if img:
                details['image_url'] = urljoin(url, img.attr('src'))
            
            # Extract tags
            details['tags'] = [
                tag.text().strip() for tag in doc('[class*="tag"], [class*="category"]').items()
                if 2 <= len(tag.text().strip()) <= 30
            ]
            
            logger.debug(f"Extracted details for agent: {name}")
            self.stats["agents_with_details"] += 1
            return details
            
        except Exception as e:
            logger.error(f"Error getting agent details from {url}: {e}")
            self.stats["failed_details"] += 1
            return None
    
    def scrape_agents(self) -> List[Agent]:
        """Scrape all agents from the directory"""
        logger.info("Starting agent scraping process...")
        start_time = time.time()
        
        agents = []
        categories = self.get_categories()
        
        for name, url in categories.items():
            logger.info(f"Processing category '{name}' ({url})")
            category_agents = self.get_agents_from_category(url)
            
            for agent in category_agents:
                if details := self.get_agent_details(agent.url):
                    agent.description = details.get('description')
                    agent.image_url = details.get('image_url')
                    agent.tags = details.get('tags', [])
            
            agents.extend(category_agents)
            logger.info(f"Completed category '{name}'. Current stats: {self.stats}")
        
        duration = time.time() - start_time
        logger.info(f"""
Scraping completed in {duration:.2f} seconds
Final Statistics:
- Total Categories: {self.stats['total_categories']}
- Total Agents Found: {self.stats['total_agents']}
- Agents with Details: {self.stats['agents_with_details']}
- Failed Detail Extractions: {self.stats['failed_details']}
""")
        
        return agents
    
    def save_agents(self, agents: List[Agent], output_file: str = 'ai_agents_data.json'):
        """Save agents to JSON file"""
        logger.info(f"Saving {len(agents)} agents to {output_file}")
        with open(output_file, 'w') as f:
            json.dump([agent.to_dict() for agent in agents], f, indent=2)
        logger.info("Save completed")

if __name__ == '__main__':
    scraper = AIDirectoryScraper()
    agents = scraper.scrape_agents()
    scraper.save_agents(agents)