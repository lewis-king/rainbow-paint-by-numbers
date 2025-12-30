import React from 'react';
import { View, StyleSheet, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as Haptics from 'expo-haptics';
import { LinearGradient } from 'expo-linear-gradient';

import { colors, rainbowArray, shadows } from '@/theme';

interface HeaderBarProps {
  progress: number;
  onReset: () => void;
}

export function HeaderBar({ progress, onReset }: HeaderBarProps) {
  const insets = useSafeAreaInsets();

  const handleBack = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    router.back();
  };

  const handleReset = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    onReset();
  };

  return (
    <View style={[styles.container, { paddingTop: insets.top + 8 }]}>
      <Pressable
        style={({ pressed }) => [
          styles.iconButton,
          pressed && styles.buttonPressed,
        ]}
        onPress={handleBack}
      >
        <Ionicons name="arrow-back" size={28} color={colors.text.primary} />
      </Pressable>

      <View style={styles.progressContainer}>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFillContainer, { width: `${Math.min(progress, 100)}%` }]}>
            <LinearGradient
              colors={[...rainbowArray]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.progressGradient}
            />
          </View>
        </View>
      </View>

      <Pressable
        style={({ pressed }) => [
          styles.iconButton,
          pressed && styles.buttonPressed,
        ]}
        onPress={handleReset}
      >
        <Ionicons name="refresh" size={28} color={colors.text.primary} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingBottom: 12,
    gap: 12,
  },
  iconButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.backgrounds.elevated,
    justifyContent: 'center',
    alignItems: 'center',
    ...shadows.small,
  },
  buttonPressed: {
    transform: [{ scale: 0.92 }],
    opacity: 0.8,
  },
  progressContainer: {
    flex: 1,
    paddingHorizontal: 8,
  },
  progressTrack: {
    height: 14,
    backgroundColor: colors.backgrounds.elevated,
    borderRadius: 7,
    overflow: 'hidden',
  },
  progressFillContainer: {
    height: '100%',
    borderRadius: 7,
    overflow: 'hidden',
  },
  progressGradient: {
    flex: 1,
  },
});
