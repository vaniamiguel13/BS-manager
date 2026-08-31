import Link from "next/link";
import { db } from "@/lib/db";
import { requireRole } from "@/lib/auth-helpers";
import { formatCents, formatDate } from "@/lib/format";
import { StatCard } from "@/components/stat-card";
import { InvoiceStatusSelect } from "./invoice-status-select";

function invoiceTotal(items: { quantity: number; unitPriceCents: number }[]) {
  return items.reduce((sum, item) => sum + item.quantity * item.unitPriceCents, 0);
}

export default async function ContabilidadePage() {
  await requireRole("ADMIN");

  const now = new Date();
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 1);

  const [invoices, expenses] = await Promise.all([
    db.invoice.findMany({ include: { items: true }, orderBy: { issueDate: "desc" } }),
    db.expense.findMany({ orderBy: { date: "desc" } }),
  ]);

  const revenueThisMonth = invoices
    .filter((inv) => inv.status === "PAID" && inv.paidAt && inv.paidAt >= monthStart && inv.paidAt < monthEnd)
    .reduce((sum, inv) => sum + invoiceTotal(inv.items), 0);

  const expensesThisMonth = expenses
    .filter((e) => e.date >= monthStart && e.date < monthEnd)
    .reduce((sum, e) => sum + e.amountCents, 0);

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Contabilidade</h1>
          <p className="mt-1 text-sm text-slate-500">
            Faturação e despesas simples. Não substitui software de faturação certificado (sem SAF-T).
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/contabilidade/despesas/nova" className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100">
            Nova despesa
          </Link>
          <Link href="/contabilidade/faturas/nova" className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700">
            Nova fatura
          </Link>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Receita paga este mês" value={formatCents(revenueThisMonth)} />
        <StatCard label="Despesas este mês" value={formatCents(expensesThisMonth)} />
        <StatCard label="Saldo do mês" value={formatCents(revenueThisMonth - expensesThisMonth)} />
      </div>

      <div className="mt-8">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">Faturas</h2>
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs font-medium uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2">Nº</th>
                <th className="px-4 py-2">Cliente</th>
                <th className="px-4 py-2">Vencimento</th>
                <th className="px-4 py-2">Valor</th>
                <th className="px-4 py-2">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td className="px-4 py-2 font-medium text-slate-900">{inv.number}</td>
                  <td className="px-4 py-2">{inv.customerName}</td>
                  <td className="px-4 py-2">{formatDate(inv.dueDate)}</td>
                  <td className="px-4 py-2">{formatCents(invoiceTotal(inv.items))}</td>
                  <td className="px-4 py-2">
                    <InvoiceStatusSelect invoiceId={inv.id} status={inv.status} />
                  </td>
                </tr>
              ))}
              {invoices.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-slate-500">
                    Ainda não existem faturas.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-8">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">Despesas</h2>
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs font-medium uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2">Descrição</th>
                <th className="px-4 py-2">Categoria</th>
                <th className="px-4 py-2">Data</th>
                <th className="px-4 py-2">Valor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {expenses.map((exp) => (
                <tr key={exp.id}>
                  <td className="px-4 py-2">{exp.description}</td>
                  <td className="px-4 py-2">{exp.category}</td>
                  <td className="px-4 py-2">{formatDate(exp.date)}</td>
                  <td className="px-4 py-2">{formatCents(exp.amountCents)}</td>
                </tr>
              ))}
              {expenses.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                    Ainda não existem despesas.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
