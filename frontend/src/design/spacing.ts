/**
 * Note Assistant Spacing System
 *
 * Spacing scale, border radius, and shadows based on 8px system.
 * Consistent spacing creates visual rhythm and hierarchy.
 */

// ========================================
// Spacing Scale (8px base unit)
// ========================================
export const spacing = {
  0: '0',
  1: '0.25rem',  // 4px  - Tight padding, icon margins
  2: '0.5rem',   // 8px  - Small gaps, compact lists
  3: '0.75rem',  // 12px - Badge padding
  4: '1rem',     // 16px - Standard padding, card spacing
  5: '1.25rem',  // 20px - Medium spacing
  6: '1.5rem',   // 24px - Section spacing
  8: '2rem',     // 32px - Large gaps between sections
  10: '2.5rem',  // 40px - Extra large spacing
  12: '3rem',    // 48px - Page margins
  16: '4rem',    // 64px - Hero spacing
  20: '5rem',    // 80px - Extra spacing
  24: '6rem',    // 96px - Maximum spacing
} as const

// ========================================
// Border Radius
// ========================================
export const borderRadius = {
  none: '0',
  sm: '0.125rem',   // 2px  - Subtle rounding
  base: '0.25rem',  // 4px  - Default buttons, inputs
  md: '0.375rem',   // 6px  - Cards
  lg: '0.5rem',     // 8px  - Large cards, modals
  xl: '0.75rem',    // 12px - Feature cards
  '2xl': '1rem',    // 16px - Hero elements
  full: '9999px',   // Pill shape (circular badges)
} as const

// ========================================
// Box Shadows (using charcoal with opacity)
// ========================================
export const shadows = {
  sm: '0 1px 2px 0 rgba(52, 52, 52, 0.05)',
  base: '0 1px 3px 0 rgba(52, 52, 52, 0.1), 0 1px 2px 0 rgba(52, 52, 52, 0.06)',
  md: '0 4px 6px -1px rgba(52, 52, 52, 0.1), 0 2px 4px -1px rgba(52, 52, 52, 0.06)',
  lg: '0 10px 15px -3px rgba(52, 52, 52, 0.1), 0 4px 6px -2px rgba(52, 52, 52, 0.05)',
  xl: '0 20px 25px -5px rgba(52, 52, 52, 0.1), 0 10px 10px -5px rgba(52, 52, 52, 0.04)',
  none: 'none',
} as const

export type SpacingToken = typeof spacing
export type BorderRadiusToken = typeof borderRadius
export type ShadowToken = typeof shadows

/**
 * Helper to generate padding/margin style
 *
 * @example
 * pad(4) // { padding: '1rem' }
 * pad(4, 6) // { paddingTop: '1rem', paddingBottom: '1.5rem', paddingLeft: '1rem', paddingRight: '1rem' }
 */
export function pad(
  y: keyof typeof spacing,
  x?: keyof typeof spacing
): Record<string, string> {
  if (x === undefined) {
    return { padding: spacing[y] }
  }
  return {
    paddingTop: spacing[y],
    paddingBottom: spacing[y],
    paddingLeft: spacing[x],
    paddingRight: spacing[x],
  }
}

/**
 * Helper to generate margin style
 *
 * @example
 * margin(4) // { margin: '1rem' }
 */
export function margin(size: keyof typeof spacing): Record<string, string> {
  return { margin: spacing[size] }
}
