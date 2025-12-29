export interface NumberLabel {
  number: number;
  x: number;
  y: number;
  color_index: number;
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
