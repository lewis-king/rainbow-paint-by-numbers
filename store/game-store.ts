import { create } from 'zustand';
import type { Tool, BrushSize } from '@/types/level';

interface GameState {
  selectedColorIndex: number;
  selectedTool: Tool;
  brushSize: BrushSize;
  progress: number;
  isComplete: boolean;

  setColor: (index: number) => void;
  setTool: (tool: Tool) => void;
  toggleBrushSize: () => void;
  setProgress: (progress: number) => void;
  reset: () => void;
}

export const useGameStore = create<GameState>((set) => ({
  selectedColorIndex: 0,
  selectedTool: 'rainbow',
  brushSize: 'large',
  progress: 0,
  isComplete: false,

  setColor: (index) => set({ selectedColorIndex: index }),

  setTool: (tool) => set({ selectedTool: tool }),

  toggleBrushSize: () => set((state) => ({
    brushSize: state.brushSize === 'large' ? 'medium' : 'large'
  })),

  setProgress: (progress) => set({
    progress,
    isComplete: progress >= 98
  }),

  reset: () => set({
    selectedColorIndex: 0,
    selectedTool: 'rainbow',
    brushSize: 'large',
    progress: 0,
    isComplete: false,
  }),
}));

// Brush radius in pixels (at full resolution)
export const BRUSH_SIZES = {
  large: 28,
  medium: 14,
} as const;
