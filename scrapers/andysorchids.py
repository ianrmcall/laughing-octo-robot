import re
import time

from bs4 import BeautifulSoup

from .base import BaseScraper

BASE = "https://andysorchids.com"


class AndysOrchidsScraper(BaseScraper):
    site = "andysorchids"
    timeout = 600  # many genera + sleep between requests

    def scrape(self) -> list[dict]:
        genera = self._get_genera()
        products = []
        seen_ids = set()
        for i, genus in enumerate(genera, 1):
            print(f"    [andysorchids] genus {i}/{len(genera)}: {genus}")
            try:
                for p in self._scrape_genus(genus):
                    if p["id"] not in seen_ids:
                        seen_ids.add(p["id"])
                        products.append(p)
            except Exception as e:
                print(f"    [andysorchids] Error scraping genus '{genus}': {e}")
            time.sleep(0.1)
        return products

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
