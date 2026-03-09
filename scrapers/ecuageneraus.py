from .base import BaseScraper

DOMAIN = "https://ecuageneraus.com"


class EcuageneraUSScraper(BaseScraper):
    site = "ecuageneraus"

    def scrape(self) -> list[dict]:
        products = []
        page = 1
        while True:
            print(f"    [ecuageneraus] page {page}...")
            data = self.get(
                f"{DOMAIN}/products.json",
                params={"limit": 250, "page": page},
            ).json()
            batch = data.get("products", [])
            if not batch:
                break
            for p in batch:
                handle = p["handle"]
                variant = p["variants"][0] if p["variants"] else {}
                image_url = p["images"][0]["src"] if p.get("images") else ""
                in_stock = any(v.get("available") for v in p["variants"])
                price_cents = variant.get("price", "0")
                try:
                    price = f"${float(price_cents):.2f}"
                except (ValueError, TypeError):
                    price = str(price_cents)
                products.append({
                    "id": f"{self.site}:{handle}",
                    "site": self.site,
                    "name": p["title"],
                    "price": price,
                    "image_url": image_url,
                    "product_url": f"{DOMAIN}/products/{handle}",
                    "in_stock": in_stock,
                })
            page += 1
        return products
