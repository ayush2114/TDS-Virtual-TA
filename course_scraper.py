"""
This module crawls and downloads pages from a specific website,
converting them to markdown format with metadata.
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Set, Dict, Any, Optional
from urllib.parse import urljoin

from markdownify import markdownify as md
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext


class TDSPageScraper:
    """Web scraper for TDS pages."""
    
    def __init__(
        self,
        base_url: str = "https://tds.s-anand.net/#/2025-01/",
        base_origin: str = "https://tds.s-anand.net",
        output_dir: str = "tds_pages_md",
        metadata_file: str = "metadata.json"
    ):
        """Initialize the scraper with configuration."""
        self.base_url = base_url
        self.base_origin = base_origin
        self.output_dir = Path(output_dir)
        self.metadata_file = metadata_file
        
        self.visited: Set[str] = set()
        self.metadata: List[Dict[str, Any]] = []
        
        # Setup logging
        self._setup_logging()
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('scraper.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    @staticmethod
    def sanitize_filename(title: str) -> str:
        """
        Sanitize title to create a valid filename.
        
        Args:
            title: The title to sanitize
            
        Returns:
            Sanitized filename string
        """
        return re.sub(r'[\\/*?:"<>|]', "_", title).strip().replace(" ", "_")
    
    def extract_all_internal_links(self, page: Page) -> List[str]:
        """
        Extract all internal links from the current page.
        
        Args:
            page: The Playwright page object
            
        Returns:
            List of unique internal links
        """
        try:
            links = page.eval_on_selector_all(
                "a[href]", 
                "els => els.map(el => el.href)"
            )
            return list(set(
                link for link in links
                if self.base_origin in link and '/#/' in link
            ))
        except Exception as e:
            self.logger.error(f"Error extracting links: {e}")
            return []
    
    def wait_for_article_and_get_html(self, page: Page) -> Optional[str]:
        """
        Wait for the article to load and extract its HTML content.
        
        Args:
            page: The Playwright page object
            
        Returns:
            HTML content of the article or None if failed
        """
        try:
            page.wait_for_selector(
                "article.markdown-section#main", 
                timeout=10000
            )
            return page.inner_html("article.markdown-section#main")
        except Exception as e:
            self.logger.error(f"Error waiting for article content: {e}")
            return None
    
    def save_page_content(
        self, 
        html: str, 
        title: str, 
        url: str
    ) -> Optional[str]:
        """
        Save page content as markdown with metadata.
        
        Args:
            html: HTML content to convert
            title: Page title
            url: Original URL
            
        Returns:
            Filename if successful, None otherwise
        """
        try:
            filename = self.sanitize_filename(title)
            filepath = self.output_dir / f"{filename}.md"
            
            markdown = md(html)
            current_time = datetime.now().isoformat()
            
            # Write markdown file with frontmatter
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("---\n")
                f.write(f'title: "{title}"\n')
                f.write(f'original_url: "{url}"\n')
                f.write(f'downloaded_at: "{current_time}"\n')
                f.write("---\n\n")
                f.write(markdown)
            
            # Add to metadata
            self.metadata.append({
                "title": title,
                "filename": f"{filename}.md",
                "original_url": url,
                "downloaded_at": current_time
            })
            
            return f"{filename}.md"
            
        except Exception as e:
            self.logger.error(f"Error saving page content for {url}: {e}")
            return None
    
    def crawl_page(self, page: Page, url: str) -> None:
        """
        Crawl a single page and recursively crawl its internal links.
        
        Args:
            page: The Playwright page object
            url: URL to crawl
        """
        if url in self.visited:
            return
            
        self.visited.add(url)
        self.logger.info(f"📄 Visiting: {url}")
        
        try:
            # Navigate to page
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(1000)
            
            # Extract content
            html = self.wait_for_article_and_get_html(page)
            if html is None:
                self.logger.warning(f"No content found for {url}")
                return
            
            # Extract title
            page_title = page.title()
            title = (
                page_title.split(" - ")[0].strip() 
                if page_title else f"page_{len(self.visited)}"
            )
            
            # Save content
            saved_filename = self.save_page_content(html, title, url)
            if saved_filename:
                self.logger.info(f"✅ Saved: {saved_filename}")
            
            # Extract and crawl internal links
            links = self.extract_all_internal_links(page)
            for link in links:
                if link not in self.visited:
                    self.crawl_page(page, link)
                    
        except Exception as e:
            self.logger.error(f"❌ Error loading page: {url}\n{e}")
    
    def save_metadata(self) -> None:
        """Save metadata to JSON file."""
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Metadata saved to {self.metadata_file}")
        except Exception as e:
            self.logger.error(f"Error saving metadata: {e}")
    
    def run(self) -> None:
        """
        Run the scraping process.
        
        Main entry point that orchestrates the entire scraping workflow.
        """
        self.logger.info("Starting TDS page scraper...")
        
        try:
            with sync_playwright() as playwright:
                browser: Browser = playwright.chromium.launch(headless=True)
                context: BrowserContext = browser.new_context()
                page: Page = context.new_page()
                
                # Start crawling from base URL
                self.crawl_page(page, self.base_url)
                
                # Save metadata
                self.save_metadata()
                
                # Clean up
                browser.close()
                
                self.logger.info(
                    f"✅ Scraping completed. {len(self.metadata)} pages saved."
                )
                
        except Exception as e:
            self.logger.error(f"Fatal error during scraping: {e}")
            raise


def main() -> None:
    """Main function to run the scraper."""
    # Configuration constants
    BASE_URL = "https://tds.s-anand.net/#/2025-01/"
    BASE_ORIGIN = "https://tds.s-anand.net"
    OUTPUT_DIR = "tds_pages_md"
    METADATA_FILE = "metadata.json"
    
    # Create and run scraper
    scraper = TDSPageScraper(
        base_url=BASE_URL,
        base_origin=BASE_ORIGIN,
        output_dir=OUTPUT_DIR,
        metadata_file=METADATA_FILE
    )
    
    scraper.run()


if __name__ == "__main__":
    main()