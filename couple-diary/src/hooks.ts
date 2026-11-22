import { useEffect, useMemo, useState } from 'react';
import { AppEvent, fetchEvents } from './calendar';
import { useSettings } from './settings';
import { useStore } from './store';

/** Events from visible calendars (or only `onlyCalendarId`) within [from, to). */
export function useEvents(from: Date, to: Date, onlyCalendarId?: string | null, exclude?: string | null) {
  const { calendars, version, permission } = useStore();
  const { settings } = useSettings();
  const [events, setEvents] = useState<AppEvent[]>([]);
  const [loading, setLoading] = useState(false);

  const targets = useMemo(() => {
    if (onlyCalendarId !== undefined) {
      return calendars.filter((c) => c.id === onlyCalendarId);
    }
    return calendars.filter((c) => !settings.hiddenCalendarIds.includes(c.id) && c.id !== exclude);
  }, [calendars, settings.hiddenCalendarIds, onlyCalendarId, exclude]);

  const fromMs = from.getTime();
  const toMs = to.getTime();

  useEffect(() => {
    if (permission !== 'granted') return;
    let cancelled = false;
    setLoading(true);
    fetchEvents(targets, new Date(fromMs), new Date(toMs))
      .then((e) => !cancelled && setEvents(e))
      .catch(() => !cancelled && setEvents([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [targets, fromMs, toMs, version, permission]);

  return { events, loading };
}
