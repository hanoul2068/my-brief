import React, { useMemo, useRef } from 'react';
import { PanResponder, Pressable, StyleSheet, Text, View } from 'react-native';
import { AppEvent } from '../calendar';
import { WEEKDAYS, dayKey, daysCovered, monthGrid, sameDay } from '../dates';
import { colors } from '../theme';

type Props = {
  month: Date;
  selected: Date;
  events: AppEvent[];
  onSelect: (d: Date) => void;
  onSwipe: (dir: 1 | -1) => void;
};

const MAX_CHIPS = 3;

export default function MonthView({ month, selected, events, onSelect, onSwipe }: Props) {
  const days = useMemo(() => monthGrid(month), [month]);
  const today = new Date();

  const byDay = useMemo(() => {
    const map = new Map<string, AppEvent[]>();
    for (const e of events) {
      for (const d of daysCovered(e.start, e.end)) {
        const k = dayKey(d);
        const list = map.get(k) ?? [];
        list.push(e);
        map.set(k, list);
      }
    }
    return map;
  }, [events]);

  const swipeRef = useRef(onSwipe);
  swipeRef.current = onSwipe;
  const pan = useMemo(
    () =>
      PanResponder.create({
        onMoveShouldSetPanResponder: (_, g) => Math.abs(g.dx) > 20 && Math.abs(g.dx) > Math.abs(g.dy) * 2,
        onPanResponderRelease: (_, g) => {
          if (g.dx < -50) swipeRef.current(1);
          else if (g.dx > 50) swipeRef.current(-1);
        },
      }),
    [],
  );

  return (
    <View {...pan.panHandlers}>
      <View style={styles.weekRow}>
        {WEEKDAYS.map((w, i) => (
          <Text
            key={w}
            style={[styles.weekday, i === 0 && { color: colors.sunday }, i === 6 && { color: colors.saturday }]}
          >
            {w}
          </Text>
        ))}
      </View>
      {Array.from({ length: 6 }, (_, row) => (
        <View key={row} style={styles.row}>
          {days.slice(row * 7, row * 7 + 7).map((d) => {
            const inMonth = d.getMonth() === month.getMonth();
            const isSel = sameDay(d, selected);
            const isToday = sameDay(d, today);
            const list = byDay.get(dayKey(d)) ?? [];
            const dow = d.getDay();
            return (
              <Pressable
                key={d.toISOString()}
                style={[styles.cell, isSel && styles.cellSelected]}
                onPress={() => onSelect(d)}
              >
                <View style={[styles.dayNum, isToday && styles.today]}>
                  <Text
                    style={[
                      styles.dayText,
                      dow === 0 && { color: colors.sunday },
                      dow === 6 && { color: colors.saturday },
                      isToday && { color: '#fff', fontWeight: '700' },
                      !inMonth && { opacity: 0.35 },
                    ]}
                  >
                    {d.getDate()}
                  </Text>
                </View>
                {list.slice(0, MAX_CHIPS).map((e) => (
                  <View
                    key={e.id + e.start.getTime()}
                    style={[
                      styles.chip,
                      e.allDay || daysCovered(e.start, e.end).length > 1
                        ? { backgroundColor: e.color }
                        : { borderLeftWidth: 2, borderLeftColor: e.color, backgroundColor: e.color + '22' },
                      !inMonth && { opacity: 0.4 },
                    ]}
                  >
                    <Text
                      numberOfLines={1}
                      style={[
                        styles.chipText,
                        (e.allDay || daysCovered(e.start, e.end).length > 1) && { color: '#fff' },
                      ]}
                    >
                      {e.title}
                    </Text>
                  </View>
                ))}
                {list.length > MAX_CHIPS && <Text style={styles.more}>+{list.length - MAX_CHIPS}</Text>}
              </Pressable>
            );
          })}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  weekRow: { flexDirection: 'row', paddingVertical: 6, borderBottomWidth: StyleSheet.hairlineWidth, borderColor: colors.border },
  weekday: { flex: 1, textAlign: 'center', fontSize: 12, color: colors.sub },
  row: { flexDirection: 'row', borderBottomWidth: StyleSheet.hairlineWidth, borderColor: colors.border },
  cell: { flex: 1, minHeight: 74, paddingHorizontal: 1, paddingTop: 3, paddingBottom: 2 },
  cellSelected: { backgroundColor: colors.primarySoft },
  dayNum: { alignSelf: 'center', width: 22, height: 22, borderRadius: 11, alignItems: 'center', justifyContent: 'center', marginBottom: 2 },
  today: { backgroundColor: colors.primary },
  dayText: { fontSize: 12, color: colors.text },
  chip: { borderRadius: 3, paddingHorizontal: 2, marginBottom: 1, height: 14, justifyContent: 'center' },
  chipText: { fontSize: 9, color: colors.text },
  more: { fontSize: 9, color: colors.sub, textAlign: 'center' },
});
