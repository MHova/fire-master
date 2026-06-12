// Single source of truth for account-type display.
//
// API enum values are mixed-case (e.g. "checking", "401k", "roth_ira",
// "VEHICLE", "PRIVATE"). Naive title-casing produces wrong results
// like "Roth Ira" or "VEHICLE", so callers should always look up here.
//
// Color values must be raw hex — the badge styling concatenates "15"/"30"
// onto the value for alpha (e.g. "#3d6e9e15"), and CSS vars do not survive
// that concat ("var(--blue)15" is invalid CSS).

export const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  checking: "Checking",
  savings: "Savings",
  "401k": "401k",
  ira: "IRA",
  roth_ira: "Roth IRA",
  taxable: "Brokerage",
  hsa: "HSA",
  real_estate: "Real Estate",
  crypto: "Crypto",
  CREDIT_CARD: "Credit Card",
  VEHICLE: "Vehicle",
  PRIVATE: "Private",
  other: "Other",
  // Debt-side derived categories (returned in liability_allocation)
  mortgage: "Mortgage",
  auto_loan: "Auto Loan",
};

export const ACCOUNT_TYPE_COLORS: Record<string, string> = {
  "401k": "#3d6e9e",        // blue
  ira: "#3d6e9e",
  roth_ira: "#3d6e9e",
  checking: "#2e8b6e",      // green
  savings: "#2e8b6e",
  hsa: "#06b6d4",
  taxable: "#a07d1a",       // yellow
  real_estate: "#a855f7",
  crypto: "#b06830",
  CREDIT_CARD: "#ef4444",
  VEHICLE: "#64748b",
  PRIVATE: "#7a6aaa",
  other: "#5c5c6a",
};

export function accountTypeLabel(rawType: string): string {
  return ACCOUNT_TYPE_LABELS[rawType] ?? rawType;
}

export function accountTypeColor(rawType: string): string {
  return ACCOUNT_TYPE_COLORS[rawType] ?? "#5c5c6a";
}
