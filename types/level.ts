export interface NumberLabel {
  number: number;
  x: number;
  y: number;
  color_index: number;
  size?: number; // font px for a number in a narrow region; 10 when absent
}

export interface LevelDimensions {
  w: number;
  h: number;
}

export interface LevelData {
  id: string;
  palette: string[];
  numbers: NumberLabel[];
  dimensions: LevelDimensions;
  has_reward: boolean;
}

export type Tool = 'bucket' | 'brush' | 'rainbow';
export type BrushSize = 'large' | 'medium';
