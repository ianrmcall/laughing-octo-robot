import re

from bs4 import BeautifulSoup

from .base import BaseScraper

BASE = "https://www.kartuz.com"

CATEGORY_PAGES = [
    "/c/1GES/Gesneriads.html",
    "/c/2BEG/Begonias.html",
    "/c/7RFP/Rare+Flowering+Plants.html",
    "/c/8FLV/Vines+and+Climbers.html",
    "/c/8Y01/Other+Categories.html",
]


class KartuzScraper(BaseScraper):
    site = "kartuz"

    def scrape(self) -> list[dict]:
        products = []
        for i, path in enumerate(CATEGORY_PAGES, 1):
            url = BASE + path
            print(f"    [kartuz] category {i}/{len(CATEGORY_PAGES)}: {path}")
            try:
                soup = BeautifulSoup(self.get(url).text, "html.parser")
                products.extend(self._parse_category(soup, url))
            except Exception as e:
                print(f"    [kartuz] Error fetching {url}: {e}")
        return products

    def _parse_category(self, soup: BeautifulSoup, page_url: str) -> list[dict]:
        products = []
        text = soup.get_text(separator="\n")
        blocks = re.split(r"Quantity(?:\s+in\s+Basket)?:", text)

        for block in blocks:
            code_match = re.search(r"Code:\s*(\S+)", block)
            price_match = re.search(r"Price:\s*(\$[\d.]+)", block)
            if not code_match or not price_match:
                continue

            code = code_match.group(1)
            price = price_match.group(1)

            before_code = block[: code_match.start()].strip()
            lines = [l.strip() for l in before_code.split("\n") if l.strip()]
            name = lines[-1] if lines else "Unknown"
            name = re.sub(r"\s+", " ", name).strip()

            in_stock = "none" in block[: price_match.start()].lower()

            products.append({
                "id": f"{self.site}:{code}",
                "site": self.site,
                "name": name,
                "price": price,
                "image_url": "",
                "product_url": page_url,
                "in_stock": in_stock,
            })
        return products
