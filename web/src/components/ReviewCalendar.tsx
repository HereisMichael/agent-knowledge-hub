import { useEffect, useState } from "react";
import { quizReviewCalendar } from "../api";

type DaySlot = { due: number; scheduled: number; overdue?: number };

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];

function daysInMonth(year: number, month: number) {
  return new Date(year, month, 0).getDate();
}

function firstWeekday(year: number, month: number) {
  const d = new Date(year, month - 1, 1).getDay();
  return d === 0 ? 6 : d - 1;
}

export function ReviewCalendar() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [data, setData] = useState<{
    today: string;
    overdue_count: number;
    total_cards: number;
    days: Record<string, DaySlot>;
  } | null>(null);

  useEffect(() => {
    quizReviewCalendar(year, month).then(setData).catch(() => setData(null));
  }, [year, month]);

  function prevMonth() {
    if (month === 1) {
      setYear((y) => y - 1);
      setMonth(12);
    } else setMonth((m) => m - 1);
  }

  function nextMonth() {
    if (month === 12) {
      setYear((y) => y + 1);
      setMonth(1);
    } else setMonth((m) => m + 1);
  }

  const totalDays = daysInMonth(year, month);
  const startPad = firstWeekday(year, month);
  const cells: (number | null)[] = [
    ...Array(startPad).fill(null),
    ...Array.from({ length: totalDays }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  return (
    <div className="review-calendar">
      <div className="review-calendar-nav">
        <button type="button" className="btn btn-ghost" onClick={prevMonth} aria-label="上个月">
          ‹
        </button>
        <span className="review-calendar-title">
          {year} 年 {month} 月
        </span>
        <button type="button" className="btn btn-ghost" onClick={nextMonth} aria-label="下个月">
          ›
        </button>
      </div>

      {data && (
        <p className="review-calendar-summary">
          共 {data.total_cards} 张复习卡
          {data.overdue_count > 0 && (
            <span className="review-overdue-badge"> · {data.overdue_count} 张已逾期</span>
          )}
        </p>
      )}

      <div className="review-calendar-weekdays">
        {WEEKDAYS.map((w) => (
          <span key={w}>{w}</span>
        ))}
      </div>

      <div className="review-calendar-grid">
        {cells.map((day, i) => {
          if (day == null) {
            return <div key={`e-${i}`} className="review-cal-cell empty" />;
          }
          const key = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
          const slot = data?.days[key];
          const isToday = data?.today === key;
          const count = (slot?.due ?? 0) + (slot?.scheduled ?? 0);
          const hasDue = (slot?.due ?? 0) > 0 || (slot?.overdue ?? 0) > 0;

          return (
            <div
              key={key}
              className={`review-cal-cell${isToday ? " today" : ""}${hasDue ? " has-due" : ""}${count > 0 ? " has-cards" : ""}`}
              title={
                slot
                  ? `待复习 ${slot.due} · 已排期 ${slot.scheduled}`
                  : undefined
              }
            >
              <span className="review-cal-day">{day}</span>
              {count > 0 && <span className="review-cal-count">{count}</span>}
            </div>
          );
        })}
      </div>

      <div className="review-calendar-legend">
        <span>
          <i className="legend-dot due" /> 待复习
        </span>
        <span>
          <i className="legend-dot scheduled" /> 已排期
        </span>
        <span>
          <i className="legend-dot today" /> 今天
        </span>
      </div>
    </div>
  );
}
