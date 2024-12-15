"""
Crawl4AI service for fetching and processing agent details
"""
import asyncio
from typing import Optional
from promptic import llm
from ..models.agent import AgentInfo
from crawl4ai import AsyncWebCrawler

@llm(model='ollama/llama3.1:8b-instruct-fp16', api_base='http://192.168.8.119:11434', temperature=0, top_p=0, top_k=0, debug=True)
def get_agent_info(content: str) -> AgentInfo:
    """Get Agent Information from markdown {content}"""

async def _crawl4ai_crawl_async(url: str, css_selector: Optional[str] = 'div.max-w-4xl.mx-auto.px-1.py-8.sm\\:px-6.lg\\:px-8'):
    """Crawl a URL using crawl4ai with optional CSS selector"""
    async with AsyncWebCrawler() as crawler:
        if css_selector:
            result = await crawler.arun(
                url=url,
                css_selector=css_selector
            )
        else:
            result = await crawler.arun(url=url)
        #print(result.markdown)
        return result.markdown

def crawl4ai_crawl(url: str) -> str:
    """Synchronous wrapper for crawl4ai crawling"""
    return asyncio.run(_crawl4ai_crawl_async(url))
