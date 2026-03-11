import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup

from .base import BaseScraper

BASE = "https://andysorchids.com"
_WORKERS = 5


class AndysOrchidsScraper(BaseScraper):
    site = "andysorchids"
    timeout = 300  # parallelised, so much faster now

    def scrape(self) -> list[dict]:
        genera = self._get_genera()
        print(f"    [andysorchids] {len(genera)} genera to scrape")
        results: list[dict] = []
        seen_ids: set[str] = set()

        def fetch(args):
            i, genus = args
            print(f"    [andysorchids] genus {i}/{len(genera)}: {genus}")
            return self._scrape_genus(genus)

        with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
            futures = {pool.submit(fetch, (i, g)): g for i, g in enumerate(genera, 1)}
            for future in as_completed(futures):
                genus = futures[future]
                try:
                    for p in future.result():
                        if p["id"] not in seen_ids:
                            seen_ids.add(p["id"])
                            results.append(p)
                except Exception as e:
                    print(f"    [andysorchids] Error scraping genus '{genus}': {e}")

        return results

    def _get_genera(self) -> list[str]:
        soup = BeautifulSoup(self.get(f"{BASE}/genlist.asp").text, "html.parser")
        genera, seen = [], set()
        for a in soup.find_all("a", href=re.compile(r"searchresults\.asp\?genus=")):
            m = re.search(r"genus=([^&]+)", a.get("href", ""))
            if m:
                genus = m.group(1).strip()
                if genus not in seen:
                    seen.add(genus)
                    genera.append(genus)
        return genera

    def _scrape_genus(self, genus: str) -> list[dict]:
        url = f"{BASE}/searchresults.asp"
        soup = BeautifulSoup(
            self.get(url, params={"genus": genus, "s": "g"}).text,
            "html.parser",
        )
        products = []
        for card in soup.find_all("div", class_="iTemList"):
            link = card.find("a", href=re.compile(r"pictureframe\.asp\?picid="))
            if not link:
                continue
            href = link["href"]
            picid_match = re.search(r"picid=(\w+)", href)
            if not picid_match:
                continue
            picid = picid_match.group(1)

            name = card.get("data-gen") or ""
            name_tag = card.select_one("h2.pro-heading a")
            if name_tag:
                name = name_tag.get_text(strip=True)

            price = ""
            price_tag = card.select_one("span.price")
            if price_tag:
                price = price_tag.get_text(strip=True)
            elif card.get("data-price"):
                try:
                    price = f"${float(card['data-price']):.2f}"
                except ValueError:
                    price = card["data-price"]

            image_url = ""
            img = card.select_one("img.fst-image")
            if img and img.get("src"):
                src = img["src"].replace("\\", "/")
                image_url = f"{BASE}/{src.lstrip('/')}"

            products.append({
                "id": f"{self.site}:{picid}",
                "site": self.site,
                "name": name,
                "price": price,
                "image_url": image_url,
                "product_url": f"{BASE}/{href}",
                "in_stock": True,
            })
        return products


if __name__ == "__main__":
    import json
    import sys

    scraper = AndysOrchidsScraper()
    print(f"Running {scraper.site} scraper...")

    try:
        products = scraper.scrape()
        print(f"Found {len(products)} products.\n")

        if "--json" in sys.argv:
            print(json.dumps(products, indent=2))
        else:
            for p in products:
                stock = "IN STOCK" if p["in_stock"] else "out of stock"
                print(f"  [{stock}] {p['name']} — {p['price']}")
                print(f"    {p['product_url']}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
