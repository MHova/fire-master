import { type ReactNode } from "react";
import { useAuth } from "../hooks/useAuth";
import { useSyncStatus } from "../api/queries";

const NAV_ITEMS = [
  { label: "Dashboard", path: "/", active: true },
  { label: "Runway", path: "/runway", active: true },
  { label: "Assets", path: "/assets", active: true },
  { label: "Spending", path: "/spending", active: true },
  { label: "Tracker", path: "/tracker", active: true },
  { label: "Transactions", path: "/transactions", active: true },
  { label: "Properties", path: "/properties", active: true },
  { label: "Retirement", path: "/retirement", active: true },
  { label: "Tax Planning", path: "/tax", active: true },
  { label: "Trading", path: "/trading", active: false },
  { label: "Settings", path: "/settings", active: false },
];

export default function Layout({ children }: { children: ReactNode }) {
  const { logout } = useAuth();
  const { data: syncStatus } = useSyncStatus();
  const currentPath = window.location.pathname;

  return (
    <div className="flex min-h-screen w-full">
      {/* Sidebar */}
      <nav className="w-56 shrink-0 border-r border-[var(--border)] bg-[var(--bg-secondary)] flex flex-col">
        <div className="px-5 py-5 border-b border-[var(--border)]">
          <h1 className="text-lg font-semibold tracking-tight text-[var(--text-primary)] flex items-center gap-2">
            <img src="/favicon.svg" alt="" className="w-6 h-6" />
            FIRE Master
          </h1>
        </div>
        <ul className="flex-1 py-2">
          {NAV_ITEMS.map((item) => {
            const isCurrent = item.path === "/" ? currentPath === "/" : currentPath.startsWith(item.path);
            return (
              <li key={item.path}>
                <a
                  href={item.active ? item.path : undefined}
                  className={`block px-5 py-2.5 text-sm ${
                    !item.active
                      ? "text-[var(--text-secondary)] cursor-not-allowed opacity-50"
                      : isCurrent
                        ? "text-[var(--green)] bg-[rgba(0,212,170,0.08)]"
                        : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[rgba(255,255,255,0.03)] transition-colors"
                  }`}
                >
                  {item.label}
                </a>
              </li>
            );
          })}
        </ul>
        <div className="px-5 py-4 border-t border-[var(--border)]">
          <button
            onClick={logout}
            className="text-sm text-[var(--text-secondary)] hover:text-[var(--red)] transition-colors"
          >
            Sign Out
          </button>
        </div>
      </nav>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 border-b border-[var(--border)] bg-[var(--bg-secondary)] flex items-center justify-end px-6 gap-4">
          {syncStatus && (
            <span className="text-xs text-[var(--text-secondary)]">
              Sync: {syncStatus.status}
              {syncStatus.last_sync_at &&
                ` \u00B7 ${new Date(syncStatus.last_sync_at).toLocaleString()}`}
            </span>
          )}
        </header>
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>

      {/* AI Advisor — disabled, Claude Code is the preferred analysis tool */}
      {/* <AdvisorPanel /> */}
    </div>
  );
}
