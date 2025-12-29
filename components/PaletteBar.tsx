import React from 'react';
import { View, StyleSheet, ScrollView, Pressable, Text } from 'react-native';
import { useGameStore } from '@/store/game-store';

interface PaletteBarProps {
  palette: string[];
}

const SWATCH_SIZE = 56;

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

export function PaletteBar({ palette }: PaletteBarProps) {
  const { selectedColorIndex, setColor, selectedTool } = useGameStore();

  // Don't show palette for rainbow brush
  if (selectedTool === 'rainbow') {
    return null;
  }

  return (
    <View style={styles.container}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {palette.map((color, index) => {
          const isLight = isLightColor(color);
          const isSelected = selectedColorIndex === index;

          return (
            <Pressable
              key={`${color}-${index}`}
              style={[
                styles.swatch,
                { backgroundColor: color },
                isSelected && styles.selectedSwatch,
              ]}
              onPress={() => setColor(index)}
            >
              <Text
                style={[
                  styles.numberText,
                  { color: isLight ? '#333' : '#fff' },
                ]}
              >
                {index + 1}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#2d2d44',
    paddingVertical: 16,
    borderRadius: 16,
    marginHorizontal: 8,
  },
  scrollContent: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    gap: 10,
  },
  swatch: {
    width: SWATCH_SIZE,
    height: SWATCH_SIZE,
    borderRadius: SWATCH_SIZE / 2,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: 'transparent',
  },
  selectedSwatch: {
    borderColor: '#fff',
    transform: [{ scale: 1.1 }],
  },
  numberText: {
    fontSize: 16,
    fontWeight: 'bold',
  },
});
