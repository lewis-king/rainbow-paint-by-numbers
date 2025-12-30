import React from 'react';
import { View, StyleSheet, Pressable, Text } from 'react-native';
import { Ionicons, MaterialCommunityIcons, Entypo } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import Animated, {
  useAnimatedStyle,
  withSpring,
  useSharedValue,
} from 'react-native-reanimated';

import { useGameStore } from '@/store/game-store';
import { colors, fonts, shadows } from '@/theme';
import type { Tool } from '@/types/level';

const TOOL_SIZE = 64;

interface ToolConfig {
  id: Tool;
  icon: React.ReactNode;
  activeColor: string;
  label: string;
}

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

function ToolButton({
  tool,
  isSelected,
  onPress,
}: {
  tool: ToolConfig;
  isSelected: boolean;
  onPress: () => void;
}) {
  const scale = useSharedValue(1);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: withSpring(scale.value, { damping: 12 }) }],
    backgroundColor: isSelected ? tool.activeColor : colors.backgrounds.elevated,
    borderColor: isSelected ? tool.activeColor : colors.backgrounds.card,
  }));

  const handlePressIn = () => {
    scale.value = 0.9;
  };

  const handlePressOut = () => {
    scale.value = 1;
  };

  return (
    <AnimatedPressable
      style={[styles.toolButton, animatedStyle]}
      onPress={onPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
    >
      {tool.icon}
    </AnimatedPressable>
  );
}

export function ToolBar() {
  const { selectedTool, setTool, brushSize, toggleBrushSize } = useGameStore();

  const tools: ToolConfig[] = [
    {
      id: 'bucket',
      icon: <Ionicons name="color-fill" size={28} color={colors.text.primary} />,
      activeColor: colors.rainbow.green,
      label: 'Fill',
    },
    {
      id: 'brush',
      icon: <MaterialCommunityIcons name="brush" size={28} color={colors.text.primary} />,
      activeColor: colors.rainbow.blue,
      label: 'Brush',
    },
    {
      id: 'rainbow',
      icon: <Entypo name="rainbow" size={28} color={colors.text.primary} />,
      activeColor: colors.rainbow.orange,
      label: 'Magic',
    },
  ];

  const showBrushSize = selectedTool === 'brush' || selectedTool === 'rainbow';

  const handleToolPress = (tool: Tool) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setTool(tool);
  };

  const handleSizeToggle = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    toggleBrushSize();
  };

  return (
    <View style={styles.container}>
      <View style={styles.toolsRow}>
        {tools.map((tool) => (
          <ToolButton
            key={tool.id}
            tool={tool}
            isSelected={selectedTool === tool.id}
            onPress={() => handleToolPress(tool.id)}
          />
        ))}

        {showBrushSize && (
          <Pressable
            style={({ pressed }) => [
              styles.sizeButton,
              pressed && styles.buttonPressed,
            ]}
            onPress={handleSizeToggle}
          >
            <View
              style={[
                styles.sizeIndicator,
                brushSize === 'large' ? styles.sizeLarge : styles.sizeMedium,
              ]}
            />
            <Text style={styles.sizeLabel}>
              {brushSize === 'large' ? 'L' : 'M'}
            </Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  toolsRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
  },
  toolButton: {
    width: TOOL_SIZE,
    height: TOOL_SIZE,
    borderRadius: TOOL_SIZE / 2,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    ...shadows.small,
  },
  sizeButton: {
    width: TOOL_SIZE,
    height: TOOL_SIZE,
    borderRadius: TOOL_SIZE / 2,
    backgroundColor: colors.backgrounds.elevated,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    borderColor: colors.backgrounds.card,
    ...shadows.small,
  },
  buttonPressed: {
    transform: [{ scale: 0.92 }],
    opacity: 0.8,
  },
  sizeIndicator: {
    backgroundColor: colors.text.primary,
    borderRadius: 20,
  },
  sizeLarge: {
    width: 26,
    height: 26,
  },
  sizeMedium: {
    width: 16,
    height: 16,
  },
  sizeLabel: {
    fontFamily: fonts.bodyBold,
    fontWeight: 'bold' as const,
    color: colors.text.primary,
    fontSize: 10,
    marginTop: 2,
  },
});
