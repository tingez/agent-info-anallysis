"""
Service layer for AI Agent Directory scraping
"""
import logging
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from pyquery import PyQuery as pq
import asyncio
import json

from ..models.agent import Agent, AgentInfo, AgentEncoder
from .crawl4ai import _crawl4ai_crawl_async, get_agent_info

logger = logging.getLogger(__name__)

class AIDirectoryScraper:
    """Service for scraping AI Agents Directory website"""
    
    def __init__(self, base_url: str = "https://aiagentsdirectory.com", headless: bool = True):
        """Initialize scraper with configuration"""
        self.base_url = base_url
        self.driver = self._setup_driver(headless)
        self.wait = WebDriverWait(self.driver, 15)
        self.stats = {"total_agents": 0}
        
    def _setup_driver(self, headless: bool) -> webdriver.Chrome:
        """Set up Chrome WebDriver with optimal settings"""
        options = Options()
        if headless:
            options.add_argument("--headless")
        
        # Common options for stability
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-extensions")
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        return webdriver.Chrome(options=options)
    
    def _safe_request(self, url: str, retries: int = 3) -> Optional[str]:
        """Make a safe request with retries and proper error handling"""
        for attempt in range(retries):
            try:
                logger.info(f"Requesting URL: {url} (Attempt {attempt + 1}/{retries})")
                self.driver.get(url)
                
                # Wait for page load
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                self.wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                
                # Wait for dynamic content
                time.sleep(1)
                
                if len(self.driver.page_source) < 1000:
                    raise WebDriverException("Page content too short, likely failed to load")
                
                return self.driver.page_source
                
            except Exception as e:
                logger.error(f"Request failed: {str(e)}")
                if attempt == retries - 1:
                    logger.error(f"All attempts failed for URL: {url}")
                    return None
                time.sleep(min(2 ** attempt, 3))
        
        return None

    def get_agents_from_category(self, category_url: str) -> List[Agent]:
        """Extract all agents from a category page"""
        logger.info(f"Processing category: {category_url}")
        
        if not (page_source := self._safe_request(category_url)):
            logger.error(f"Failed to fetch category page: {category_url}")
            return []

        # Handle pagination
        while True:
            try:
                load_more = self.driver.find_element("xpath", "//button[contains(text(), 'Load More')]")
                if not load_more or not load_more.is_displayed() or not load_more.is_enabled():
                    break
                
                load_more.click()
                time.sleep(1)
                logger.info("Successfully loaded more agents")
            except Exception as e:
                logger.debug(f"No more agents to load: {str(e)}")
                break
        
        agents = []
        seen_urls = set()
        doc = pq(self.driver.page_source)
        blocks = doc('a.block[href^="/agent"]').items()

        for block in blocks:
            try:
                href = block.attr('href')
                if not href or href in seen_urls:
                    continue
                
                name = block('h3').text().strip()
                description = block('p').text().strip()
                url = urljoin(self.base_url, href)
                
                if name and url:
                    agent = Agent(
                        name=name,
                        url=url,
                        description=description,
                        source_url=category_url
                    )
                    agents.append(agent)
                    seen_urls.add(href)
                    logger.debug(f"Found agent: {name} ({url})")
            
            except Exception as e:
                logger.error(f"Error processing agent block: {str(e)}")
        
        logger.info(f"Found {len(agents)} agents in category")
        self.stats["total_agents"] += len(agents)
        return agents
    
    def get_categories(self) -> Dict[str, str]:
        """Get all available AI agent categories"""
        logger.info("Fetching categories...")
        
        if not (page_source := self._safe_request(f"{self.base_url}/categories")):
            return {}
            
        doc = pq(page_source)
        categories = {}
        
        for link in doc('a[href^="/category/"]').items():
            href = link.attr('href')
            name = link('h2').text().strip()
            if href and name:
                categories[name] = urljoin(self.base_url, href)
                logger.debug(f"Found category: {name}")
        
        logger.info(f"Found {len(categories)} categories")
        return categories

    def get_agent_info(self, url: str) -> AgentInfo:
        """Get agent info from URL"""
        logger.info(f"Getting agent info from {url}")
        for attempt in range(4):
            try:
                content = asyncio.run(_crawl4ai_crawl_async(url))
                print(content)
                agent_info = get_agent_info(content)
                return agent_info
            except Exception as e:
                print(e)
                if attempt == 3:
                    logger.error(f"Failed to get agent info: {str(e)}")
                    raise 

    def get_agent_details(self, agent: Agent) -> Agent:
        """Get detailed information about an agent from its page"""
        logger.info(f"Getting details for agent: {agent.name}")
        try:
            details_md = asyncio.run(_crawl4ai_crawl_async(agent.url))
            agent_info = get_agent_info(details_md)
            agent.info = agent_info
            logger.info(f"Successfully got details for {agent.name}")
        except Exception as e:
            logger.error(f"Failed to get details for {agent.name}: {str(e)}")
        return agent

    def save_progress(self, agents: List[Agent], output_file: str = 'ai_agents_data.json'):
        """Save progress to a file"""
        try:
            filename = output_file
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(agents, f, indent=2, ensure_ascii=False, cls=AgentEncoder)
            logger.info(f"Progress saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save progress: {str(e)}")

    def close(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
