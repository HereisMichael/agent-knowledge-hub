"""APScheduler daily content update."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.content.daily_update import run_daily_update

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _parse_cron() -> dict:
    parts = settings.content_update_cron.strip().split()
    if len(parts) == 5:
        return {"minute": parts[0], "hour": parts[1], "day": parts[2], "month": parts[3], "day_of_week": parts[4]}
    return {"hour": "6", "minute": "0"}


def start_scheduler() -> None:
    global _scheduler
    if not settings.content_scheduler_enabled:
        return
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone=settings.content_tz)
    cron = _parse_cron()

    def job() -> None:
        try:
            result = run_daily_update()
            logger.info("Daily update: %s", result)
        except Exception as e:
            logger.exception("Daily update failed: %s", e)

    _scheduler.add_job(
        job,
        CronTrigger(
            hour=int(cron.get("hour", 6)),
            minute=int(cron.get("minute", 0)),
            timezone=settings.content_tz,
        ),
        id="daily_content_update",
    )
    _scheduler.start()
    logger.info("Content scheduler started (%s)", settings.content_update_cron)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
