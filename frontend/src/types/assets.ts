export interface AccountTile {
  id: string;
  name: string;
  account_type: string;
  institution: string | null;
  balance_cents: number;
  balance: number;
  is_asset: boolean;
  fire_role: string | null;
  tags: string[] | null;
  has_enrichment: boolean;
  value_change_30d: number | null;
}

export interface PhysicalAssetTile {
  id: string;
  name: string;
  asset_category: "real_estate" | "vehicle" | "private_investment";
  subcategory: string | null;
  current_value_cents: number;
  current_value: number;
  equity_cents: number | null;
  equity: number | null;
  fire_role: string | null;
  tags: string[] | null;
  has_notes: boolean;
  value_change_30d: number | null;
}

export interface AssetHubData {
  accounts: AccountTile[];
  physical_assets: PhysicalAssetTile[];
  total_net_worth: number;
  total_assets: number;
  total_liabilities: number;
  total_physical_assets: number;
}

export interface AccountEnrichment {
  notes: string | null;
  tags: string[] | null;
  fire_role: string | null;
  target_balance: number | null;
  target_allocation_pct: number | null;
  strategy: string | null;
  custom_data: Record<string, unknown> | null;
}

export interface AccountDetail {
  id: string;
  external_id: string | null;
  name: string;
  account_type: string;
  institution: string | null;
  balance_cents: number;
  balance: number;
  is_asset: boolean;
  include_in_net_worth: boolean;
  source: string;
  last_synced_at: string | null;
  has_enrichment: boolean;
  // Enrichment fields
  notes: string | null;
  tags: string[] | null;
  fire_role: string | null;
  target_balance: number | null;
  target_allocation_pct: number | null;
  strategy: string | null;
  custom_data: Record<string, unknown> | null;
  // Detail data
  balance_history: Array<{ date: string; balance: number }>;
  recent_transactions: Array<{
    id: string;
    date: string;
    amount: number;
    category: string | null;
    merchant: string | null;
  }>;
}
