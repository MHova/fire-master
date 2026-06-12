/**
 * Shared theme constants — FIRE palette colors and Recharts tooltip styles.
 * Extracted from individual page components to eliminate duplication.
 */

/** Chart color palette — warm, muted institutional tones. */
export const CHART_COLORS = [
  "#2e8b6e",
  "#3d6e9e",
  "#a07d1a",
  "#b04a56",
  "#7a6aaa",
  "#2e8494",
  "#b06830",
  "#9e4a7a",
  "#6a6e9e",
  "#2e8a7a",
];

/** Standard Recharts tooltip style — warm light theme. */
export const TOOLTIP_STYLE = {
  contentStyle: {
    background: "rgba(255, 255, 255, 0.95)",
    backdropFilter: "blur(12px)",
    WebkitBackdropFilter: "blur(12px)",
    border: "1px solid #d6ccb8",
    borderRadius: "8px",
    color: "#1a1a1e",
    fontSize: "12px",
    boxShadow: "0 4px 16px rgba(0,0,0,0.1), 0 1px 3px rgba(0,0,0,0.06)",
  },
  itemStyle: { color: "#1a1a1e", fontSize: "12px" },
  labelStyle: { color: "#5c5c6a", fontSize: "11px", marginBottom: "4px" },
};
