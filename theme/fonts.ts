/**
 * Font configuration for Rainbow Paint by Numbers
 *
 * Fredoka - Playful, bold headers
 * Comfortaa - Friendly, rounded UI text
 */

export const fontAssets = {
  'Fredoka-SemiBold': require('../assets/fonts/Fredoka-SemiBold.ttf'),
  'Comfortaa-Regular': require('../assets/fonts/Comfortaa-Regular.ttf'),
} as const;

export const fonts = {
  // Headers and titles - playful and bold
  heading: 'Fredoka-SemiBold',

  // Body and UI text - friendly and readable
  body: 'Comfortaa-Regular',
  bodyBold: 'Comfortaa-Regular', // Use Regular with fontWeight: 'bold' in styles
} as const;

export const fontSizes = {
  xs: 10,
  sm: 12,
  md: 14,
  lg: 16,
  xl: 20,
  xxl: 28,
  title: 36,
  hero: 48,
} as const;

export default fonts;
