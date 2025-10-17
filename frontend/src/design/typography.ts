/**
 * Note Assistant Typography System
 *
 * Type scale, font families, and text styling tokens.
 * Uses system fonts for native feel and optimal performance.
 */

export const typography = {
  // ========================================
  // Font Families
  // ========================================
  fontFamily: {
    sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif',
    serif: 'Georgia, "Times New Roman", serif',
    mono: '"JetBrains Mono", "Fira Code", Consolas, monospace',
  },

  // ========================================
  // Font Sizes (rem-based for accessibility)
  // ========================================
  fontSize: {
    xs: '0.75rem',     // 12px - Metadata, timestamps
    sm: '0.875rem',    // 14px - Labels, secondary text
    base: '1rem',      // 16px - Body text (default)
    lg: '1.125rem',    // 18px - Emphasized text
    xl: '1.25rem',     // 20px - Section headings
    '2xl': '1.5rem',   // 24px - Page titles
    '3xl': '1.875rem', // 30px - Hero text
    '4xl': '2.25rem',  // 36px - Display text
  },

  // ========================================
  // Font Weights
  // ========================================
  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },

  // ========================================
  // Line Heights
  // ========================================
  lineHeight: {
    tight: '1.25',    // Headings, compact UI
    normal: '1.5',    // Body text (optimal readability)
    relaxed: '1.75',  // Long-form content
  },

  // ========================================
  // Letter Spacing
  // ========================================
  letterSpacing: {
    tight: '-0.01em',
    normal: '0',
    wide: '0.025em',
  },
} as const

export type TypographyToken = typeof typography

/**
 * Helper to generate text style object
 *
 * @example
 * textStyle('2xl', 'semibold') // { fontSize: '1.5rem', fontWeight: '600' }
 */
export function textStyle(
  size: keyof typeof typography.fontSize,
  weight: keyof typeof typography.fontWeight = 'normal'
) {
  return {
    fontSize: typography.fontSize[size],
    fontWeight: typography.fontWeight[weight],
  }
}
