import React, { useEffect, useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { AppEvent, Repeat, createEvent, deleteEvent, updateEvent } from '../calendar';
import DateField from '../components/DateField';
import { Chip, Dot, Section } from '../components/ui';
import { useSettings } from '../settings';
import { useStore } from '../store';
import { colors } from '../theme';

type Props = {
  visible: boolean;
  event: AppEvent | null;
  initialDate: Date;
  onClose: () => void;
};

const REPEATS: { key: Repeat; label: string }[] = [
  { key: 'none', label: '안 함' },
  { key: 'daily', label: '매일' },
  { key: 'weekly', label: '매주' },
  { key: 'monthly', label: '매월' },
  { key: 'yearly', label: '매년' },
];

const ALARMS: { key: number | null; label: string }[] = [
  { key: null, label: '없음' },
  { key: 0, label: '정시' },
  { key: 10, label: '10분 전' },
  { key: 60, label: '1시간 전' },
  { key: 60 * 24, label: '하루 전' },
];

function defaultStart(day: Date): Date {
  const now = new Date();
  const d = new Date(day);
  d.setHours(now.getHours() + 1, 0, 0, 0);
  return d;
}

/** Ask "this occurrence only / all following" for repeating events. */
function askScope(event: AppEvent | null, verb: string): Promise<boolean | null> {
  if (!event?.recurring) return Promise.resolve(true);
  return new Promise((resolve) =>
    Alert.alert('반복 일정', `어떤 일정을 ${verb}할까요?`, [
      { text: '취소', style: 'cancel', onPress: () => resolve(null) },
      { text: '이 일정만', onPress: () => resolve(false) },
      { text: '이후 모든 일정', onPress: () => resolve(true) },
    ]),
  );
}

export default function EventEditor({ visible, event, initialDate, onClose }: Props) {
  const { calendars, refresh } = useStore();
  const { settings } = useSettings();
  const writable = calendars.filter((c) => c.writable && c.id !== settings.diaryCalendarId);

  const [title, setTitle] = useState('');
  const [allDay, setAllDay] = useState(false);
  const [start, setStart] = useState(new Date());
  const [end, setEnd] = useState(new Date());
  const [calendarId, setCalendarId] = useState<string>('');
  const [location, setLocation] = useState('');
  const [notes, setNotes] = useState('');
  const [repeat, setRepeat] = useState<Repeat>('none');
  const [alarm, setAlarm] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!visible) return;
    if (event) {
      setTitle(event.title);
      setAllDay(event.allDay);
      setStart(event.start);
      setEnd(event.end);
      setCalendarId(event.calendarId);
      setLocation(event.location);
      setNotes(event.notes);
      setRepeat(event.recurrence);
      setAlarm(event.alarmMinutes);
    } else {
      const s = defaultStart(initialDate);
      setTitle('');
      setAllDay(false);
      setStart(s);
      setEnd(new Date(s.getTime() + 60 * 60 * 1000));
      const fallback =
        writable.find((c) => c.id === settings.defaultCalendarId)?.id ?? writable[0]?.id ?? '';
      setCalendarId(fallback);
      setLocation('');
      setNotes('');
      setRepeat('none');
      setAlarm(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, event]);

  const onChangeStart = (d: Date) => {
    const dur = end.getTime() - start.getTime();
    setStart(d);
    setEnd(new Date(d.getTime() + Math.max(dur, 0)));
  };

  const save = async () => {
    if (!calendarId) {
      Alert.alert('캘린더 없음', '설정에서 공유 캘린더를 먼저 만들어 주세요.');
      return;
    }
    const scope = await askScope(event, '수정');
    if (scope === null) return;
    setSaving(true);
    try {
      const input = {
        calendarId,
        title,
        start,
        end,
        allDay,
        location,
        notes,
        // Keep the original writer when editing someone else's event.
        author: event?.author ?? settings.myName,
        repeat,
        alarmMinutes: alarm,
      };
      if (event) await updateEvent(event, input, scope);
      else await createEvent(input);
      await refresh();
      onClose();
    } catch (e) {
      Alert.alert('저장 실패', String(e));
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!event) return;
    const scope = await askScope(event, '삭제');
    if (scope === null) return;
    const go = async () => {
      try {
        await deleteEvent(event, scope);
        await refresh();
        onClose();
      } catch (e) {
        Alert.alert('삭제 실패', String(e));
      }
    };
    if (event.recurring) go();
    else
      Alert.alert('일정 삭제', `"${event.title}"을(를) 삭제할까요?`, [
        { text: '취소', style: 'cancel' },
        { text: '삭제', style: 'destructive', onPress: go },
      ]);
  };

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
        <View style={styles.header}>
          <Pressable onPress={onClose} hitSlop={10}>
            <Text style={styles.cancel}>취소</Text>
          </Pressable>
          <Text style={styles.headerTitle}>{event ? '일정 수정' : '새 일정'}</Text>
          <Pressable onPress={save} disabled={saving} hitSlop={10}>
            <Text style={[styles.save, saving && { opacity: 0.4 }]}>저장</Text>
          </Pressable>
        </View>
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
            <Section>
              <TextInput
                style={styles.title}
                placeholder="일정 제목"
                placeholderTextColor={colors.faint}
                value={title}
                onChangeText={setTitle}
                autoFocus={!event}
              />
            </Section>

            <Section>
              <View style={styles.switchRow}>
                <Text style={styles.label}>하루 종일</Text>
                <Switch value={allDay} onValueChange={setAllDay} trackColor={{ true: colors.primary }} />
              </View>
              <DateField label="시작" value={start} onChange={onChangeStart} showTime={!allDay} />
              <DateField label="종료" value={end} onChange={setEnd} showTime={!allDay} />
            </Section>

            <Section title="캘린더">
              <View style={styles.wrap}>
                {writable.map((c) => (
                  <Pressable
                    key={c.id}
                    onPress={() => setCalendarId(c.id)}
                    style={[styles.calOption, calendarId === c.id && { borderColor: c.color, backgroundColor: c.color + '18' }]}
                  >
                    <Dot color={c.color} />
                    <Text style={styles.calText}>{c.title}</Text>
                  </Pressable>
                ))}
              </View>
            </Section>

            <Section title="반복">
              <View style={styles.wrap}>
                {REPEATS.map((r) => (
                  <Chip key={r.key} label={r.label} active={repeat === r.key} onPress={() => setRepeat(r.key)} />
                ))}
              </View>
            </Section>

            <Section title="알림">
              <View style={styles.wrap}>
                {ALARMS.map((a) => (
                  <Chip key={String(a.key)} label={a.label} active={alarm === a.key} onPress={() => setAlarm(a.key)} />
                ))}
              </View>
            </Section>

            <Section title="장소">
              <TextInput
                style={styles.input}
                placeholder="장소 추가"
                placeholderTextColor={colors.faint}
                value={location}
                onChangeText={setLocation}
              />
            </Section>

            <Section title="메모">
              <TextInput
                style={[styles.input, { minHeight: 90 }]}
                placeholder="메모를 남겨 보세요"
                placeholderTextColor={colors.faint}
                value={notes}
                onChangeText={setNotes}
                multiline
                textAlignVertical="top"
              />
            </Section>

            {event?.author && <Text style={styles.author}>✍️ {event.author}님이 등록한 일정</Text>}

            {event && (
              <Pressable style={styles.delete} onPress={remove}>
                <Text style={styles.deleteText}>일정 삭제</Text>
              </Pressable>
            )}
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.surface },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: colors.bg,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
  },
  headerTitle: { fontSize: 16, fontWeight: '700', color: colors.text },
  cancel: { fontSize: 16, color: colors.sub },
  save: { fontSize: 16, fontWeight: '700', color: colors.primary },
  body: { padding: 12, paddingBottom: 40 },
  title: { fontSize: 20, fontWeight: '600', color: colors.text },
  switchRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingBottom: 4 },
  label: { fontSize: 15, color: colors.text },
  wrap: { flexDirection: 'row', flexWrap: 'wrap' },
  calOption: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    paddingHorizontal: 10,
    paddingVertical: 6,
    marginRight: 6,
    marginBottom: 6,
  },
  calText: { fontSize: 13, color: colors.text },
  input: { fontSize: 15, color: colors.text, paddingVertical: 4 },
  author: { textAlign: 'center', color: colors.sub, fontSize: 13, marginVertical: 8 },
  delete: { alignItems: 'center', padding: 14, backgroundColor: colors.bg, borderRadius: 12, marginTop: 8 },
  deleteText: { color: colors.danger, fontSize: 15, fontWeight: '600' },
});
