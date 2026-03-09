from abc import ABC, abstractmethod

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


class BaseScraper(ABC):
    site: str       # short identifier, e.g. "ecuagenera"
    timeout: int = 120  # per-scraper timeout in seconds; override in subclass if needed

    def get(self, url: str, **kwargs) -> requests.Response:
        resp = requests.get(url, headers=HEADERS, timeout=15, **kwargs)
        resp.raise_for_status()
        return resp

    @abstractmethod
    def scrape(self) -> list[dict]:
        """Return a list of product dicts for this site."""
        ...
