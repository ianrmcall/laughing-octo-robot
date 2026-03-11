import importlib
import pkgutil
from pathlib import Path

from .base import BaseScraper


def discover_scrapers() -> list[BaseScraper]:
    """Auto-discover all BaseScraper subclasses in this package.

    Scans every .py module in scrapers/, finds classes that extend
    BaseScraper, instantiates them, and returns enabled ones.
    """
    scrapers = []
    package_dir = Path(__file__).parent

    for module_info in pkgutil.iter_modules([str(package_dir)]):
        if module_info.name == "base":
            continue

        module = importlib.import_module(f".{module_info.name}", package=__package__)

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BaseScraper)
                and attr is not BaseScraper
            ):
                instance = attr()
                if instance.enabled:
                    scrapers.append(instance)

    return scrapers


SCRAPERS = discover_scrapers()
