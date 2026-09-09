/**
 * Brand Design Tokens & Chart Palettes.
 * Matches InvIQ design language defined in index.css.
 */

export const THEME_COLORS = Object.freeze({
    brandCoral: '#F26A4B',
    charcoalDark: '#1E1E1E',
    charcoalMedium: '#2E2E2E',
    warmMuted: '#7A7268',
    cardBackground: '#F4EFE4',
    appBackground: '#E9E4D8',
    subtleBorder: '#D2CBBB',
    destructive: '#DC2626',
    success: '#10B981',
    warning: '#F59E0B',
});

/**
 * Palette used for Stock Health donut & mono-rounded arcs:
 * 1. Good Health (#1E1E1E - Charcoal Dark)
 * 2. Moderate / Warning (#7A7268 - Warm Muted)
 * 3. Critical / Action Needed (#F26A4B - Coral Accent)
 */
export const STOCK_HEALTH_PALETTE = Object.freeze([
    '#1E1E1E',
    '#7A7268',
    '#F26A4B',
]);

/**
 * Standard palette for multi-category bar charts & volume metrics
 */
export const CATEGORY_VOLUME_PALETTE = Object.freeze([
    '#F26A4B',
    '#1E1E1E',
    '#5E5A52',
    '#A89F8F',
    '#CFC8B8',
]);
