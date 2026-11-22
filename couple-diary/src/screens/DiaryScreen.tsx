import React, { useMemo, useState } from 'react';
import {
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { DiaryEntry, MOODS, createEvent, deleteEvent, diaryTitle, toDiaryEntry, updateEvent } from '../calendar';
import DateField from '../components/DateField';
import { addMonths, formatFullDate, startOfDay } from '../dates';
import { useEvents } from '../hooks';
import { useSettings } from '../settings';
import { useStore } from '../store';
import { colors } from '../theme';

/**
 * Diary entries are stored as all-day events in a dedicated "diary"
 * calendar, so they sync to your partner through the same iCloud sharing
 * and stay readable in Apple Calendar even without this app.
 */
export default function DiaryScreen({ goSettings }: { goSettings: () => void }) {
  const { settings } = useSettings();
  const [month, setMonth] = useState(() => addMonths(new Date(), 0));
  const [editing, setEditing] = useState<DiaryEntry | null>(null);
  const [open, setOpen] = useState(false);

  const { events } = useEvents(month, addMonths(month, 1), settings.diaryCalendarId);
  const entries = useMemo(
    () => events.map(toDiaryEntry).sort((a, b) => b.date.getTime() - a.date.getTime()),
    [events],
  );

  if (!settings.diaryCalendarId) {
    return (
      <View style={styles.setup}>
        <Text style={styles.setupEmoji}>📔</Text>
        <Text style={styles.setupTitle}>일기장 캘린더가 아직 없어요</Text>
        <Text style={styles.setupText}>설정에서 "일기장 만들기"를 누르면 iCloud에 일기 전용 캘린더가 생겨요. 이걸 배우자와 공유하면 서로의 일기를 볼 수 있어요.</Text>
        <Pressable style={styles.setupBtn} onPress={goSettings}>
          <Text style={styles.setupBtnText}>설정으로 가기</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Pressable onPress={() => setMonth(addMonths(month, -1))} hitSlop={12}>
          <Text style={styles.arrow}>‹</Text>
        </Pressable>
        <Text style={styles.month}>
          {month.getFullYear()}년 {month.getMonth() + 1}월의 일기
        </Text>
        <Pressable onPress={() => setMonth(addMonths(month, 1))} hitSlop={12}>
          <Text style={styles.arrow}>›</Text>
        </Pressable>
      </View>

      <FlatList
        data={entries}
        keyExtractor={(e) => e.event.id + e.event.start.getTime()}
        contentContainerStyle={{ padding: 12, paddingBottom: 100 }}
        ListEmptyComponent={<Text style={styles.empty}>이 달에 쓴 일기가 없어요.</Text>}
        renderItem={({ item }) => {
          const mine = !!settings.myName && item.author === settings.myName;
          return (
            <Pressable
              style={[styles.card, mine ? styles.cardMine : styles.cardPartner]}
              onPress={() => {
                setEditing(item);
                setOpen(true);
              }}
            >
              <View style={styles.cardHead}>
                <Text style={styles.mood}>{item.mood}</Text>
                <View style={{ flex: 1 }}>
                  <Text style={styles.cardDate}>{formatFullDate(item.date)}</Text>
                  <Text style={styles.cardAuthor}>{item.author ? `${item.author}의 일기` : '일기'}</Text>
                </View>
              </View>
              <Text style={styles.cardBody} numberOfLines={6}>
                {item.body}
              </Text>
            </Pressable>
          );
        }}
      />

      <Pressable
        style={styles.fab}
        onPress={() => {
          setEditing(null);
          setOpen(true);
        }}
      >
        <Text style={styles.fabText}>✎</Text>
      </Pressable>

      <DiaryEditor visible={open} entry={editing} onClose={() => setOpen(false)} />
    </View>
  );
}

function DiaryEditor({ visible, entry, onClose }: { visible: boolean; entry: DiaryEntry | null; onClose: () => void }) {
  const { settings } = useSettings();
  const { refresh } = useStore();
  const [date, setDate] = useState(new Date());
  const [mood, setMood] = useState(MOODS[0]);
  const [body, setBody] = useState('');

  React.useEffect(() => {
    if (!visible) return;
    setDate(entry?.date ?? new Date());
    setMood(entry?.mood && MOODS.includes(entry.mood) ? entry.mood : MOODS[0]);
    setBody(entry?.body ?? '');
  }, [visible, entry]);

  const save = async () => {
    if (!body.trim()) {
      Alert.alert('내용을 입력해 주세요');
      return;
    }
    const author = entry?.author ?? settings.myName;
    const day = startOfDay(date);
    const input = {
      calendarId: settings.diaryCalendarId!,
      title: diaryTitle(mood, author, body),
      start: day,
      end: day,
      allDay: true,
      location: '',
      notes: body,
      author,
      repeat: 'none' as const,
      alarmMinutes: null,
    };
    try {
      if (entry) await updateEvent(entry.event, input);
      else await createEvent(input);
      await refresh();
      onClose();
    } catch (e) {
      Alert.alert('저장 실패', String(e));
    }
  };

  const remove = () => {
    if (!entry) return;
    Alert.alert('일기 삭제', '이 일기를 삭제할까요?', [
      { text: '취소', style: 'cancel' },
      {
        text: '삭제',
        style: 'destructive',
        onPress: async () => {
          await deleteEvent(entry.event);
          await refresh();
          onClose();
        },
      },
    ]);
  };

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }} edges={['top', 'bottom']}>
        <View style={styles.editorHeader}>
          <Pressable onPress={onClose} hitSlop={10}>
            <Text style={styles.cancel}>취소</Text>
          </Pressable>
          <Text style={styles.editorTitle}>{entry ? '일기 수정' : '오늘의 일기'}</Text>
          <Pressable onPress={save} hitSlop={10}>
            <Text style={styles.saveText}>저장</Text>
          </Pressable>
        </View>
        <KeyboardAvoidingView style={{ flex: 1, padding: 16 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <DateField label="날짜" value={date} onChange={setDate} showTime={false} />
          <Text style={styles.label}>오늘 기분은?</Text>
          <View style={styles.moods}>
            {MOODS.map((m) => (
              <Pressable key={m} onPress={() => setMood(m)} style={[styles.moodBtn, mood === m && styles.moodActive]}>
                <Text style={{ fontSize: 24 }}>{m}</Text>
              </Pressable>
            ))}
          </View>
          <TextInput
            style={styles.textArea}
            multiline
            placeholder="오늘 있었던 일을 적어 보세요"
            placeholderTextColor={colors.faint}
            value={body}
            onChangeText={setBody}
            textAlignVertical="top"
            autoFocus={!entry}
          />
          {entry && (
            <Pressable onPress={remove} style={{ padding: 14, alignItems: 'center' }}>
              <Text style={{ color: colors.danger, fontWeight: '600' }}>일기 삭제</Text>
            </Pressable>
          )}
        </KeyboardAvoidingView>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.surface },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 16, paddingVertical: 10, backgroundColor: colors.bg },
  arrow: { fontSize: 26, color: colors.sub, lineHeight: 28 },
  month: { fontSize: 18, fontWeight: '700', color: colors.text },
  empty: { textAlign: 'center', color: colors.faint, marginTop: 40 },
  card: { borderRadius: 14, padding: 14, marginBottom: 10, backgroundColor: colors.bg },
  cardMine: { borderLeftWidth: 4, borderLeftColor: colors.primary },
  cardPartner: { borderLeftWidth: 4, borderLeftColor: '#F26B8A' },
  cardHead: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 8 },
  mood: { fontSize: 30 },
  cardDate: { fontSize: 14, fontWeight: '700', color: colors.text },
  cardAuthor: { fontSize: 12, color: colors.sub, marginTop: 2 },
  cardBody: { fontSize: 15, lineHeight: 22, color: colors.text },
  fab: {
    position: 'absolute', right: 20, bottom: 20, width: 56, height: 56, borderRadius: 28,
    backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center', elevation: 4,
    shadowColor: '#000', shadowOpacity: 0.2, shadowRadius: 6, shadowOffset: { width: 0, height: 3 },
  },
  fabText: { color: '#fff', fontSize: 24 },
  setup: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 30, backgroundColor: colors.bg },
  setupEmoji: { fontSize: 50, marginBottom: 12 },
  setupTitle: { fontSize: 18, fontWeight: '700', color: colors.text, marginBottom: 8 },
  setupText: { fontSize: 14, color: colors.sub, textAlign: 'center', lineHeight: 21, marginBottom: 20 },
  setupBtn: { backgroundColor: colors.primary, borderRadius: 10, paddingHorizontal: 20, paddingVertical: 12 },
  setupBtnText: { color: '#fff', fontWeight: '700' },
  editorHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth, borderColor: colors.border,
  },
  editorTitle: { fontSize: 16, fontWeight: '700', color: colors.text },
  cancel: { fontSize: 16, color: colors.sub },
  saveText: { fontSize: 16, fontWeight: '700', color: colors.primary },
  label: { fontSize: 14, color: colors.sub, marginTop: 12, marginBottom: 6 },
  moods: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 12 },
  moodBtn: { padding: 6, borderRadius: 10 },
  moodActive: { backgroundColor: colors.primarySoft },
  textArea: { flex: 1, fontSize: 16, lineHeight: 24, color: colors.text, backgroundColor: colors.surface, borderRadius: 12, padding: 14 },
});
