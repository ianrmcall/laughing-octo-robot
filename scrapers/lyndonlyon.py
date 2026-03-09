import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import urllib3
from bs4 import BeautifulSoup

from .base import BaseScraper

# Lyndon Lyon's SSL certificate is expired/self-signed — suppress the warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://lyndonlyon.com/store"
TOP_LEVEL_PATHS = [1, 2, 3, 35]  # african_violets, gesneriads, other_plants, new_listings
_WORKERS = 5


class LyndonLyonScraper(BaseScraper):
    site = "lyndonlyon"

    def scrape(self) -> list[dict]:
        seen_ids: set[str] = set()
        results: list[dict] = []
        leaf_cpaths = self._discover_leaf_cpaths()
        print(f"    [lyndonlyon] {len(leaf_cpaths)} categories to scrape")

        def fetch_category(args):
            i, cpath = args
            print(f"    [lyndonlyon] category {i}/{len(leaf_cpaths)}: cPath={cpath}")
            cat_products = []
            page = 1
            while True:
                try:
                    url = f"{BASE}/index.php"
                    soup = BeautifulSoup(
                        self.get(url, params={"main_page": "index", "cPath": cpath, "page": page}, verify=False).text,
                        "html.parser",
                    )
                    page_products = self._parse_listing(soup)
                    if not page_products:
                        break
                    cat_products.extend(page_products)
                    page += 1
                except Exception as e:
                    print(f"    [lyndonlyon] Error scraping cPath={cpath} page={page}: {e}")
                    break
            return cat_products

        with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
            futures = {pool.submit(fetch_category, (i, cp)): cp for i, cp in enumerate(leaf_cpaths, 1)}
            for future in as_completed(futures):
                cpath = futures[future]
                try:
                    for p in future.result():
                        if p["id"] not in seen_ids:
                            seen_ids.add(p["id"])
                            results.append(p)
                except Exception as e:
                    print(f"    [lyndonlyon] Error in category cPath={cpath}: {e}")

        return results

    def _discover_leaf_cpaths(self) -> list:
        leaf_paths = []
        for cpath in TOP_LEVEL_PATHS:
            try:
                url = f"{BASE}/index.php"
                resp = self.get(url, params={"main_page": "index", "cPath": cpath, "page": 1}, verify=False)
                soup = BeautifulSoup(resp.text, "html.parser")
                sub_pattern = re.compile(rf"[?&]cPath={cpath}_(\d+)(?:&|$)")
                seen = set()
                sub_paths = []
                for a in soup.find_all("a", href=True):
                    m = sub_pattern.search(a["href"])
                    if m:
                        sub_cpath = f"{cpath}_{m.group(1)}"
                        if sub_cpath not in seen:
                            seen.add(sub_cpath)
                            sub_paths.append(sub_cpath)
                if sub_paths:
                    leaf_paths.extend(sub_paths)
                else:
                    leaf_paths.append(cpath)
            except Exception as e:
                print(f"    [lyndonlyon] Error discovering cPath={cpath}: {e}")
        return leaf_paths

    def _parse_listing(self, soup: BeautifulSoup) -> list[dict]:
        products = []
        for row in soup.find_all("tr", class_=re.compile(r"productListing-(odd|even)")):
            title_tag = row.select_one("h3.itemTitle a")
            if not title_tag:
                continue
            href = title_tag.get("href", "")
            pid_match = re.search(r"products_id=(\d+)", href)
            if not pid_match:
                continue
            pid = pid_match.group(1)
            name = title_tag.get_text(strip=True)

            price = ""
            for label in row.select("label.attribsRadioButton"):
                m = re.search(r"\$[\d,]+\.?\d*", label.get_text())
                if m:
                    price = m.group(0)
                    break
            if not price:
                price_tag = row.select_one("span.productPrices")
                if price_tag:
                    m = re.search(r"\$[\d,]+\.?\d*", price_tag.get_text())
                    price = m.group(0) if m else ""

            image_url = ""
            img = row.select_one("img.listingProductImage")
            if img and img.get("src"):
                src = img["src"]
                image_url = src if src.startswith("http") else f"{BASE}/{src.lstrip('/')}"

            in_stock = bool(row.select_one("span.button_buy_now"))

            products.append({
                "id": f"{self.site}:{pid}",
                "site": self.site,
                "name": name,
                "price": price,
                "image_url": image_url,
                "product_url": href,
                "in_stock": in_stock,
            })
        return products
