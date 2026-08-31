import Link from "next/link";
import { db } from "@/lib/db";
import { requireRole } from "@/lib/auth-helpers";
import { formatCents, formatDate } from "@/lib/format";
import { StatCard } from "@/components/stat-card";
import { SubscriptionStatusSelect } from "./subscription-status-select";

export default async function PaywallsPage() {
  await requireRole("ADMIN");

  const subscriptions = await db.subscription.findMany({
    include: { plan: true },
    orderBy: { createdAt: "desc" },
  });

  const activeSubs = subscriptions.filter((s) => s.status === "ACTIVE");
  const mrrCents = activeSubs.reduce((sum, s) => {
    const monthly = s.plan.interval === "YEARLY" ? s.plan.priceCents / 12 : s.plan.priceCents;
    return sum + monthly;
  }, 0);
  const pastDueCount = subscriptions.filter((s) => s.status === "PAST_DUE").length;

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Paywalls</h1>
          <p className="mt-1 text-sm text-slate-500">Planos e subscrições de clientes.</p>
        </div>
        <div className="flex gap-2">
          <Link href="/paywalls/planos" className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100">
            Gerir planos
          </Link>
          <Link href="/paywalls/subscricoes/nova" className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700">
            Nova subscrição
          </Link>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Subscrições ativas" value={String(activeSubs.length)} />
        <StatCard label="Receita mensal recorrente (MRR)" value={formatCents(mrrCents)} />
        <StatCard label="Pagamentos em atraso" value={String(pastDueCount)} />
      </div>

      <div className="mt-6 overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-medium uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Cliente</th>
              <th className="px-4 py-2">Plano</th>
              <th className="px-4 py-2">Renovação</th>
              <th className="px-4 py-2">Estado</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {subscriptions.map((sub) => (
              <tr key={sub.id}>
                <td className="px-4 py-2">
                  <p className="font-medium text-slate-900">{sub.customerName}</p>
                  <p className="text-xs text-slate-500">{sub.customerEmail}</p>
                </td>
                <td className="px-4 py-2">
                  {sub.plan.name} ({formatCents(sub.plan.priceCents)}/{sub.plan.interval === "MONTHLY" ? "mês" : "ano"})
                </td>
                <td className="px-4 py-2">{formatDate(sub.currentPeriodEnd)}</td>
                <td className="px-4 py-2">
                  <SubscriptionStatusSelect subscriptionId={sub.id} status={sub.status} />
                </td>
              </tr>
            ))}
            {subscriptions.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                  Ainda não existem subscrições.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
