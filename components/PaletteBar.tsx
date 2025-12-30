import React from 'react';
import { View, StyleSheet, ScrollView, Pressable, Text } from 'react-native';
import Animated, {
  useAnimatedStyle,
  withSpring,
  useSharedValue,
} from 'react-native-reanimated';
import * as Haptics from 'expo-haptics';

import { useGameStore } from '@/store/game-store';
import { colors, fonts, shadows } from '@/theme';

interface PaletteBarProps {
  palette: string[];
}

const SWATCH_SIZE = 58;

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

// Helper to determine if a color is light or dark
function isLightColor(hex: string): boolean {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return false;
  const r = parseInt(result[1], 16);
  const g = parseInt(result[2], 16);
  const b = parseInt(result[3], 16);
  // Using relative luminance formula
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5;
}

function ColorSwatch({
  color,
  index,
  isSelected,
  onPress,
}: {
  color: string;
  index: number;
  isSelected: boolean;
  onPress: () => void;
}) {
  const scale = useSharedValue(isSelected ? 1.15 : 1);
  const isLight = isLightColor(color);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: withSpring(scale.value, { damping: 12, stiffness: 150 }) }],
  }));

  React.useEffect(() => {
    scale.value = isSelected ? 1.15 : 1;
  }, [isSelected]);

  const handlePressIn = () => {
    scale.value = 0.9;
  };

  const handlePressOut = () => {
    scale.value = isSelected ? 1.15 : 1;
  };

  return (
    <AnimatedPressable
      style={[
        styles.swatch,
        { backgroundColor: color },
        isSelected && styles.selectedSwatch,
        animatedStyle,
      ]}
      onPress={onPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
    >
      <Text
        style={[
          styles.numberText,
          { color: isLight ? colors.text.onLight : colors.text.primary },
        ]}
      >
        {index + 1}
      </Text>
    </AnimatedPressable>
  );
}

export function PaletteBar({ palette }: PaletteBarProps) {
  const { selectedColorIndex, setColor, selectedTool } = useGameStore();

  // Don't show palette for rainbow brush
  if (selectedTool === 'rainbow') {
    return null;
  }

  const handleColorPress = (index: number) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setColor(index);
  };

  return (
    <View style={styles.container}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {palette.map((color, index) => (
          <ColorSwatch
            key={`${color}-${index}`}
            color={color}
            index={index}
            isSelected={selectedColorIndex === index}
            onPress={() => handleColorPress(index)}
          />
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.backgrounds.card,
    paddingVertical: 16,
    borderRadius: 20,
    marginHorizontal: 8,
    ...shadows.small,
  },
  scrollContent: {
    paddingHorizontal: 14,
    paddingVertical: 4,
    gap: 12,
  },
  swatch: {
    width: SWATCH_SIZE,
    height: SWATCH_SIZE,
    borderRadius: SWATCH_SIZE / 2,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: 'transparent',
    ...shadows.small,
  },
  selectedSwatch: {
    borderColor: colors.text.primary,
    ...shadows.medium,
  },
  numberText: {
    fontFamily: fonts.bodyBold,
    fontWeight: 'bold' as const,
    fontSize: 16,
  },
});
