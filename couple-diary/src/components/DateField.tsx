import DateTimePicker, { DateTimePickerAndroid } from '@react-native-community/datetimepicker';
import React from 'react';
import { Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { formatDate, formatTime } from '../dates';
import { colors } from '../theme';

type Props = {
  label: string;
  value: Date;
  onChange: (d: Date) => void;
  showTime: boolean;
};

/** iOS: native compact pickers inline. Android: buttons that open the system dialog. */
export default function DateField({ label, value, onChange, showTime }: Props) {
  if (Platform.OS === 'ios') {
    return (
      <View style={styles.row}>
        <Text style={styles.label}>{label}</Text>
        <View style={styles.pickers}>
          <DateTimePicker
            value={value}
            mode={showTime ? 'datetime' : 'date'}
            display="compact"
            locale="ko-KR"
            minuteInterval={5}
            onValueChange={(_, d) => onChange(d)}
          />
        </View>
      </View>
    );
  }

  const open = (mode: 'date' | 'time') =>
    DateTimePickerAndroid.open({
      value,
      mode,
      is24Hour: false,
      onValueChange: (_, d) => onChange(d),
    });

  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.pickers}>
        <Pressable style={styles.btn} onPress={() => open('date')}>
          <Text style={styles.btnText}>{formatDate(value)}</Text>
        </Pressable>
        {showTime && (
          <Pressable style={styles.btn} onPress={() => open('time')}>
            <Text style={styles.btnText}>{formatTime(value)}</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 8 },
  label: { fontSize: 15, color: colors.text },
  pickers: { flexDirection: 'row', gap: 6 },
  btn: { backgroundColor: colors.surface, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6 },
  btnText: { fontSize: 15, color: colors.text },
});
