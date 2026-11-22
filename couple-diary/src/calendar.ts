/**
 * All data lives in the phone's system calendar (iOS EventKit / Android
 * CalendarContract) instead of a private server like TimeTree uses.
 * That is what makes events show up everywhere: Apple Calendar, widgets,
 * Siri, CarPlay, Google Calendar, and any other app that reads the
 * system calendar. Sharing with a partner is done by iCloud's own shared
 * calendars, so no backend is needed.
 */
import { Platform } from 'react-native';
import * as Cal from 'expo-calendar/legacy';

export type AppCalendar = {
  id: string;
  title: string;
  color: string;
  sourceName: string;
  writable: boolean;
};

export type AppEvent = {
  id: string;
  calendarId: string;
  title: string;
  start: Date;
  end: Date;
  allDay: boolean;
  location: string;
  /** Notes without the author footer. */
  notes: string;
  author: string | null;
  color: string;
  recurring: boolean;
  recurrence: Repeat;
  alarmMinutes: number | null;
};

export type Repeat = 'none' | 'daily' | 'weekly' | 'monthly' | 'yearly';

export type EventInput = {
  calendarId: string;
  title: string;
  start: Date;
  end: Date;
  allDay: boolean;
  location: string;
  notes: string;
  author: string;
  repeat: Repeat;
  alarmMinutes: number | null;
};

const AUTHOR_MARK = '✍️ ';

export function withAuthor(notes: string, author: string): string {
  const body = notes.trim();
  if (!author.trim()) return body;
  return body ? `${body}\n\n${AUTHOR_MARK}${author.trim()}` : `${AUTHOR_MARK}${author.trim()}`;
}

export function splitAuthor(notes: string | null | undefined): { body: string; author: string | null } {
  const text = notes ?? '';
  const idx = text.lastIndexOf(AUTHOR_MARK);
  if (idx === -1) return { body: text, author: null };
  const tail = text.slice(idx + AUTHOR_MARK.length).trim();
  if (!tail || tail.includes('\n')) return { body: text, author: null };
  return { body: text.slice(0, idx).trim(), author: tail };
}

export async function ensurePermission(): Promise<boolean> {
  const current = await Cal.getCalendarPermissionsAsync();
  if (current.granted) return true;
  const req = await Cal.requestCalendarPermissionsAsync();
  return req.granted;
}

export async function listCalendars(): Promise<AppCalendar[]> {
  const cals = await Cal.getCalendarsAsync(Cal.EntityTypes.EVENT);
  return cals
    .map((c) => ({
      id: c.id,
      title: c.title,
      color: c.color || '#888',
      sourceName: c.source?.name ?? '',
      writable: c.allowsModifications,
    }))
    .sort((a, b) => a.sourceName.localeCompare(b.sourceName) || a.title.localeCompare(b.title));
}

/** Creates a calendar in iCloud when possible so it can be shared with a partner. */
export async function createSharedCalendar(title: string, color: string): Promise<string> {
  if (Platform.OS === 'ios') {
    const sources = await Cal.getSourcesAsync();
    const icloud = sources.find((s) => s.type === Cal.SourceType.CALDAV && /icloud/i.test(s.name));
    const fallback = (await Cal.getDefaultCalendarAsync()).source;
    const source = icloud ?? fallback;
    return Cal.createCalendarAsync({
      title,
      color,
      entityType: Cal.EntityTypes.EVENT,
      sourceId: source.id,
      source,
      name: title,
      ownerAccount: 'personal',
      accessLevel: Cal.CalendarAccessLevel.OWNER,
    });
  }
  // Android: attach to the Google account if one exists so it syncs, otherwise local.
  const cals = await Cal.getCalendarsAsync(Cal.EntityTypes.EVENT);
  const google = cals.find((c) => c.source?.type === 'com.google' && c.isPrimary);
  const source = google
    ? google.source
    : { isLocalAccount: true, name: '커플 다이어리', type: Cal.SourceType.LOCAL };
  return Cal.createCalendarAsync({
    title,
    color,
    entityType: Cal.EntityTypes.EVENT,
    source,
    name: title,
    ownerAccount: google?.ownerAccount ?? 'personal',
    accessLevel: Cal.CalendarAccessLevel.OWNER,
  });
}

function toRepeat(rule: Cal.RecurrenceRule | null): Repeat {
  if (!rule) return 'none';
  switch (rule.frequency) {
    case Cal.Frequency.DAILY:
      return 'daily';
    case Cal.Frequency.WEEKLY:
      return 'weekly';
    case Cal.Frequency.MONTHLY:
      return 'monthly';
    case Cal.Frequency.YEARLY:
      return 'yearly';
    default:
      return 'none';
  }
}

function fromRepeat(r: Repeat): Cal.RecurrenceRule | null {
  const map = {
    daily: Cal.Frequency.DAILY,
    weekly: Cal.Frequency.WEEKLY,
    monthly: Cal.Frequency.MONTHLY,
    yearly: Cal.Frequency.YEARLY,
  } as const;
  return r === 'none' ? null : { frequency: map[r], interval: 1 };
}

export async function fetchEvents(
  calendars: AppCalendar[],
  from: Date,
  to: Date,
): Promise<AppEvent[]> {
  if (calendars.length === 0) return [];
  const colors = new Map(calendars.map((c) => [c.id, c.color]));
  const raw = await Cal.getEventsAsync(
    calendars.map((c) => c.id),
    from,
    to,
  );
  return raw
    .map((e) => {
      const { body, author } = splitAuthor(e.notes);
      const offset = e.alarms?.find((a) => typeof a.relativeOffset === 'number')?.relativeOffset;
      return {
        id: e.id,
        calendarId: e.calendarId,
        title: e.title || '(제목 없음)',
        start: new Date(e.startDate),
        end: new Date(e.endDate),
        allDay: e.allDay,
        location: e.location ?? '',
        notes: body,
        author,
        color: colors.get(e.calendarId) ?? '#888',
        recurring: !!e.recurrenceRule,
        recurrence: toRepeat(e.recurrenceRule),
        alarmMinutes: offset === undefined ? null : -offset,
      };
    })
    .sort((a, b) => Number(b.allDay) - Number(a.allDay) || a.start.getTime() - b.start.getTime());
}

function toDetails(input: EventInput) {
  let { start, end } = input;
  if (input.allDay) {
    start = new Date(start.getFullYear(), start.getMonth(), start.getDate());
    end = new Date(end.getFullYear(), end.getMonth(), end.getDate(), 23, 59, 0);
  }
  if (end < start) end = new Date(start.getTime() + 60 * 60 * 1000);
  return {
    title: input.title.trim() || '(제목 없음)',
    startDate: start,
    endDate: end,
    allDay: input.allDay,
    location: input.location.trim(),
    notes: withAuthor(input.notes, input.author),
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    recurrenceRule: fromRepeat(input.repeat),
    alarms: input.alarmMinutes === null ? [] : [{ relativeOffset: -input.alarmMinutes }],
  };
}

export async function createEvent(input: EventInput): Promise<string> {
  return Cal.createEventAsync(input.calendarId, toDetails(input));
}

/**
 * futureEvents=false edits only the tapped occurrence of a repeating event.
 * Moving an event to another calendar isn't supported by EventKit updates,
 * so that case is done as create + delete.
 */
export async function updateEvent(
  original: AppEvent,
  input: EventInput,
  futureEvents = true,
): Promise<void> {
  if (original.calendarId !== input.calendarId) {
    await createEvent(input);
    await deleteEvent(original, futureEvents);
    return;
  }
  const opts = original.recurring ? { futureEvents, instanceStartDate: original.start } : {};
  await Cal.updateEventAsync(original.id, toDetails(input), opts);
}

export async function deleteEvent(event: AppEvent, futureEvents = true): Promise<void> {
  const opts = event.recurring ? { futureEvents, instanceStartDate: event.start } : {};
  await Cal.deleteEventAsync(event.id, opts);
}

/* ---------- Diary ---------- */

export const MOODS = ['😊', '🥰', '😆', '😌', '😐', '😢', '😡', '😴', '🤒', '🎉'];

export type DiaryEntry = {
  event: AppEvent;
  mood: string;
  body: string;
  author: string | null;
  date: Date;
};

export function toDiaryEntry(e: AppEvent): DiaryEntry {
  const mood = MOODS.find((m) => e.title.startsWith(m)) ?? '📝';
  return { event: e, mood, body: e.notes, author: e.author, date: e.start };
}

export function diaryTitle(mood: string, author: string, body: string): string {
  const firstLine = body.trim().split('\n')[0].slice(0, 30);
  const who = author.trim() ? `${author.trim()}: ` : '';
  return `${mood} ${who}${firstLine || '오늘의 일기'}`;
}
