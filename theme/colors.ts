/**
 * Bold Rainbow Theme - Magical colors for little artists
 */

// Rainbow palette - vibrant, joyful colors
export const rainbow = {
  red: '#FF6B6B',
  orange: '#FFA94D',
  yellow: '#FFE066',
  green: '#69DB7C',
  blue: '#74C0FC',
  indigo: '#9775FA',
  violet: '#DA77F2',
} as const;

// Full rainbow array for gradients and effects
export const rainbowArray = [
  rainbow.red,
  rainbow.orange,
  rainbow.yellow,
  rainbow.green,
  rainbow.blue,
  rainbow.indigo,
  rainbow.violet,
] as const;

// Background colors - dark to make colors pop
export const backgrounds = {
  primary: '#1a1a2e',      // Deep navy - main background
  card: '#2d2d44',         // Slightly lighter - cards
  elevated: '#3d3d5c',     // Buttons, elevated surfaces
  overlay: 'rgba(0, 0, 0, 0.85)', // Modal overlays
} as const;

// Accent colors for interactive states
export const accents = {
  success: '#69DB7C',      // Green from rainbow
  active: '#74C0FC',       // Blue from rainbow
  warning: '#FFA94D',      // Orange from rainbow
  star: '#FFE066',         // Yellow - for stars/celebration
  heart: '#FF6B6B',        // Red - for love/hearts
} as const;

// Text colors
export const text = {
  primary: '#FFFFFF',
  secondary: 'rgba(255, 255, 255, 0.7)',
  onLight: '#333333',
} as const;

// Celebration colors - extra sparkle!
export const celebration = {
  gold: '#FFD700',
  sparkle: '#FFFACD',
  pink: '#FFB6C1',
  mint: '#98FB98',
} as const;

// Combined theme export
export const colors = {
  rainbow,
  rainbowArray,
  backgrounds,
  accents,
  text,
  celebration,
} as const;

export default colors;
