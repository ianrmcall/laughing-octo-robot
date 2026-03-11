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

        # Match full product pattern: Code, Price, then Quantity in Basket value.
        # Using a single regex ensures stock status is paired with the correct product.
        pattern = re.compile(
            r"Code:\s*(\S+).*?"
            r"Price:\s*(\$[\d.]+).*?"
            r"Quantity\s+in\s+Basket:\s*(\S+)",
            re.DOTALL,
        )

        for m in pattern.finditer(text):
            code = m.group(1)
            price = m.group(2)
            basket_val = m.group(3)

            # "none" in basket means item is available for purchase
            in_stock = basket_val.lower() == "none"

            # Name: last non-empty line before "Code:" in the full text
            before_code = text[: m.start()].strip()
            lines = [l.strip() for l in before_code.split("\n") if l.strip()]
            name = lines[-1] if lines else "Unknown"
            name = re.sub(r"\s+", " ", name).strip()

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
