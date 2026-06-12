// Transactions ledger types — the Monarch-like all-transactions browser.
// Money values are signed dollars (positive = income, negative = expense).

export type LedgerType = "all" | "income" | "expense";
export type LedgerClassification = "all" | "unclassified" | "classified";

export interface LedgerTransaction {
  id: string;
  date: string;
  merchant: string | null;
  account_name: string | null;
  category: string | null; // raw Monarch category
  amount: number; // signed dollars
  property_id: string | null;
  property_category: string | null;
  property_source: "rule" | "manual" | "monarch_tag" | null;
  hide_from_reports: boolean;
}

export interface LedgerResponse {
  transactions: LedgerTransaction[];
  total_count: number;
  total_income: number;
  total_expense: number;
}

export interface LedgerFilters {
  q?: string;
  type?: LedgerType;
  classification?: LedgerClassification;
  propertyId?: string | null;
  accountId?: string | null;
  dateFrom?: string | null;
  dateTo?: string | null;
  limit?: number;
  offset?: number;
}
