export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface Account {
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
}

export interface NetWorthCurrent {
  net_worth: number;
  total_assets: number;
  total_liabilities: number;
  asset_allocation: Record<string, number>;
  liability_allocation: Record<string, number>;
  change_1d: number | null;
  change_30d: number | null;
}

export interface NetWorthHistoryPoint {
  date: string;
  net_worth: number;
  total_assets: number;
  total_liabilities: number;
}

export interface NetWorthHistory {
  points: NetWorthHistoryPoint[];
  range: string;
  interval: string;
}

export interface DashboardSummary {
  net_worth: NetWorthCurrent;
  accounts: Account[];
  last_synced_at: string | null;
  account_count: number;
}

export interface SyncStatus {
  status: string;
  last_sync_at: string | null;
  accounts_synced: number;
  transactions_synced: number;
  snapshots_synced: number;
  error_message: string | null;
  demo_mode?: boolean;
}

export interface SyncTriggerResponse {
  message: string;
  task_id: string | null;
}
