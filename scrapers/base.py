from abc import ABC, abstractmethod
import json
from pathlib import Path

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

_CONFIG_PATH = Path(__file__).parent.parent / "scraper_config.json"
_SCRAPER_CONFIG: dict = {}
if _CONFIG_PATH.exists():
    with open(_CONFIG_PATH) as _f:
        _SCRAPER_CONFIG = json.load(_f)


class BaseScraper(ABC):
    site: str       # short identifier, e.g. "ecuagenera"
    timeout: int = 120  # per-scraper timeout in seconds; override in subclass if needed

    @property
    def config(self) -> dict:
        """Return this scraper's config section from scraper_config.json."""
        return _SCRAPER_CONFIG.get(self.site, {})

    @property
    def enabled(self) -> bool:
        """Whether this scraper is enabled in config. Defaults to True."""
        return self.config.get("enabled", True)

    def get(self, url: str, **kwargs) -> requests.Response:
        resp = requests.get(url, headers=HEADERS, timeout=15, **kwargs)
        resp.raise_for_status()
        return resp

    @abstractmethod
    def scrape(self) -> list[dict]:
        """Return a list of product dicts for this site."""
        ...
