import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

export type Settings = {
  /** Shown on what you write, so your partner sees who added it ("✍️ 남편"). */
  myName: string;
  /** Calendar new events go to by default — ideally the shared iCloud calendar. */
  defaultCalendarId: string | null;
  /** Calendar that stores diary entries (also shareable through iCloud). */
  diaryCalendarId: string | null;
  /** Calendars the user switched off in the month view. */
  hiddenCalendarIds: string[];
};

const DEFAULTS: Settings = {
  myName: '',
  defaultCalendarId: null,
  diaryCalendarId: null,
  hiddenCalendarIds: [],
};

const KEY = 'couple-diary/settings/v1';

type Ctx = {
  settings: Settings;
  loaded: boolean;
  update: (patch: Partial<Settings>) => void;
};

const SettingsContext = createContext<Ctx>({ settings: DEFAULTS, loaded: false, update: () => {} });

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<Settings>(DEFAULTS);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((raw) => {
        if (raw) setSettings({ ...DEFAULTS, ...JSON.parse(raw) });
      })
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  const update = useCallback((patch: Partial<Settings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      AsyncStorage.setItem(KEY, JSON.stringify(next)).catch(() => {});
      return next;
    });
  }, []);

  return (
    <SettingsContext.Provider value={{ settings, loaded, update }}>{children}</SettingsContext.Provider>
  );
}

export function useSettings() {
  return useContext(SettingsContext);
}
