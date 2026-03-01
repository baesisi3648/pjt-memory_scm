# @TASK T-SCHEDULER - APScheduler background job configuration
# @SPEC Background scheduler for periodic data collection
"""APScheduler configuration for background data collection."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def start_scheduler():
    """Start the background scheduler with data collection jobs."""
    from app.services.data_collector import (
        collect_exchange_rates,
        collect_stock_prices,
    )

    # Stock prices every 30 minutes during market hours
    scheduler.add_job(
        collect_stock_prices,
        trigger=IntervalTrigger(minutes=30),
        id="collect_stock_prices",
        name="Collect stock prices",
        replace_existing=True,
    )

    # Exchange rates every hour
    scheduler.add_job(
        collect_exchange_rates,
        trigger=IntervalTrigger(hours=1),
        id="collect_exchange_rates",
        name="Collect exchange rates",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Background scheduler started with %d jobs",
        len(scheduler.get_jobs()),
    )


def stop_scheduler():
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
