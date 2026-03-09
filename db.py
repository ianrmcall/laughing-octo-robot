"""
Database layer for the plant database.

Uses SQLAlchemy so the backend can be swapped from SQLite to PostgreSQL
by changing DATABASE_URL — everything else stays the same.

Schema
------
products       — one row per unique product (site + external id)
price_history  — one row every time a product's price changes
scrape_runs    — one row per scraper execution (for auditing / debugging)
"""

import os
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///plants.db")

engine = create_engine(DATABASE_URL, echo=False)

# Keep SQLite foreign-key enforcement on (it's off by default)
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id          = Column(Integer, primary_key=True)
    # Stable external key, e.g. "ecuagenera:dracula-roezlii"
    external_id = Column(String, unique=True, nullable=False, index=True)
    site        = Column(String, nullable=False, index=True)
    name        = Column(String, nullable=False)
    price       = Column(String)          # stored as the raw string, e.g. "$12.50"
    image_url   = Column(Text)
    product_url = Column(Text)
    in_stock    = Column(Boolean, default=True)
    first_seen  = Column(DateTime, nullable=False)
    last_seen   = Column(DateTime, nullable=False)

    price_history = relationship(
        "PriceHistory", back_populates="product", order_by="PriceHistory.recorded_at"
    )

    def __repr__(self):
        return f"<Product {self.external_id!r} {self.name!r}>"


class PriceHistory(Base):
    __tablename__ = "price_history"

    id          = Column(Integer, primary_key=True)
    product_id  = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    price       = Column(String)
    recorded_at = Column(DateTime, nullable=False)

    product = relationship("Product", back_populates="price_history")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id           = Column(Integer, primary_key=True)
    site         = Column(String, nullable=False)
    started_at   = Column(DateTime, nullable=False)
    finished_at  = Column(DateTime)
    products_found = Column(Integer)
    new_products   = Column(Integer)
    error        = Column(Text)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create all tables if they don't exist yet."""
    Base.metadata.create_all(engine)


def upsert_products(scraped: list[dict]) -> dict:
    """
    Insert or update products from a scraper run.

    Returns a summary dict:
        {"new": int, "updated": int, "total": int}
    """
    now = datetime.now(timezone.utc)
    counts = {"new": 0, "updated": 0, "total": len(scraped)}

    with Session(engine) as session:
        for item in scraped:
            existing = (
                session.query(Product)
                .filter_by(external_id=item["id"])
                .one_or_none()
            )

            if existing is None:
                product = Product(
                    external_id=item["id"],
                    site=item["site"],
                    name=item["name"],
                    price=item.get("price"),
                    image_url=item.get("image_url", ""),
                    product_url=item.get("product_url", ""),
                    in_stock=item.get("in_stock", True),
                    first_seen=now,
                    last_seen=now,
                )
                session.add(product)
                session.flush()  # get product.id
                if product.price:
                    session.add(PriceHistory(
                        product_id=product.id,
                        price=product.price,
                        recorded_at=now,
                    ))
                counts["new"] += 1
            else:
                # Record price change if the price moved
                if existing.price != item.get("price") and item.get("price"):
                    session.add(PriceHistory(
                        product_id=existing.id,
                        price=item["price"],
                        recorded_at=now,
                    ))
                    existing.price = item["price"]

                existing.name      = item["name"]
                existing.image_url = item.get("image_url", existing.image_url)
                existing.product_url = item.get("product_url", existing.product_url)
                existing.in_stock  = item.get("in_stock", existing.in_stock)
                existing.last_seen = now
                counts["updated"] += 1

        session.commit()

    return counts


def record_scrape_run(
    site: str,
    started_at: datetime,
    finished_at: datetime,
    products_found: int = 0,
    new_products: int = 0,
    error: str | None = None,
) -> None:
    with Session(engine) as session:
        session.add(ScrapeRun(
            site=site,
            started_at=started_at,
            finished_at=finished_at,
            products_found=products_found,
            new_products=new_products,
            error=error,
        ))
        session.commit()
