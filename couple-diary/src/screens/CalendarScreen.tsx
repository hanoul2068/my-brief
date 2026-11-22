import React, { useMemo, useState } from 'react';
import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { AppEvent } from '../calendar';
import MonthView from '../components/MonthView';
import { Dot } from '../components/ui';
import { addDays, addMonths, dayKey, daysCovered, formatDate, formatTime, monthGrid, sameDay } from '../dates';
import { useEvents } from '../hooks';
import { useSettings } from '../settings';
import { colors } from '../theme';
import EventEditor from './EventEditor';

export default function CalendarScreen() {
  const { settings } = useSettings();
  const [month, setMonth] = useState(() => addMonths(new Date(), 0));
  const [selected, setSelected] = useState(() => new Date());
  const [editing, setEditing] = useState<AppEvent | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);

  const grid = useMemo(() => monthGrid(month), [month]);
  const { events } = useEvents(grid[0], addDays(grid[41], 1), undefined, settings.diaryCalendarId);

  const dayEvents = useMemo(
    () => events.filter((e) => daysCovered(e.start, e.end).some((d) => dayKey(d) === dayKey(selected))),
    [events, selected],
  );

  const changeMonth = (dir: 1 | -1) => {
    const m = addMonths(month, dir);
    setMonth(m);
    const now = new Date();
    const isThisMonth = m.getFullYear() === now.getFullYear() && m.getMonth() === now.getMonth();
    setSelected(isThisMonth ? now : m);
  };

  const goToday = () => {
    setMonth(addMonths(new Date(), 0));
    setSelected(new Date());
  };

  const onSelect = (d: Date) => {
    if (sameDay(d, selected)) {
      // Tapping the selected day again opens the editor, like TimeTree.
      openNew();
      return;
    }
    setSelected(d);
    if (d.getMonth() !== month.getMonth()) setMonth(addMonths(d, 0));
  };

  const openNew = () => {
    setEditing(null);
    setEditorOpen(true);
  };

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Pressable onPress={() => changeMonth(-1)} hitSlop={12}>
          <Text style={styles.arrow}>‹</Text>
        </Pressable>
        <Text style={styles.month}>
          {month.getFullYear()}년 {month.getMonth() + 1}월
        </Text>
        <Pressable onPress={() => changeMonth(1)} hitSlop={12}>
          <Text style={styles.arrow}>›</Text>
        </Pressable>
        <Pressable onPress={goToday} style={styles.todayBtn}>
          <Text style={styles.todayText}>오늘</Text>
        </Pressable>
      </View>

      <MonthView month={month} selected={selected} events={events} onSelect={onSelect} onSwipe={changeMonth} />

      <View style={styles.dayHeader}>
        <Text style={styles.dayTitle}>{formatDate(selected)}</Text>
        <Text style={styles.dayCount}>{dayEvents.length}개 일정</Text>
      </View>
      <FlatList
        data={dayEvents}
        keyExtractor={(e) => e.id + e.start.getTime()}
        contentContainerStyle={{ paddingBottom: 100 }}
        ListEmptyComponent={<Text style={styles.empty}>일정이 없어요. 날짜를 한 번 더 누르거나 + 를 눌러 추가하세요.</Text>}
        renderItem={({ item }) => (
          <Pressable
            style={styles.item}
            onPress={() => {
              setEditing(item);
              setEditorOpen(true);
            }}
          >
            <View style={[styles.bar, { backgroundColor: item.color }]} />
            <View style={styles.time}>
              {item.allDay ? (
                <Text style={styles.timeText}>하루 종일</Text>
              ) : (
                <>
                  <Text style={styles.timeText}>{formatTime(item.start)}</Text>
                  <Text style={styles.timeSub}>{formatTime(item.end)}</Text>
                </>
              )}
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.itemTitle} numberOfLines={1}>
                {item.recurring ? '🔁 ' : ''}
                {item.title}
              </Text>
              {!!item.location && <Text style={styles.itemSub} numberOfLines={1}>📍 {item.location}</Text>}
              {!!item.author && <Text style={styles.itemSub}>✍️ {item.author}</Text>}
            </View>
            <Dot color={item.color} size={8} />
          </Pressable>
        )}
      />

      <Pressable style={styles.fab} onPress={openNew}>
        <Text style={styles.fabText}>＋</Text>
      </Pressable>

      <EventEditor visible={editorOpen} event={editing} initialDate={selected} onClose={() => setEditorOpen(false)} />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, gap: 14 },
  arrow: { fontSize: 26, color: colors.sub, lineHeight: 28 },
  month: { fontSize: 20, fontWeight: '700', color: colors.text },
  todayBtn: { marginLeft: 'auto', borderWidth: 1, borderColor: colors.border, borderRadius: 14, paddingHorizontal: 12, paddingVertical: 4 },
  todayText: { fontSize: 13, color: colors.text },
  dayHeader: { flexDirection: 'row', alignItems: 'baseline', gap: 8, paddingHorizontal: 16, paddingTop: 12, paddingBottom: 6 },
  dayTitle: { fontSize: 16, fontWeight: '700', color: colors.text },
  dayCount: { fontSize: 13, color: colors.sub },
  empty: { color: colors.faint, textAlign: 'center', marginTop: 20, paddingHorizontal: 30, lineHeight: 20 },
  item: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, paddingHorizontal: 16, gap: 10 },
  bar: { width: 4, alignSelf: 'stretch', borderRadius: 2 },
  time: { width: 64 },
  timeText: { fontSize: 12, color: colors.text },
  timeSub: { fontSize: 11, color: colors.faint },
  itemTitle: { fontSize: 15, color: colors.text, fontWeight: '500' },
  itemSub: { fontSize: 12, color: colors.sub, marginTop: 2 },
  fab: {
    position: 'absolute',
    right: 20,
    bottom: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.2,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 3 },
    elevation: 4,
  },
  fabText: { color: '#fff', fontSize: 28, lineHeight: 30 },
});
