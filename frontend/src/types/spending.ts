export interface CategoryBreakdownItem {
  category: string;
  parent_category: string;
  amount: number;
  percentage: number;
  transaction_count: number;
}

export interface SpendingAnalysis {
  categories: CategoryBreakdownItem[];
  total_spending: number;
  total_income: number;
  net_savings: number;
  savings_rate: number | null;
  start_date: string;
  end_date: string;
  group_by_parent: boolean;
}

export interface TrendPoint {
  month: string;
  amount: number;
}

export interface CategoryTrend {
  category: string;
  points: TrendPoint[];
  total: number;
}

export interface SpendingTrends {
  categories: CategoryTrend[];
  total_trend: TrendPoint[];
  months: number;
}

export interface RecurringExpense {
  merchant: string;
  category: string;
  average_amount: number;
  frequency: string;
  last_date: string;
  occurrence_count: number;
  estimated_annual: number;
}

export interface RecurringExpensesData {
  expenses: RecurringExpense[];
  total_monthly: number;
  total_annual: number;
}

export interface HeatmapCell {
  month: string;
  category: string;
  amount: number;
}

export interface HeatmapData {
  cells: HeatmapCell[];
  categories: string[];
  months: string[];
}

// ---------------------------------------------------------------------------
//  Spending Tracker types
// ---------------------------------------------------------------------------

export interface TrackerCategoryItem {
  category: string;
  parent_category: string;
  amount: number;
  percentage: number;
  transaction_count: number;
  is_discretionary: boolean;
}

export interface TrackerMonthSummary {
  month: string;
  total: number;
  target: number;
  delta: number;
  daily_average: number;
  status: "under_pace" | "on_pace" | "over_pace";
}

export interface PlannedExclusion {
  event_name: string;
  event_amount: number;
  matched_transaction_id: string;
  matched_amount: number;
  matched_merchant: string | null;
  matched_date: string;
}

export interface TrackerSummary {
  current_month: string;
  start_date: string;
  monthly_target: number;

  spent_so_far: number;
  days_elapsed: number;
  days_remaining: number;
  days_in_month: number;
  daily_average: number;
  projected_total: number;
  budget_remaining: number;
  status: "under_pace" | "on_pace" | "over_pace";

  pre_layoff_avg: number;
  savings_vs_old: number;
  runway_days_added: number;

  categories: TrackerCategoryItem[];
  months: TrackerMonthSummary[];

  exclude_planned: boolean;
  planned_exclusions: PlannedExclusion[];
}

export interface TrackerDailyPoint {
  day: number;
  date: string;
  daily_amount: number;
  cumulative: number;
  target_pace: number;
}

export interface TrackerDailyData {
  month: string;
  days: TrackerDailyPoint[];
  monthly_target: number;
}

export interface TrackerTransaction {
  id: string;
  date: string;
  merchant: string | null;
  amount: number;
  category: string;
  parent_category: string;
  is_discretionary: boolean;
}

export interface TrackerTransactionsData {
  transactions: TrackerTransaction[];
  total_count: number;
  total_amount: number;
}
