import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  useDashboardSummary,
  useNetWorthHistory,
  useTriggerSync,
  useSyncStatus,
} from "../api/queries";
import { fetchJSON } from "../api/client";
import LightweightChart from "../charts/LightweightChart";
import Layout from "../components/Layout";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { formatCurrency } from "../utils/formatting";
import { accountTypeLabel } from "../utils/accountTypes";
import { CHART_COLORS } from "../utils/theme";

const RANGE_OPTIONS = ["30d", "90d", "1y", "3y", "5y", "all"] as const;

// Warm, cautionary palette for debt slices — distinct hues (red, burnt
// orange, amber, wine, purple) so adjacent slices are easy to tell apart
// while still reading as "debt" against the cooler asset palette.
const DEBT_COLORS = ["#b04a56", "#d97706", "#a07d1a", "#9e4a7a", "#7a6aaa"];

function AllocationCard({
  title,
  data,
  palette = CHART_COLORS,
}: {
  title: string;
  data: { name: string; value: number }[];
  palette?: readonly string[];
}) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-[var(--text-secondary)]">
          {title}
        </h3>
        {total > 0 && (
          <span className="text-sm font-mono text-[var(--text-primary)]">
            {formatCurrency(total)}
          </span>
        )}
      </div>
      {data.length > 0 ? (
        <>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                dataKey="value"
                stroke="none"
              >
                {data.map((_, i) => (
                  <Cell key={i} fill={palette[i % palette.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value) => formatCurrency(Number(value))}
                contentStyle={{
                  background: "rgba(255, 255, 255, 0.95)",
                  border: "1px solid #d6ccb8",
                  borderRadius: "8px",
                  color: "#1a1a1e",
                  fontSize: "12px",
                  boxShadow: "0 4px 16px rgba(0,0,0,0.1)",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1.5 mt-2">
            {data.map((item, i) => (
              <div key={item.name} className="flex justify-between text-xs">
                <span className="flex items-center gap-1.5">
                  <span
                    className="w-2 h-2 rounded-full inline-block"
                    style={{ background: palette[i % palette.length] }}
                  />
                  <span className="text-[var(--text-secondary)]">
                    {item.name}
                  </span>
                </span>
                <span className="font-mono text-[var(--text-primary)]">
                  {formatCurrency(item.value)}
                </span>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="flex items-center justify-center h-[200px] text-[var(--text-secondary)] text-sm">
          No data yet
        </div>
      )}
    </div>
  );
}

function formatChange(value: number | null | undefined): {
  text: string;
  color: string;
} {
  if (value == null) return { text: "--", color: "var(--text-secondary)" };
  const sign = value >= 0 ? "+" : "";
  return {
    text: `${sign}${formatCurrency(value)}`,
    color: value >= 0 ? "var(--green)" : "var(--red)",
  };
}

export default function DashboardPage() {
  const [range, setRange] = useState<string>("1y");
  const { data: summary, isLoading } = useDashboardSummary();
  const { data: history } = useNetWorthHistory(range);
  const triggerSync = useTriggerSync();
  const { data: syncStatus } = useSyncStatus();
  const [syncing, setSyncing] = useState(false);
  const queryClient = useQueryClient();

  const handleSync = async () => {
    setSyncing(true);
    triggerSync.mutate(undefined, {
      onSuccess: () => {
        // Poll sync status until completion, then refresh dashboard
        const poll = setInterval(async () => {
          const data = await fetchJSON<{ status: string }>("/api/sync/status");
          if (data.status !== "syncing") {
            clearInterval(poll);
            setSyncing(false);
            queryClient.invalidateQueries({ queryKey: ["dashboard", "summary"] });
            queryClient.invalidateQueries({ queryKey: ["net-worth", "history"] });
            queryClient.invalidateQueries({ queryKey: ["sync", "status"] });
          }
        }, 3000);
      },
      onError: () => setSyncing(false),
    });
  };

  if (isLoading || !summary) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-96 text-[var(--text-secondary)]">
          Loading...
        </div>
      </Layout>
    );
  }

  const { net_worth, accounts } = summary;
  const change1d = formatChange(net_worth.change_1d);
  const change30d = formatChange(net_worth.change_30d);

  // Prepare chart data
  const chartData = (history?.points ?? []).map((p) => ({
    time: p.date,
    value: p.net_worth,
  }));

  // Prepare allocation data for donut charts
  const allocationData = Object.entries(net_worth.asset_allocation)
    .filter(([, value]) => value > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([key, value]) => ({
      name: accountTypeLabel(key),
      value,
    }));

  const liabilityData = Object.entries(net_worth.liability_allocation ?? {})
    .filter(([, value]) => value > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([key, value]) => ({
      name: accountTypeLabel(key),
      value,
    }));

  return (
    <Layout>
      <div className="space-y-6">
        {/* Net Worth Hero */}
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-[var(--text-secondary)] mb-1">
              Net Worth
            </p>
            <h2 className="text-4xl font-bold font-mono tracking-tight text-[var(--text-primary)]">
              {formatCurrency(net_worth.net_worth)}
            </h2>
            <div className="flex gap-4 mt-2 text-sm">
              <span style={{ color: change1d.color }}>
                1D: {change1d.text}
              </span>
              <span style={{ color: change30d.color }}>
                30D: {change30d.text}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {summary.last_synced_at && (
              <span className="text-xs text-[var(--text-secondary)]">
                Last sync:{" "}
                {new Date(summary.last_synced_at).toLocaleString()}
              </span>
            )}
            {syncStatus?.demo_mode ? (
              // Tooltip lives on the SPAN: browsers suppress mouse events on
              // disabled controls, so a title on the button itself never shows.
              <span
                title="Disabled in the demo — the full app syncs your live Monarch Money accounts and transactions automatically. Get it at firemaster.io"
                className="cursor-not-allowed"
              >
                <button
                  disabled
                  className="px-3 py-1.5 text-xs bg-[var(--bg-secondary)] border border-[var(--border)] rounded text-[var(--text-tertiary)] opacity-60 pointer-events-none"
                >
                  Sync Now
                </button>
              </span>
            ) : (
              <button
                onClick={handleSync}
                disabled={syncing || triggerSync.isPending}
                className="px-3 py-1.5 text-xs bg-[var(--bg-secondary)] border border-[var(--border)] rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--blue)] transition-colors disabled:opacity-50"
              >
                {syncing ? "Syncing..." : "Sync Now"}
              </button>
            )}
          </div>
        </div>

        {/* Net Worth Chart */}
        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-[var(--text-secondary)]">
              Net Worth History
            </h3>
            <div className="flex gap-1">
              {RANGE_OPTIONS.map((r) => (
                <button
                  key={r}
                  onClick={() => setRange(r)}
                  className={`px-2.5 py-1 text-xs rounded transition-colors ${
                    range === r
                      ? "bg-[var(--blue)] text-white"
                      : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                  }`}
                >
                  {r.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          {chartData.length > 0 ? (
            <LightweightChart data={chartData} height={350} disableScroll />
          ) : (
            <div className="flex items-center justify-center h-[350px] text-[var(--text-secondary)] text-sm">
              No history data yet. Sync Monarch to populate.
            </div>
          )}
        </div>

        {/* Bottom row: Accounts + Allocation */}
        <div className="grid grid-cols-3 gap-6">
          {/* Account List */}
          <div className="col-span-2 bg-[var(--bg-card)] border border-[var(--border)] rounded-lg p-4">
            <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-3">
              Accounts ({summary.account_count})
            </h3>
            <div className="space-y-1">
              {accounts.map((acct) => (
                <div
                  key={acct.id}
                  className="flex items-center justify-between py-2 px-3 rounded hover:bg-[var(--bg-secondary)] transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        acct.is_asset ? "bg-[var(--green)]" : "bg-[var(--red)]"
                      }`}
                    />
                    <div>
                      <p className="text-sm text-[var(--text-primary)]">
                        {acct.name}
                      </p>
                      <p className="text-xs text-[var(--text-secondary)]">
                        {acct.institution ?? acct.account_type}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`text-sm font-mono ${
                      acct.is_asset
                        ? "text-[var(--text-primary)]"
                        : "text-[var(--red)]"
                    }`}
                  >
                    {acct.is_asset ? "" : "-"}
                    {formatCurrency(Math.abs(acct.balance))}
                  </span>
                </div>
              ))}
              {accounts.length === 0 && (
                <p className="text-sm text-[var(--text-secondary)] text-center py-8">
                  No accounts yet. Sync Monarch to import.
                </p>
              )}
            </div>
          </div>

          {/* Allocation Donuts — assets stacked over debts */}
          <div className="space-y-6">
            <AllocationCard title="Asset Allocation" data={allocationData} />
            <AllocationCard
              title="Debt Allocation"
              data={liabilityData}
              palette={DEBT_COLORS}
            />
          </div>
        </div>
      </div>
    </Layout>
  );
}
