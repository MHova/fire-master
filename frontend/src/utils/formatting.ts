/**
 * Shared formatting utilities for currency, percentages, and chart axes.
 * Extracted from individual page components to eliminate duplication.
 */

/** Format a number as full USD currency (e.g., "$1,234,567"). No decimals. */
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

/** Format a number as compact USD (e.g., "$1.23M", "$456K"). */
export function fmtCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 2,
    }).format(value);
  }
  if (Math.abs(value) >= 1_000) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value);
  }
  return formatCurrency(value);
}

/** Short axis label for charts (e.g., "$1.2M", "$500K", "$100"). */
export function fmtAxis(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value}`;
}

/** Format a decimal as a percentage string (e.g., 0.235 → "23.5%"). */
export function fmtPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
