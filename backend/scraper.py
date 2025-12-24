from firecrawl import FirecrawlApp
import os
from typing import Optional


class ContentScraper:
    def __init__(self):
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            print("⚠️  Warning: Firecrawl API key not found. Scraping operations will fail.")
            self.firecrawl = None
        else:
            self.firecrawl = FirecrawlApp(api_key=api_key)

    def scrape_url(self, url: str) -> Optional[str]:
        """
        Scrape the given URL and return clean Markdown content

        Args:
            url: The URL to scrape

        Returns:
            Clean Markdown content or None if scraping fails
        """
        print(f"🔍 Starting scrape for URL: {url}")
        if not self.firecrawl:
            print("❌ Firecrawl not configured - please set FIRECRAWL_API_KEY")
            return None

        try:
            # Scrape the URL with Firecrawl
            scrape_result = self.firecrawl.scrape(
                url=url,
                formats=['markdown'],  # Get content in Markdown format
                only_main_content=True,  # Focus on main content
            )

            print(f"🔍 Scrape result type: {type(scrape_result)}")

            # Try accessing markdown attribute directly (Firecrawl v2 returns Document objects)
            if hasattr(scrape_result, 'markdown') and scrape_result.markdown:
                return scrape_result.markdown

            # Fallback: try accessing as dictionary
            if scrape_result and isinstance(scrape_result, dict):
                if 'markdown' in scrape_result:
                    return scrape_result['markdown']
                if 'content' in scrape_result:
                    return scrape_result['content']

            print(f"❌ Unexpected scrape result structure: {scrape_result}")
            return None

        except Exception as e:
            print(f"Error scraping URL {url}: {str(e)}")
            return None


# Scraper instance will be created in main.py after environment variables are loaded
