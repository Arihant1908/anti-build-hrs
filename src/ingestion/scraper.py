"""
Phase 1 — Data Loading
Scrapes raw text content from the 5 scoped Groww URLs.
Outputs: ScrapedDocument objects saved as JSON to data/raw/

Architecture reference: docs/architecture.md § Phase 1
PRD reference: docs/PRD.md § 3, § 4
"""

import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scraper")

# ---------------------------------------------------------------------------
# Constants — URL Registry (hard-coded, PRD §3 — no exceptions)
# ---------------------------------------------------------------------------
FUND_REGISTRY = [
    {
        "url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        "fund_name": "HDFC Large Cap Fund Direct Growth",
        "fund_category": "Large Cap",
    },
    {
        "url": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
        "fund_name": "HDFC Flexi Cap Fund Direct Growth",
        "fund_category": "Flexi Cap",
    },
    {
        "url": "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
        "fund_name": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
        "fund_category": "ELSS",
    },
    {
        "url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
        "fund_name": "HDFC Small Cap Fund Direct Growth",
        "fund_category": "Small Cap",
    },
    {
        "url": "https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth",
        "fund_name": "HDFC Balanced Advantage Fund Direct Growth",
        "fund_category": "Hybrid",
    },
]

# IST timezone for timestamps
IST = timezone(timedelta(hours=5, minutes=30))

# Retry configuration (architecture: retry 3× with exponential backoff)
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 2

# Output directory
RAW_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"


# ---------------------------------------------------------------------------
# Data Model (from architecture.md)
# ---------------------------------------------------------------------------
@dataclass
class ScrapedDocument:
    """Represents a scraped and cleaned Groww mutual fund page."""

    url: str                  # Source Groww URL
    fund_name: str            # e.g., "HDFC Large Cap Fund Direct Growth"
    fund_category: str        # e.g., "Large Cap"
    raw_text: str             # Cleaned plain text from the page
    scrape_timestamp: str     # ISO-8601 timestamp


# ---------------------------------------------------------------------------
# HTML Cleaning
# ---------------------------------------------------------------------------
# Tags to remove entirely (architecture: strip nav bars, footers, ads, script/style)
TAGS_TO_REMOVE = [
    "script", "style", "noscript", "svg", "img", "link", "meta",
    "header", "footer", "nav", "iframe",
]

# CSS classes that indicate non-fund-content (Groww-specific navigation/chrome)
CLASSES_TO_REMOVE = [
    "header2025_headerContainer",
    "loggedOut_navContainer",
    "dropdownUI_dropdownContainer",
    "footer",
    "loginWrapper",
    "searchBar",
]


def _clean_html(soup: BeautifulSoup) -> BeautifulSoup:
    """Remove non-content elements from the parsed HTML."""
    # Remove unwanted tags entirely
    for tag_name in TAGS_TO_REMOVE:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove elements with known non-content CSS classes
    for class_prefix in CLASSES_TO_REMOVE:
        for el in soup.find_all(class_=lambda c: c and any(
            cls.startswith(class_prefix) for cls in (c if isinstance(c, list) else [c])
        )):
            el.decompose()

    return soup


def _extract_text(soup: BeautifulSoup) -> str:
    """
    Extract clean, readable text from the fund page.

    Strategy:
    1. Target the main content container (#__next > div#root)
    2. Clean out navigation/chrome elements
    3. Extract text with proper spacing
    4. Collapse excessive whitespace
    """
    # Try to find the main content area
    main_content = soup.find("div", id="root")
    if main_content is None:
        main_content = soup.find("div", id="__next")
    if main_content is None:
        main_content = soup  # Fallback to full page

    # Clean the content
    main_content = _clean_html(main_content)

    # Extract text with newline separators between block elements
    text = main_content.get_text(separator="\n", strip=True)

    # Clean up whitespace: collapse multiple newlines to max 2
    lines = []
    prev_empty = False
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            if not prev_empty:
                lines.append("")
                prev_empty = True
            continue
        prev_empty = False
        lines.append(stripped)

    text = "\n".join(lines).strip()

    return text


# ---------------------------------------------------------------------------
# HTTP Fetching with Retry
# ---------------------------------------------------------------------------
def _fetch_page(url: str) -> str:
    """
    Fetch a Groww page with retry logic.

    Retries 3× with exponential backoff as specified in architecture.
    Uses a browser-like User-Agent to get full server-rendered HTML.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    last_exception = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Fetching {url} (attempt {attempt}/{MAX_RETRIES})")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            logger.info(f"  ✓ Success — {len(response.text):,} chars received")
            return response.text

        except requests.RequestException as e:
            last_exception = e
            if attempt < MAX_RETRIES:
                wait = INITIAL_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    f"  ✗ Attempt {attempt} failed: {e}. "
                    f"Retrying in {wait}s..."
                )
                time.sleep(wait)
            else:
                logger.error(
                    f"  ✗ All {MAX_RETRIES} attempts failed for {url}: {e}"
                )

    raise last_exception


# ---------------------------------------------------------------------------
# Scraping Pipeline
# ---------------------------------------------------------------------------
def scrape_fund_page(fund_info: dict) -> ScrapedDocument:
    """
    Scrape a single Groww mutual fund page and return a ScrapedDocument.

    Args:
        fund_info: Dict with keys 'url', 'fund_name', 'fund_category'

    Returns:
        ScrapedDocument with cleaned text and metadata
    """
    url = fund_info["url"]
    fund_name = fund_info["fund_name"]
    fund_category = fund_info["fund_category"]

    logger.info(f"Scraping: {fund_name} ({fund_category})")

    # Fetch HTML
    html = _fetch_page(url)

    # Parse with BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Extract clean text
    raw_text = _extract_text(soup)

    if not raw_text or len(raw_text) < 100:
        logger.warning(
            f"  ⚠ Very little text extracted ({len(raw_text)} chars). "
            f"Page may require JS rendering (Playwright fallback)."
        )

    # Build the ScrapedDocument
    doc = ScrapedDocument(
        url=url,
        fund_name=fund_name,
        fund_category=fund_category,
        raw_text=raw_text,
        scrape_timestamp=datetime.now(IST).isoformat(),
    )

    logger.info(
        f"  ✓ Extracted {len(raw_text):,} chars from {fund_name}"
    )

    return doc


def scrape_all_funds() -> list[ScrapedDocument]:
    """
    Scrape all 5 fund pages defined in the FUND_REGISTRY.

    Returns:
        List of ScrapedDocument objects (may be fewer than 5 if some fail)
    """
    documents = []
    failed = []

    for fund_info in FUND_REGISTRY:
        try:
            doc = scrape_fund_page(fund_info)
            documents.append(doc)
        except Exception as e:
            logger.error(
                f"  ✗ Failed to scrape {fund_info['fund_name']}: {e}"
            )
            failed.append(fund_info["fund_name"])

    logger.info(
        f"\n{'='*60}\n"
        f"Scraping complete: {len(documents)}/{len(FUND_REGISTRY)} pages scraped\n"
        f"{'='*60}"
    )
    if failed:
        logger.warning(f"Failed: {', '.join(failed)}")

    return documents


# ---------------------------------------------------------------------------
# Persistence — Save to data/raw/
# ---------------------------------------------------------------------------
def save_documents(documents: list[ScrapedDocument], output_dir: Path = None) -> list[Path]:
    """
    Save scraped documents as JSON files to data/raw/.

    Each file is named: {fund_category_slug}.json
    Also saves a manifest.json listing all scraped files.

    Returns:
        List of saved file paths
    """
    if output_dir is None:
        output_dir = RAW_DATA_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []

    for doc in documents:
        # Create a filesystem-safe slug from the category
        slug = doc.fund_category.lower().replace(" ", "_")
        filename = f"{slug}.json"
        filepath = output_dir / filename

        # Save as JSON
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(doc), f, indent=2, ensure_ascii=False)

        saved_files.append(filepath)
        logger.info(f"  💾 Saved: {filepath}")

    # Save a manifest with summary info
    manifest = {
        "scrape_run_timestamp": datetime.now(IST).isoformat(),
        "total_documents": len(documents),
        "documents": [
            {
                "fund_name": doc.fund_name,
                "fund_category": doc.fund_category,
                "url": doc.url,
                "text_length": len(doc.raw_text),
                "file": f"{doc.fund_category.lower().replace(' ', '_')}.json",
            }
            for doc in documents
        ],
    }

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    logger.info(f"  📋 Manifest saved: {manifest_path}")

    return saved_files


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------
def run_data_loading() -> list[ScrapedDocument]:
    """
    Execute the full Phase 1 data loading pipeline:
    1. Scrape all 5 Groww fund pages
    2. Save raw documents as JSON to data/raw/
    3. Return the list of ScrapedDocument objects for Phase 2

    Returns:
        List of ScrapedDocument objects
    """
    logger.info(
        f"\n{'='*60}\n"
        f"PHASE 1 — DATA LOADING\n"
        f"Scraping {len(FUND_REGISTRY)} Groww fund pages\n"
        f"{'='*60}"
    )

    # Step 1: Scrape
    documents = scrape_all_funds()

    if not documents:
        logger.error("No documents scraped. Aborting.")
        return []

    # Step 2: Save to data/raw/
    saved_files = save_documents(documents)

    logger.info(
        f"\n{'='*60}\n"
        f"PHASE 1 COMPLETE\n"
        f"  Scraped: {len(documents)} documents\n"
        f"  Saved to: {RAW_DATA_DIR}\n"
        f"  Files: {len(saved_files)} JSON files + manifest\n"
        f"{'='*60}\n"
    )

    return documents


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    docs = run_data_loading()

    # Print summary
    print(f"\n{'-'*60}")
    print(f"Phase 1 Summary: Scraped {len(docs)} fund pages")
    print(f"{'-'*60}")
    for doc in docs:
        print(f"  [{doc.fund_category}] {doc.fund_name}")
        print(f"    URL: {doc.url}")
        print(f"    Text: {len(doc.raw_text):,} characters")
        print(f"    Time: {doc.scrape_timestamp}")
        print()
