import { db } from "@/lib/db";
import { requireUser } from "@/lib/auth-helpers";
import { StatCard } from "@/components/stat-card";
import { formatCents } from "@/lib/format";

export default async function DashboardHome() {
  const user = await requireUser();
  const isBackOffice = user.role === "ADMIN" || user.role === "HR" || user.role === "MANAGER";

  const [pendingTimeEntries, pendingLeaves] = await Promise.all([
    db.timeEntry.count({ where: { status: "PENDING" } }),
    db.leaveRequest.count({ where: { status: "PENDING" } }),
  ]);

  let employeeCount = 0;
  let openLeads = 0;
  let pipelineValueCents = 0;
  let activeSubscriptions = 0;
  let mrrCents = 0;
  let outstandingInvoicesCents = 0;

  if (isBackOffice) {
    const [employees, leads, subscriptions, invoices] = await Promise.all([
      db.employee.count({ where: { status: "ACTIVE" } }),
      db.lead.findMany({ where: { status: { in: ["NEW", "CONTACTED", "PROPOSAL"] } } }),
      db.subscription.findMany({ where: { status: "ACTIVE" }, include: { plan: true } }),
      db.invoice.findMany({ where: { status: { in: ["SENT", "OVERDUE"] } }, include: { items: true } }),
    ]);

    employeeCount = employees;
    openLeads = leads.length;
    pipelineValueCents = leads.reduce((sum, l) => sum + (l.valueCents ?? 0), 0);
    activeSubscriptions = subscriptions.length;
    mrrCents = subscriptions.reduce((sum, s) => {
      const monthly = s.plan.interval === "YEARLY" ? s.plan.priceCents / 12 : s.plan.priceCents;
      return sum + monthly;
    }, 0);
    outstandingInvoicesCents = invoices.reduce(
      (sum, inv) => sum + inv.items.reduce((s, i) => s + i.unitPriceCents * i.quantity, 0),
      0,
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Olá, {user.name}</h1>
      <p className="mt-1 text-sm text-slate-500">Resumo geral da plataforma.</p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard label="Horas pendentes de aprovação" value={String(pendingTimeEntries)} />
        <StatCard label="Pedidos de férias pendentes" value={String(pendingLeaves)} />
        {isBackOffice && (
          <>
            <StatCard label="Colaboradores ativos" value={String(employeeCount)} />
            <StatCard
              label="Leads em aberto"
              value={String(openLeads)}
              hint={`Valor em pipeline: ${formatCents(pipelineValueCents)}`}
            />
            <StatCard label="Subscrições ativas" value={String(activeSubscriptions)} hint={`MRR: ${formatCents(mrrCents)}`} />
            <StatCard label="Faturas por cobrar" value={formatCents(outstandingInvoicesCents)} />
          </>
        )}
      </div>
    </div>
  );
}
