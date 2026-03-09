from .andysorchids import AndysOrchidsScraper
from .ecuagenera import EcuageneraScraper
from .ecuageneraus import EcuageneraUSScraper
from .kartuz import KartuzScraper
from .lyndonlyon import LyndonLyonScraper

SCRAPERS = [
    EcuageneraScraper(),
    EcuageneraUSScraper(),
    AndysOrchidsScraper(),
    KartuzScraper(),
    LyndonLyonScraper(),
]
