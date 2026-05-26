"""SM-2 spaced repetition for quiz review."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db import store


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def schedule_after_quiz(
    user_id: str,
    question_id: str,
    score: int | None,
    *,
    threshold: int = 70,
) -> dict | None:
    """Create or reset review card when score is below threshold."""
    if score is None or score >= threshold:
        return None
    return store.upsert_review_card(user_id, question_id, quality=2)


def grade_review(user_id: str, question_id: str, quality: int) -> dict:
    """SM-2 update after user reviews a card. quality 0-5."""
    q = max(0, min(5, quality))
    card = store.get_review_card(user_id, question_id)
    if not card:
        card = store.upsert_review_card(user_id, question_id, quality=q)

    ef = float(card.get("easiness", 2.5))
    reps = int(card.get("repetitions", 0))
    interval = int(card.get("interval_days", 1))

    ef = max(1.3, ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))

    if q < 3:
        reps = 0
        interval = 1
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = max(1, round(interval * ef))
        reps += 1

    next_at = (_now() + timedelta(days=interval)).isoformat()
    return store.update_review_card(
        user_id,
        question_id,
        easiness=ef,
        repetitions=reps,
        interval_days=interval,
        next_review_at=next_at,
        last_quality=q,
    )


def due_reviews(user_id: str = "default", limit: int = 10) -> list[dict]:
    return store.list_due_reviews(user_id, limit=limit)


def review_stats(user_id: str = "default") -> dict:
    return store.review_stats(user_id)


def review_calendar(user_id: str, year: int, month: int) -> dict:
    """Per-day review counts for calendar UI."""
    cards = store.list_review_cards(user_id)
    today = _now().date()
    days: dict[str, dict[str, int]] = {}
    overdue_count = 0

    for card in cards:
        try:
            dt = _parse_dt(card["next_review_at"]).date()
        except Exception:
            continue
        if dt < today:
            overdue_count += 1
            key = today.isoformat()
            slot = days.setdefault(key, {"due": 0, "scheduled": 0, "overdue": 0})
            slot["overdue"] = slot.get("overdue", 0) + 1
            slot["due"] += 1
            continue
        if dt.year != year or dt.month != month:
            continue
        key = dt.isoformat()
        slot = days.setdefault(key, {"due": 0, "scheduled": 0, "overdue": 0})
        if dt <= today:
            slot["due"] += 1
        else:
            slot["scheduled"] += 1

    return {
        "year": year,
        "month": month,
        "today": today.isoformat(),
        "overdue_count": overdue_count,
        "days": days,
        "total_cards": len(cards),
    }
