import { StatusBar } from 'expo-status-bar';
import React, { useState } from 'react';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import CalendarScreen from './src/screens/CalendarScreen';
import DiaryScreen from './src/screens/DiaryScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import { SettingsProvider } from './src/settings';
import { StoreProvider, useStore } from './src/store';
import { colors } from './src/theme';

type Tab = 'calendar' | 'diary' | 'settings';

const TABS: { key: Tab; icon: string; label: string }[] = [
  { key: 'calendar', icon: '📅', label: '캘린더' },
  { key: 'diary', icon: '📔', label: '일기' },
  { key: 'settings', icon: '⚙️', label: '설정' },
];

function Main() {
  const { permission, requestPermission } = useStore();
  const [tab, setTab] = useState<Tab>('calendar');

  if (permission !== 'granted') {
    return (
      <View style={styles.center}>
        <Text style={{ fontSize: 48, marginBottom: 12 }}>📅</Text>
        <Text style={styles.permTitle}>캘린더 접근 권한이 필요해요</Text>
        <Text style={styles.permText}>
          이 앱은 아이폰 기본 캘린더에 직접 기록해요. 그래서 애플 캘린더, 위젯, 다른 앱과 자동으로 연동돼요.
        </Text>
        {permission === 'denied' ? (
          <Pressable style={styles.permBtn} onPress={() => Linking.openSettings()}>
            <Text style={styles.permBtnText}>설정에서 "전체 접근" 허용하기</Text>
          </Pressable>
        ) : (
          <Pressable style={styles.permBtn} onPress={requestPermission}>
            <Text style={styles.permBtnText}>권한 허용</Text>
          </Pressable>
        )}
      </View>
    );
  }

  return (
    <View style={{ flex: 1 }}>
      <View style={{ flex: 1 }}>
        {tab === 'calendar' && <CalendarScreen />}
        {tab === 'diary' && <DiaryScreen goSettings={() => setTab('settings')} />}
        {tab === 'settings' && <SettingsScreen />}
      </View>
      <View style={styles.tabBar}>
        {TABS.map((t) => (
          <Pressable key={t.key} style={styles.tab} onPress={() => setTab(t.key)}>
            <Text style={[styles.tabIcon, tab !== t.key && { opacity: 0.4 }]}>{t.icon}</Text>
            <Text style={[styles.tabLabel, tab === t.key && { color: colors.primary, fontWeight: '700' }]}>{t.label}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <SettingsProvider>
        <StoreProvider>
          <SafeAreaView style={styles.root} edges={['top', 'bottom']}>
            <StatusBar style="dark" />
            <Main />
          </SafeAreaView>
        </StoreProvider>
      </SettingsProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  tabBar: { flexDirection: 'row', borderTopWidth: StyleSheet.hairlineWidth, borderColor: colors.border, backgroundColor: colors.bg },
  tab: { flex: 1, alignItems: 'center', paddingVertical: 8 },
  tabIcon: { fontSize: 20 },
  tabLabel: { fontSize: 11, color: colors.sub, marginTop: 2 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 30 },
  permTitle: { fontSize: 18, fontWeight: '700', color: colors.text, marginBottom: 8 },
  permText: { fontSize: 14, color: colors.sub, textAlign: 'center', lineHeight: 21, marginBottom: 20 },
  permBtn: { backgroundColor: colors.primary, borderRadius: 10, paddingHorizontal: 20, paddingVertical: 12 },
  permBtnText: { color: '#fff', fontWeight: '700' },
});
