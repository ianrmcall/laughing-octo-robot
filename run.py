"""
Plant Database Scraper — Orchestrator

Usage:
  python run.py               # Scrape all sites and save to database
  python run.py --dry-run     # Scrape and print results only — no database writes
  python run.py --site NAME   # Scrape a single site, e.g. --site ecuagenera
"""

import argparse
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone

import db
from scrapers import SCRAPERS

# Hard deadline: exit cleanly before the GHA job timeout kills us mid-step.
# Set this a few minutes below the workflow's `timeout-minutes` so the
# "Commit updated database" step still has time to run with partial results.
SCRIPT_TIMEOUT_SECONDS = 25 * 60  # 25 minutes


def _start_watchdog(timeout: int) -> None:
    """Daemon thread: force-exit the process after *timeout* seconds."""
    def _run():
        time.sleep(timeout)
        print(
            f"\nWatchdog: script has been running for {timeout // 60} min; "
            "forcing a clean exit so partial results are committed.",
            flush=True,
        )
        os._exit(0)

    threading.Thread(target=_run, daemon=True, name="watchdog").start()


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
    _start_watchdog(SCRIPT_TIMEOUT_SECONDS)

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

    with ThreadPoolExecutor(max_workers=len(scrapers)) as pool:
        list(pool.map(lambda s: run_scraper(s, dry_run=args.dry_run), scrapers))

    print("\nDone.")


if __name__ == "__main__":
    main()
