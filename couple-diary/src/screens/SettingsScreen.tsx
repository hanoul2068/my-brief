import React, { useState } from 'react';
import { Alert, Linking, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from 'react-native';
import { createSharedCalendar } from '../calendar';
import { Chip, Dot, Section } from '../components/ui';
import { useSettings } from '../settings';
import { useStore } from '../store';
import { CALENDAR_COLORS, colors } from '../theme';

export default function SettingsScreen() {
  const { settings, update } = useSettings();
  const { calendars, refresh } = useStore();
  const [name, setName] = useState(settings.myName);
  const [busy, setBusy] = useState(false);

  const make = async (kind: 'shared' | 'diary') => {
    setBusy(true);
    try {
      const id =
        kind === 'shared'
          ? await createSharedCalendar('우리 캘린더', CALENDAR_COLORS[0])
          : await createSharedCalendar('우리 일기장', CALENDAR_COLORS[1]);
      if (kind === 'shared') update({ defaultCalendarId: id });
      else update({ diaryCalendarId: id });
      await refresh();
      Alert.alert('만들었어요', '이제 아래 "배우자와 공유하기" 안내대로 아이폰 캘린더 앱에서 공유해 주세요.');
    } catch (e) {
      Alert.alert('만들기 실패', String(e));
    } finally {
      setBusy(false);
    }
  };

  const toggleHidden = (id: string) => {
    const hidden = settings.hiddenCalendarIds.includes(id)
      ? settings.hiddenCalendarIds.filter((h) => h !== id)
      : [...settings.hiddenCalendarIds, id];
    update({ hiddenCalendarIds: hidden });
  };

  const writable = calendars.filter((c) => c.writable);

  return (
    <ScrollView style={styles.root} contentContainerStyle={{ padding: 12, paddingBottom: 40 }}>
      <Section title="내 이름 (일정·일기에 작성자로 표시돼요)">
        <TextInput
          style={styles.input}
          value={name}
          placeholder="예: 남편, 민수"
          placeholderTextColor={colors.faint}
          onChangeText={setName}
          onEndEditing={() => update({ myName: name.trim() })}
          onBlur={() => update({ myName: name.trim() })}
        />
      </Section>

      <Section title="공유 캘린더">
        <Text style={styles.help}>
          새 일정이 기본으로 들어갈 캘린더예요. 배우자와 함께 쓰는 iCloud 캘린더를 고르면 서로의 폰, 애플 캘린더, 위젯, 다른 캘린더 앱에
          모두 바로 표시돼요.
        </Text>
        <View style={styles.wrap}>
          {writable
            .filter((c) => c.id !== settings.diaryCalendarId)
            .map((c) => (
              <Chip
                key={c.id}
                label={c.title}
                color={c.color}
                active={settings.defaultCalendarId === c.id}
                onPress={() => update({ defaultCalendarId: c.id })}
              />
            ))}
        </View>
        <Pressable style={styles.btn} onPress={() => make('shared')} disabled={busy}>
          <Text style={styles.btnText}>＋ "우리 캘린더" 새로 만들기</Text>
        </Pressable>
      </Section>

      <Section title="일기장 캘린더">
        <Text style={styles.help}>일기는 별도 캘린더에 하루 종일 일정 형태로 저장돼요. 이 캘린더도 배우자와 공유하세요.</Text>
        <View style={styles.wrap}>
          {writable.map((c) => (
            <Chip
              key={c.id}
              label={c.title}
              color={c.color}
              active={settings.diaryCalendarId === c.id}
              onPress={() => update({ diaryCalendarId: c.id })}
            />
          ))}
        </View>
        <Pressable style={styles.btn} onPress={() => make('diary')} disabled={busy}>
          <Text style={styles.btnText}>＋ "우리 일기장" 새로 만들기</Text>
        </Pressable>
      </Section>

      <Section title="캘린더 표시">
        {calendars.map((c) => (
          <View key={c.id} style={styles.calRow}>
            <Dot color={c.color} />
            <View style={{ flex: 1 }}>
              <Text style={styles.calTitle}>{c.title}</Text>
              <Text style={styles.calSource}>{c.sourceName}</Text>
            </View>
            <Switch
              value={!settings.hiddenCalendarIds.includes(c.id)}
              onValueChange={() => toggleHidden(c.id)}
              trackColor={{ true: colors.primary }}
            />
          </View>
        ))}
        <Text style={styles.help}>구글 캘린더, 회사 메일(Exchange), 공휴일 캘린더도 아이폰 설정에 계정을 추가하면 여기 함께 보여요.</Text>
      </Section>

      <Section title="배우자와 공유하기 (최초 1회)">
        <Text style={styles.step}>1. 위에서 "우리 캘린더" / "우리 일기장"을 만들어요.</Text>
        <Text style={styles.step}>2. 아이폰 기본 "캘린더" 앱 → 아래 "캘린더" 탭 → 만든 캘린더 옆 ⓘ 를 눌러요.</Text>
        <Text style={styles.step}>3. "사람 추가"에 배우자의 Apple ID(이메일)를 넣고, "편집 허용"을 켜요.</Text>
        <Text style={styles.step}>4. 배우자 폰에 온 초대를 수락하고, 배우자도 이 앱을 설치한 뒤 설정에서 같은 캘린더를 골라요.</Text>
        <Text style={styles.help}>
          그다음부터는 한 명이 등록하면 iCloud로 자동 동기화돼요. 별도 서버나 회원가입이 필요 없어요.
        </Text>
        <Pressable style={styles.linkBtn} onPress={() => Linking.openURL('calshow:')}>
          <Text style={styles.linkText}>캘린더 앱 열기</Text>
        </Pressable>
      </Section>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.surface },
  input: { fontSize: 16, color: colors.text, backgroundColor: colors.surface, borderRadius: 8, padding: 10 },
  help: { fontSize: 13, color: colors.sub, lineHeight: 19, marginBottom: 10 },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 6 },
  btn: { backgroundColor: colors.primarySoft, borderRadius: 10, padding: 12, alignItems: 'center' },
  btnText: { color: colors.primary, fontWeight: '700' },
  calRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 6 },
  calTitle: { fontSize: 15, color: colors.text },
  calSource: { fontSize: 11, color: colors.faint },
  step: { fontSize: 14, color: colors.text, lineHeight: 21, marginBottom: 6 },
  linkBtn: { alignSelf: 'flex-start', borderWidth: 1, borderColor: colors.border, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8 },
  linkText: { fontSize: 13, color: colors.text },
});
