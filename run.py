"""
Plant Database Scraper — Orchestrator

Usage:
  python run.py               # Scrape all sites and save to database
  python run.py --dry-run     # Scrape and print results only — no database writes
  python run.py --site NAME   # Scrape a single site, e.g. --site ecuagenera
"""

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone

import db
from scrapers import SCRAPERS


def run_scraper(scraper, dry_run: bool) -> None:
    site = scraper.site
    started_at = datetime.now(timezone.utc)
    error = None
    products = []

    print(f"  Scraping {site}...")
    try:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(scraper.scrape)
        try:
            products = future.result(timeout=scraper.timeout)
        except FuturesTimeoutError:
            error = f"Timed out after {scraper.timeout}s"
            print(f"    ✗ {error}")
        finally:
            executor.shutdown(wait=False)
    except Exception as e:
        error = str(e)
        print(f"    ✗ Error: {e}")

    finished_at = datetime.now(timezone.utc)
    counts = {"new": 0, "updated": 0, "total": len(products)}

    if products:
        print(f"    → {len(products)} products found")
        if not dry_run:
            counts = db.upsert_products(products)
            print(f"    → {counts['new']} new, {counts['updated']} updated in database")

    if not dry_run:
        db.record_scrape_run(
            site=site,
            started_at=started_at,
            finished_at=finished_at,
            products_found=len(products),
            new_products=counts["new"],
            error=error,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Plant database scraper")
    parser.add_argument("--dry-run", action="store_true", help="Scrape but don't write to database")
    parser.add_argument("--site", help="Only scrape this site (e.g. ecuagenera)")
    args = parser.parse_args()

    if not args.dry_run:
        db.init_db()

    scrapers = SCRAPERS
    if args.site:
        scrapers = [s for s in SCRAPERS if s.site == args.site]
        if not scrapers:
            known = [s.site for s in SCRAPERS]
            print(f"Unknown site {args.site!r}. Available: {', '.join(known)}")
            sys.exit(1)

    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"{prefix}Starting plant database scraper...\n")

    for scraper in scrapers:
        run_scraper(scraper, dry_run=args.dry_run)

    print("\nDone.")


if __name__ == "__main__":
    main()
