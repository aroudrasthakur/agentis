/**
 * JS-facing mirrors of CSS theme tokens (see src/styles/theme.css).
 * Prefer Tailwind/CSS variables in components; use these for SVG/canvas fills.
 */
export const theme = {
  ink: "#edf5f4",
  sand: "#0f1b1d",
  mist: "#162426",
  surface: "#122022",
  surfaceElevated: "#18282a",
  teal: "#168f89",
  tealSoft: "#143a3a",
  tealDeep: "#7ad5cf",
  coral: "#e37863",
  coralSoft: "#3a201c",
  coralDeep: "#e39582",
  bg0: "#071011",
  bg1: "#0a1416",
  bg2: "#0d1719",
} as const;
