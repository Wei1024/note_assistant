/**
 * Note Assistant Color System
 *
 * A warm, earthy palette designed for calm focus and humanistic interaction.
 * All colors are centralized here for consistency and easy theming.
 */

export const colors = {
  // ========================================
  // Base Palette
  // ========================================
  forestGreen: '#294936',
  softBeige: '#EDE9E0',
  mutedSage: '#9CA89A',
  charcoal: '#343434',
  clayOrange: '#D47A44',

  // ========================================
  // Semantic Tokens - Backgrounds
  // ========================================
  background: {
    primary: '#EDE9E0',      // Main canvas (Soft Beige)
    secondary: '#294936',     // Sidebar/header (Forest Green)
    card: '#FFFFFF',          // Note cards (Pure white)
    hover: '#F5F2ED',         // Hover states (Lighter beige)
  },

  // ========================================
  // Semantic Tokens - Text
  // ========================================
  text: {
    primary: '#343434',       // Body text (Charcoal)
    secondary: '#6B6B6B',     // Secondary text (Mid gray)
    onDark: '#EDE9E0',        // Text on dark backgrounds (Soft Beige)
    muted: '#9CA89A',         // Labels, hints (Muted Sage)
  },

  // ========================================
  // Semantic Tokens - Accents
  // ========================================
  accent: {
    primary: '#D47A44',       // Primary actions (Clay Orange)
    primaryHover: '#C26A34',  // Hover state (Darker orange)
    secondary: '#9CA89A',     // Secondary accents (Muted Sage)
  },

  // ========================================
  // Semantic Tokens - Borders
  // ========================================
  border: {
    default: '#D4CFC4',       // Default borders (Darker beige)
    focus: '#D47A44',         // Focus state (Clay Orange)
    subtle: '#E8E4DB',        // Very light dividers
  },

  // ========================================
  // Dimension Colors (5 Boolean Dimensions)
  // ========================================
  dimension: {
    hasActionItems: '#D47A44',    // Clay Orange - warm urgency
    isSocial: '#6B8E7F',           // Soft blue-green - connection
    isEmotional: '#B87A9A',        // Muted rose - empathy
    isKnowledge: '#294936',        // Forest Green - growth
    isExploratory: '#C9A16B',      // Warm tan - curiosity
  },

  // ========================================
  // Status Colors
  // ========================================
  status: {
    success: '#4A7C59',       // Deeper green
    error: '#C85A54',         // Muted red
    warning: '#D89A4E',       // Warm amber
    info: '#6B8E7F',          // Muted teal
  },
} as const

// Type-safe color access
export type ColorToken = typeof colors

/**
 * Get dimension color by key
 *
 * @example
 * getDimensionColor('hasActionItems') // '#D47A44'
 */
export function getDimensionColor(dimension: keyof typeof colors.dimension): string {
  return colors.dimension[dimension]
}

/**
 * Get readable label for dimension
 *
 * @example
 * getDimensionLabel('hasActionItems') // 'Action'
 */
export function getDimensionLabel(dimension: keyof typeof colors.dimension): string {
  const labels: Record<keyof typeof colors.dimension, string> = {
    hasActionItems: 'Action',
    isSocial: 'Social',
    isEmotional: 'Emotional',
    isKnowledge: 'Knowledge',
    isExploratory: 'Exploratory',
  }
  return labels[dimension]
}
