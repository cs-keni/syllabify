/**
 * Avatar preset options and helpers. Used by Layout, Profile, and Preferences.
 */
import blueTriangle from '../assets/blue_inverted_triangle.png';
import greenTriangle from '../assets/green_triangle.png';
import pinkSquare from '../assets/pink_square.png';
import purpleHeart from '../assets/purple_heart.png';
import redTriangle from '../assets/red_triangle_king.png';
import yellowDiamond from '../assets/yellow_diamond.png';

export const AVATAR_OPTIONS = [
  { key: 'blue_inverted_triangle', label: 'Blue triangle', src: blueTriangle },
  { key: 'green_triangle', label: 'Green triangle', src: greenTriangle },
  { key: 'pink_square', label: 'Pink square', src: pinkSquare },
  { key: 'purple_heart', label: 'Purple heart', src: purpleHeart },
  { key: 'red_triangle_king', label: 'Red triangle', src: redTriangle },
  { key: 'yellow_diamond', label: 'Yellow diamond', src: yellowDiamond },
];

/**
 * Get display URL for custom avatar (uploaded or pasted URL).
 * Relative paths (e.g. /api/uploads/avatars/...) are resolved against the API base.
 */
export function getAvatarUrl(url) {
  if (!url || typeof url !== 'string') return null;
  const trimmed = url.trim();
  if (!trimmed) return null;
  if (trimmed.startsWith('/')) {
    const base = import.meta.env.VITE_API_URL || 'http://localhost:5000';
    return base.replace(/\/$/, '') + trimmed;
  }
  return trimmed;
}

/**
 * Get avatar option by key (e.g. user.avatar). Returns { key, label, src } or null.
 */
export function getAvatarOption(key) {
  if (!key || typeof key !== 'string') return null;
  return AVATAR_OPTIONS.find(o => o.key === key) || null;
}
