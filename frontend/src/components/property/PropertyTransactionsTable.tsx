import {
  useProperties,
  usePropertyTransactions,
  usePropertyCategories,
  useReassignTransaction,
  useClearTransactionOverride,
} from "../../api/queries";
import { formatCurrency as fmt } from "../../utils/formatting";

export default function PropertyTransactionsTable({
  propertyId,
}: {
  propertyId: string;
}) {
  const { data: properties } = useProperties();
  const { data: cats } = usePropertyCategories();
  const { data, isLoading } = usePropertyTransactions(propertyId, undefined, 200);
  const reassign = useReassignTransaction();
  const clearOverride = useClearTransactionOverride();

  if (isLoading || !data) {
    return (
      <div className="text-xs text-[var(--text-secondary)] px-1 py-3">Loading transactions…</div>
    );
  }

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-lg overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[var(--text-secondary)] text-[11px] uppercase tracking-wider text-left">
            <th className="px-4 py-2.5">Date</th>
            <th className="px-3 py-2.5">Merchant</th>
            <th className="px-3 py-2.5">Category</th>
            <th className="px-3 py-2.5 text-right">Amount</th>
            <th className="px-3 py-2.5">Source</th>
            <th className="px-3 py-2.5">Property</th>
          </tr>
        </thead>
        <tbody>
          {data.transactions.map((tx) => (
            <tr key={tx.id} className="border-t border-[var(--border)] hover:bg-[rgba(0,0,0,0.02)]">
              <td className="px-4 py-2 text-[var(--text-secondary)] whitespace-nowrap">{tx.date}</td>
              <td className="px-3 py-2 text-[var(--text-primary)]">{tx.merchant ?? "—"}</td>
              <td className="px-3 py-2">
                {tx.amount >= 0 ? (
                  <span className="text-[var(--text-secondary)]">{tx.property_category ?? "Rental Income"}</span>
                ) : (
                  <select
                    value={tx.property_category ?? "Other"}
                    onChange={(e) =>
                      reassign.mutate({
                        txId: tx.id,
                        propertyId: tx.property_id,
                        category: e.target.value,
                      })
                    }
                    className="input"
                  >
                    {cats?.expense_categories.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                )}
              </td>
              <td
                className="px-3 py-2 text-right tabular-nums"
                style={{ color: tx.amount >= 0 ? "var(--green)" : "var(--text-primary)" }}
              >
                {fmt(tx.amount)}
              </td>
              <td className="px-3 py-2">
                {tx.property_source === "manual" ? (
                  <button
                    onClick={() => clearOverride.mutate(tx.id)}
                    title="Reset to automatic classification"
                    className="text-[10px] uppercase font-semibold text-[var(--yellow)] hover:underline"
                  >
                    manual ✕
                  </button>
                ) : (
                  <span className="text-[10px] uppercase text-[var(--text-secondary)]">auto</span>
                )}
              </td>
              <td className="px-3 py-2">
                <select
                  value={tx.property_id ?? ""}
                  onChange={(e) =>
                    reassign.mutate({
                      txId: tx.id,
                      propertyId: e.target.value || null,
                      category:
                        e.target.value === ""
                          ? null
                          : tx.amount >= 0
                            ? cats?.income_category ?? "Rental Income"
                            : tx.property_category ?? "Other",
                    })
                  }
                  className="input"
                >
                  <option value="">— exclude —</option>
                  {properties?.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
          {data.transactions.length === 0 && (
            <tr>
              <td colSpan={6} className="px-4 py-6 text-center text-[var(--text-secondary)] text-xs">
                No transactions classified to this property yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
