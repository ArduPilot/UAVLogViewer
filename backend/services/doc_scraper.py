"""
ArduPilot Documentation Scraper

Utility to fetch, clean, and convert ArduPilot documentation pages to Markdown.
Provides one-time HTML snapshot functionality with proper tag stripping and
markdown conversion.

Usage:
    python -m backend.services.doc_scraper
"""

import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup
from html_to_markdown import convert_to_markdown

logger = logging.getLogger(__name__)

# ArduPilot documentation URLs to scrape
URLS = {
    "log_messages": "https://ardupilot.org/plane/docs/logmessages.html",
    "diagnosing": "https://ardupilot.org/plane/docs/common-diagnosing-problems-using-logs.html",
    "download_analyze": "https://ardupilot.org/plane/docs/common-downloading-and-analyzing-data-logs-in-mission-planner.html",
}

EXTRA = [
    "https://ardupilot.org/plane/docs/common-measuring-vibration.html",
    "https://ardupilot.org/plane/docs/common-imu-batchsampling.html",
    "https://ardupilot.org/plane/docs/common-raw-imu-logging.html",
    "https://ardupilot.org/plane/docs/case-study-fly-by-wire.html",
    "https://ardupilot.org/plane/docs/case-study-turn-rate.html",
]

# Tags to strip from HTML before conversion
STRIP_TAGS = [
    "nav",
    "header",
    "footer",
    "script",
    "style",
    "aside",
    "noscript",
    "iframe",
    "form",
    "input",
    "button",
]

# CSS classes/IDs to remove (common navigation/sidebar elements)
STRIP_CLASSES = [".toc", ".sidebar", ".navigation", ".breadcrumb", ".footer"]
STRIP_IDS = ["#toc", "#sidebar", "#navigation", "#header", "#footer"]


class DocScraper:
    """ArduPilot documentation scraper and converter."""

    def __init__(self, output_dir: Path = None, delay: float = 1.0):
        """
        Initialize the doc scraper.

        Args:
            output_dir: Directory to save markdown files (default: data/docs/)
            delay: Delay between requests in seconds (be respectful)
        """
        self.output_dir = output_dir or Path("data/docs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay

        # Setup requests session with proper headers
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "UAVLogViewer-DocScraper/1.0 (Educational Use)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
        )

    def _get_slug_from_url(self, url: str) -> str:
        """Extract a clean filename slug from URL."""
        parsed = urlparse(url)
        # Get the filename part, remove .html extension
        filename = Path(parsed.path).stem
        # Clean up the filename
        slug = re.sub(r"[^a-zA-Z0-9-_]", "_", filename)
        # Remove common- prefix if present
        slug = re.sub(r"^common_", "", slug)
        return slug or "unknown"

    def _fetch_with_retry(self, url: str, max_retries: int = 3) -> Optional[str]:
        """
        Fetch URL content with retry logic.

        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts

        Returns:
            HTML content or None if failed
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching {url} (attempt {attempt + 1}/{max_retries})")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                # Check if we got HTML content
                content_type = response.headers.get("content-type", "").lower()
                if "html" not in content_type:
                    logger.warning(f"Non-HTML content type: {content_type}")
                    return None

                # Fix UTF-8 encoding issue - many servers don't specify charset correctly
                if response.encoding != response.apparent_encoding:
                    logger.debug(
                        f"Encoding mismatch: {response.encoding} vs {response.apparent_encoding}, using apparent"
                    )
                    response.encoding = response.apparent_encoding

                return response.text

            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(self.delay * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
                    return None

        return None

    def _clean_html(self, html: str, base_url: str) -> BeautifulSoup:
        """
        Clean HTML by removing unwanted elements.

        Args:
            html: Raw HTML content
            base_url: Base URL for resolving relative links

        Returns:
            Cleaned BeautifulSoup object
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted tags entirely
        for tag_name in STRIP_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Remove elements by class/id
        for selector in STRIP_CLASSES + STRIP_IDS:
            for element in soup.select(selector):
                element.decompose()

        # Convert relative URLs to absolute URLs
        base_domain = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith("/"):
                link["href"] = base_domain + href
            elif not href.startswith(("http://", "https://", "mailto:", "#")):
                link["href"] = urljoin(base_url, href)

        for img in soup.find_all("img", src=True):
            src = img["src"]
            if src.startswith("/"):
                img["src"] = base_domain + src
            elif not src.startswith(("http://", "https://")):
                img["src"] = urljoin(base_url, src)

        return soup

    def _extract_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """
        Extract main content from the page.

        Attempts to find the main content area and strip navigation/sidebar elements.

        Args:
            soup: Cleaned BeautifulSoup object

        Returns:
            BeautifulSoup object with main content only
        """
        # Try to find main content area
        content_selectors = [
            "main",
            ".content",
            ".main-content",
            "#content",
            "#main-content",
            "article",
            ".document",  # Common in Sphinx docs
            ".body",  # Common in Sphinx docs
        ]

        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                logger.debug(f"Found main content using selector: {selector}")
                break

        if main_content:
            # Create new soup with just the main content
            new_soup = BeautifulSoup("<div></div>", "html.parser")
            new_soup.div.replace_with(main_content)
            return new_soup
        else:
            # Fallback: use body content if available
            body = soup.find("body")
            if body:
                return BeautifulSoup(str(body), "html.parser")
            else:
                logger.warning(
                    "Could not identify main content area, using full document"
                )
                return soup

    def _convert_to_markdown(self, soup: BeautifulSoup, source_url: str) -> str:
        """
        Convert cleaned HTML to Markdown.

        Args:
            soup: Cleaned BeautifulSoup object
            source_url: Original source URL for reference

        Returns:
            Markdown content
        """
        # Convert to markdown with specific options
        markdown = convert_to_markdown(
            soup,
            heading_style="atx",  # Use # style headers
            strip=["script", "style"],  # Additional stripping
            convert_as_inline=False,
            wrap=True,
            wrap_width=100,
            escape_asterisks=True,
            autolinks=True,
        )

        # Clean up the markdown
        # Remove excessive blank lines (max 2 consecutive newlines)
        markdown = re.sub(r"\n{3,}", "\n\n", markdown)

        # Clean up markdown artifacts from HTML conversion
        # Remove anchor links like [¶](#section "Link to this heading")
        markdown = re.sub(r'\[¶\]\([^)]*"[^"]*"\)', "", markdown)

        # Clean up whitespace
        markdown = markdown.strip()

        # Add source URL as header comment
        header = f"# {soup.find('h1').get_text() if soup.find('h1') else 'ArduPilot Documentation'}\n\n"
        header += f"**Source:** [{source_url}]({source_url})\n\n"
        header += "---\n\n"

        return header + markdown

    def scrape_url(self, url: str, slug: Optional[str] = None) -> bool:
        """
        Scrape a single URL and save as markdown.

        Args:
            url: URL to scrape
            slug: Optional filename slug (auto-generated if not provided)

        Returns:
            True if successful, False otherwise
        """
        if not slug:
            slug = self._get_slug_from_url(url)

        output_file = self.output_dir / f"{slug}.md"

        # Skip if file already exists (one-time promise)
        if output_file.exists():
            logger.info(f"Skipping {url} - {output_file} already exists")
            return True

        # Fetch HTML content
        html = self._fetch_with_retry(url)
        if not html:
            return False

        try:
            # Clean and process HTML
            soup = self._clean_html(html, url)
            content_soup = self._extract_content(soup)

            # Convert to markdown
            markdown = self._convert_to_markdown(content_soup, url)

            # Save to file
            output_file.write_text(markdown, encoding="utf-8")
            logger.info(f"Saved {url} -> {output_file}")

            # Be respectful - add delay between requests
            if self.delay > 0:
                time.sleep(self.delay)

            return True

        except Exception as e:
            logger.error(f"Failed to process {url}: {e}")
            return False

    def scrape_all(self) -> Dict[str, bool]:
        """
        Scrape all configured URLs.

        Returns:
            Dictionary mapping URLs to success status
        """
        results = {}

        logger.info("Starting ArduPilot documentation scraping...")

        # Scrape named URLs
        for name, url in URLS.items():
            logger.info(f"Processing {name}: {url}")
            results[url] = self.scrape_url(url, name)

        # Scrape extra URLs
        for url in EXTRA:
            logger.info(f"Processing extra URL: {url}")
            results[url] = self.scrape_url(url)

        # Summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)

        logger.info(
            f"Scraping complete: {successful}/{total} URLs processed successfully"
        )

        if successful < total:
            failed_urls = [url for url, success in results.items() if not success]
            logger.warning(f"Failed URLs: {failed_urls}")

        return results


def run_scraper(output_dir: Path = None, delay: float = 1.0) -> Dict[str, bool]:
    """
    Programmatic entry point for scraping.

    Args:
        output_dir: Directory to save markdown files
        delay: Delay between requests in seconds

    Returns:
        Dictionary mapping URLs to success status
    """
    if output_dir is None:
        output_dir = Path("data/docs")

    scraper = DocScraper(output_dir=output_dir, delay=delay)
    return scraper.scrape_all()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrape ArduPilot documentation and convert to Markdown"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/docs"),
        help="Output directory for markdown files (default: data/docs)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create scraper and run
    results = run_scraper(output_dir=args.output_dir, delay=args.delay)

    # Exit with error code if any URLs failed
    failed_count = sum(1 for success in results.values() if not success)
    exit(failed_count)


if __name__ == "__main__":
    main()
