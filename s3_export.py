"""
Export plant data from SQLite to S3.

Uploads two things after each scrape run:
  raw/{site}/{YYYY-MM-DD}.json   — per-source archival snapshots
  processed/latest.json          — aggregated summary for consumers

Usage:
  python s3_export.py                # upload to S3
  python s3_export.py --dry-run      # print what would be uploaded, skip S3
"""

import argparse
import json
import os
from datetime import datetime, timezone

import boto3
from sqlalchemy.orm import Session

import db

BUCKET = "ian-first-plant-scraping-database"


def _products_by_site() -> dict[str, list[dict]]:
    """Read all products from the database, grouped by site."""
    by_site: dict[str, list[dict]] = {}
    with Session(db.engine) as session:
        for p in session.query(db.Product).all():
            entry = {
                "id": p.external_id,
                "site": p.site,
                "name": p.name,
                "price": p.price,
                "image_url": p.image_url or "",
                "product_url": p.product_url or "",
                "in_stock": p.in_stock,
                "first_seen": p.first_seen.isoformat() if p.first_seen else None,
                "last_seen": p.last_seen.isoformat() if p.last_seen else None,
            }
            by_site.setdefault(p.site, []).append(entry)
    return by_site


def export(dry_run: bool = False) -> None:
    by_site = _products_by_site()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    total = sum(len(v) for v in by_site.values())

    if not by_site:
        print("No products in database — nothing to export.")
        return

    print(f"Exporting {total} products across {len(by_site)} sites...")

    s3 = None
    if not dry_run:
        s3 = boto3.client("s3")

    # raw/{site}/{date}.json — per-source daily snapshots
    for site, products in by_site.items():
        key = f"raw/{site}/{today}.json"
        body = json.dumps(products, indent=2)
        print(f"  {key} ({len(products)} products)")
        if s3:
            s3.put_object(Bucket=BUCKET, Key=key, Body=body, ContentType="application/json")

    # processed/latest.json — aggregated summary for consumers
    all_products = []
    for products in by_site.values():
        all_products.extend(products)

    latest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "total_products": len(all_products),
        "sites": list(by_site.keys()),
        "products": all_products,
    }
    key = "processed/latest.json"
    body = json.dumps(latest, indent=2)
    print(f"  {key} ({len(all_products)} products)")
    if s3:
        s3.put_object(Bucket=BUCKET, Key=key, Body=body, ContentType="application/json")

    print("Done." if not dry_run else "Done (dry run — nothing uploaded).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export plant data to S3")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be uploaded without uploading")
    args = parser.parse_args()
    export(dry_run=args.dry_run)
