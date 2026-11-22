export const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];

export function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

export function addDays(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

export function addMonths(d: Date, n: number): Date {
  return new Date(d.getFullYear(), d.getMonth() + n, 1);
}

export function sameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

/** "2026-11-22" — stable key for grouping by day in local time. */
export function dayKey(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${m}-${day}`;
}

/** 6 weeks x 7 days grid (Sunday first) covering the given month. */
export function monthGrid(month: Date): Date[] {
  const first = new Date(month.getFullYear(), month.getMonth(), 1);
  const start = addDays(first, -first.getDay());
  return Array.from({ length: 42 }, (_, i) => addDays(start, i));
}

export function formatTime(d: Date): string {
  const h = d.getHours();
  const m = String(d.getMinutes()).padStart(2, '0');
  const ampm = h < 12 ? '오전' : '오후';
  const hh = h % 12 === 0 ? 12 : h % 12;
  return `${ampm} ${hh}:${m}`;
}

export function formatDate(d: Date): string {
  return `${d.getMonth() + 1}월 ${d.getDate()}일 (${WEEKDAYS[d.getDay()]})`;
}

export function formatFullDate(d: Date): string {
  return `${d.getFullYear()}년 ${formatDate(d)}`;
}

/**
 * Every local day an event touches. An end exactly at midnight belongs to the
 * previous day (a 2-day all-day event ends at 00:00 of day 3 on Android).
 */
export function daysCovered(start: Date, end: Date): Date[] {
  let last = new Date(end);
  if (last > start && last.getHours() === 0 && last.getMinutes() === 0 && last.getSeconds() === 0) {
    last = new Date(last.getTime() - 1);
  }
  if (last < start) last = start;
  const out: Date[] = [];
  for (let d = startOfDay(start); d <= last; d = addDays(d, 1)) {
    out.push(d);
    if (out.length > 366) break;
  }
  return out;
}
