"""
CLI test tools for AI Agent Directory scraper
"""
import typer
import json
from src.services.scraper import AIDirectoryScraper
from src.models.agent import Agent, AgentEncoder

app = typer.Typer()

@app.command()
def test_categories():
    """Test getting categories from the directory"""
    print("Testing get_categories...")
    scraper = AIDirectoryScraper(headless=True)
    try:
        categories = scraper.get_categories()
        assert isinstance(categories, dict), "Categories should be a dictionary"
        assert len(categories) > 0, "Should find at least one category"
        print(f"Found {len(categories)} categories:")
        for name, url in categories.items():
            print(f"- {name}: {url}")
        print("\nTest passed!")
    except Exception as e:
        print(f"Test failed: {str(e)}")
    finally:
        scraper.close()

@app.command()
def test_agent_info(url: str = "https://aiagentsdirectory.com/agent/beam-ai"):
    """Test getting details for a single agent"""
    print(f"Testing agent: {url}")
    scraper = AIDirectoryScraper(headless=True)
    try:
        # Get agent info directly from URL
        agent_info = scraper.get_agent_info(url)
        
        # Convert to JSON for pretty printing
        agent_json = json.dumps(agent_info, cls=AgentEncoder, indent=2)
        print("\nAgent info:")
        print(agent_json)
        print("\nTest passed!")
    except Exception as e:
        print(f"Test failed: {str(e)}")
    finally:
        scraper.close()

@app.command()
def test_agent_category(url: str = "https://aiagentsdirectory.com/category/model-serving"):
    """Test getting agents from a category"""
    print(f"Testing category: {url}")
    scraper = AIDirectoryScraper(headless=True)
    try:
        agents = scraper.get_agents_from_category(url)
        assert isinstance(agents, list), "Agents should be a list"
        assert len(agents) > 0, "Should find at least one agent"
        print(f"Found {len(agents)} agents:")
        agent_infos = []
        for agent in agents:
            agent_info = scraper.get_agent_info(agent.url)
            agent.info = agent_info
            agent_infos.append(agent)
        print(json.dumps(agent_infos, cls=AgentEncoder, indent=2))
        print("\nTest passed!")
        with open('./test.json', 'w') as fd:
            json.dump(agent_infos, fd, cls=AgentEncoder, indent=2)
    except Exception as e:
        print(f"Test failed: {str(e)}")
    finally:
        scraper.close()


if __name__ == "__main__":
    app()
