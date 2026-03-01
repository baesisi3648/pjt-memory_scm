# @TASK T-SCHEDULER - Data collection pipeline
# @SPEC Background job: fetches external data and stores as DataPoints
"""Data collection pipeline - fetches external data and stores as DataPoints."""
import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.core.database import engine
from app.models.data_point import DataPoint
from app.models.data_source import DataSource
from app.models.company import Company

logger = logging.getLogger(__name__)


def collect_stock_prices():
    """Collect stock prices for companies with tickers via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance not installed, skipping stock collection")
        return

    with Session(engine) as session:
        # Get or create data source
        source = session.exec(
            select(DataSource).where(DataSource.name == "Yahoo Finance")
        ).first()
        if not source:
            source = DataSource(name="Yahoo Finance", type="api", is_active=True)
            session.add(source)
            session.flush()

        companies = session.exec(
            select(Company).where(Company.ticker != None)  # noqa: E711
        ).all()

        for company in companies:
            try:
                ticker = yf.Ticker(company.ticker)
                info = ticker.info
                price = info.get("currentPrice") or info.get(
                    "regularMarketPrice"
                )
                if price:
                    dp = DataPoint(
                        source_id=source.id,
                        company_id=company.id,
                        metric="stock_price",
                        value=float(price),
                        unit=(
                            "KRW"
                            if company.ticker.endswith((".KS", ".KQ"))
                            else "JPY"
                            if company.ticker.endswith(".T")
                            else "USD"
                        ),
                        timestamp=datetime.now(timezone.utc),
                    )
                    session.add(dp)
                    logger.info(
                        "Collected price for %s: %s", company.name, price
                    )

                market_cap = info.get("marketCap")
                if market_cap:
                    dp2 = DataPoint(
                        source_id=source.id,
                        company_id=company.id,
                        metric="market_cap",
                        value=float(market_cap),
                        unit="USD",
                        timestamp=datetime.now(timezone.utc),
                    )
                    session.add(dp2)
            except Exception as e:
                logger.error(
                    "Failed to collect data for %s: %s", company.name, e
                )

        session.commit()
        logger.info(
            "Stock price collection completed for %d companies",
            len(companies),
        )


def collect_exchange_rates():
    """Collect exchange rates from frankfurter.app."""
    import httpx

    with Session(engine) as session:
        source = session.exec(
            select(DataSource).where(DataSource.name == "Frankfurter")
        ).first()
        if not source:
            source = DataSource(
                name="Frankfurter", type="api", is_active=True
            )
            session.add(source)
            session.flush()

        try:
            resp = httpx.get(
                "https://api.frankfurter.app/latest",
                params={"from": "USD", "to": "KRW,JPY,TWD,EUR"},
                timeout=10.0,
            )
            resp.raise_for_status()
            rates = resp.json().get("rates", {})

            for currency, rate in rates.items():
                dp = DataPoint(
                    source_id=source.id,
                    company_id=None,
                    metric=f"exchange_rate_USD_{currency}",
                    value=float(rate),
                    unit=currency,
                    timestamp=datetime.now(timezone.utc),
                )
                session.add(dp)

            session.commit()
            logger.info("Exchange rates collected: %s", rates)
        except Exception as e:
            logger.error("Failed to collect exchange rates: %s", e)
