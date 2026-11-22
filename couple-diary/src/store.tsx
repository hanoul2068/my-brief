import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { AppState } from 'react-native';
import { AppCalendar, ensurePermission, listCalendars } from './calendar';

type Ctx = {
  permission: 'unknown' | 'granted' | 'denied';
  calendars: AppCalendar[];
  /** Bumped whenever data may have changed (save, delete, app returning to foreground). */
  version: number;
  refresh: () => Promise<void>;
  requestPermission: () => Promise<void>;
};

const StoreContext = createContext<Ctx>({
  permission: 'unknown',
  calendars: [],
  version: 0,
  refresh: async () => {},
  requestPermission: async () => {},
});

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [permission, setPermission] = useState<Ctx['permission']>('unknown');
  const [calendars, setCalendars] = useState<AppCalendar[]>([]);
  const [version, setVersion] = useState(0);

  const refresh = useCallback(async () => {
    try {
      setCalendars(await listCalendars());
    } catch {
      // permission revoked in system settings
    }
    setVersion((v) => v + 1);
  }, []);

  const requestPermission = useCallback(async () => {
    const ok = await ensurePermission();
    setPermission(ok ? 'granted' : 'denied');
    if (ok) await refresh();
  }, [refresh]);

  useEffect(() => {
    requestPermission();
  }, [requestPermission]);

  // Partner's edits arrive through iCloud while we're in the background;
  // reload whenever the app comes back.
  useEffect(() => {
    const sub = AppState.addEventListener('change', (s) => {
      if (s === 'active' && permission === 'granted') refresh();
    });
    return () => sub.remove();
  }, [permission, refresh]);

  const value = useMemo(
    () => ({ permission, calendars, version, refresh, requestPermission }),
    [permission, calendars, version, refresh, requestPermission],
  );
  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore() {
  return useContext(StoreContext);
}
