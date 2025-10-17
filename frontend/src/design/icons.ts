/**
 * Note Assistant Icon System
 *
 * Type-safe icon registry for consistent iconography.
 * Icons are stored as SVGs in /src/assets/icons/
 */

// ========================================
// Icon Name Registry
// ========================================
export const iconNames = [
  'search',         // Magnifying glass
  'graph',          // Network nodes
  'note',           // Document/page
  'capture',        // Pen/pencil
  'close',          // X mark
  'settings',       // Gear
  'person',         // User silhouette
  'tag',            // Label
  'calendar',       // Date
  'link',           // Chain
  'action',         // Checkbox
  'social',         // Speech bubble
  'emotional',      // Heart
  'knowledge',      // Book/lightbulb
  'exploratory',    // Compass
  'arrow-right',    // Arrow pointing right
  'arrow-left',     // Arrow pointing left
  'check',          // Checkmark
  'loading',        // Spinner/loading indicator
] as const

export type IconName = (typeof iconNames)[number]

/**
 * Validate if a string is a valid icon name
 *
 * @example
 * isValidIcon('search') // true
 * isValidIcon('invalid') // false
 */
export function isValidIcon(name: string): name is IconName {
  return iconNames.includes(name as IconName)
}

/**
 * Icon size presets (in pixels)
 */
export const iconSizes = {
  xs: 16,
  sm: 20,
  base: 24,
  lg: 32,
  xl: 48,
} as const

export type IconSize = keyof typeof iconSizes
