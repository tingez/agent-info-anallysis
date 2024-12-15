# AI Agent Directory Scraper

## Description
This project is a command-line interface (CLI) tool for scraping data from the AI Agent Directory. It allows users to collect information about various AI agents, transform the data into Excel format, and generate visualizations such as word clouds based on user cases.

## Installation
To install the necessary dependencies, ensure you have Python 3.6 or higher installed, and then run:

```bash
pip install -r requirements.txt
```

### Usage
After installing the dependencies, you can use the following commands:

- scrape: Scrapes data from the AI Agent Directory and saves it to a JSON file.
- transform_to_excel <category>: Transforms the scraped JSON data into an Excel file filtered by the specified category.
- generate_wordcloud: Generates a Minecraft-style word cloud from the user cases in the AI agents data.

### Commands
- scrape: Scrapes the AI Agent Directory and saves the data to ai_agents_data.json.
- transform_to_excel: Transforms the JSON data into an Excel file.
- generate_wordcloud: Generates a Minecraft-style word cloud based on user cases from the data.