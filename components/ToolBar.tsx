import React from 'react';
import { View, StyleSheet, Pressable, Text } from 'react-native';
import { Ionicons, MaterialCommunityIcons, Entypo } from '@expo/vector-icons';
import { useGameStore } from '@/store/game-store';
import type { Tool } from '@/types/level';

const TOOL_SIZE = 60;

interface ToolConfig {
  id: Tool;
  icon: React.ReactNode;
  activeColor: string;
}

export function ToolBar() {
  const { selectedTool, setTool, brushSize, toggleBrushSize } = useGameStore();

  const tools: ToolConfig[] = [
    {
      id: 'bucket',
      icon: <Ionicons name="color-fill" size={28} color="#fff" />,
      activeColor: '#4CAF50',
    },
    {
      id: 'brush',
      icon: <MaterialCommunityIcons name="brush" size={28} color="#fff" />,
      activeColor: '#2196F3',
    },
    {
      id: 'rainbow',
      icon: <Entypo name="rainbow" size={28} color="#fff" />,
      activeColor: '#FF9800',
    },
  ];

  const showBrushSize = selectedTool === 'brush' || selectedTool === 'rainbow';

  return (
    <View style={styles.container}>
      <View style={styles.toolsRow}>
        {tools.map((tool) => (
          <Pressable
            key={tool.id}
            style={[
              styles.toolButton,
              selectedTool === tool.id && { backgroundColor: tool.activeColor },
            ]}
            onPress={() => setTool(tool.id)}
          >
            {tool.icon}
          </Pressable>
        ))}

        {showBrushSize && (
          <Pressable
            style={styles.sizeButton}
            onPress={toggleBrushSize}
          >
            <View style={[
              styles.sizeIndicator,
              brushSize === 'large' ? styles.sizeLarge : styles.sizeMedium,
            ]} />
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
    backgroundColor: '#3d3d5c',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#4d4d6c',
  },
  sizeButton: {
    width: TOOL_SIZE,
    height: TOOL_SIZE,
    borderRadius: TOOL_SIZE / 2,
    backgroundColor: '#3d3d5c',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#4d4d6c',
  },
  sizeIndicator: {
    backgroundColor: '#fff',
    borderRadius: 20,
  },
  sizeLarge: {
    width: 24,
    height: 24,
  },
  sizeMedium: {
    width: 16,
    height: 16,
  },
  sizeLabel: {
    color: '#fff',
    fontSize: 10,
    fontWeight: 'bold',
    marginTop: 2,
  },
});
