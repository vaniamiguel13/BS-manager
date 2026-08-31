import Link from "next/link";
import { db } from "@/lib/db";
import { requireRole } from "@/lib/auth-helpers";
import { formatCents } from "@/lib/format";
import { Badge } from "@/components/badge";
import { ToggleActiveButton } from "./toggle-active-button";

export default async function PlanosPage() {
  await requireRole("ADMIN");

  const plans = await db.plan.findMany({ orderBy: { priceCents: "asc" } });

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Planos</h1>
          <p className="mt-1 text-sm text-slate-500">Planos disponíveis para os clientes subscreverem.</p>
        </div>
        <Link href="/paywalls/planos/novo" className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700">
          Novo plano
        </Link>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {plans.map((plan) => (
          <div key={plan.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between">
              <p className="font-semibold text-slate-900">{plan.name}</p>
              <Badge color={plan.active ? "green" : "slate"}>{plan.active ? "Ativo" : "Inativo"}</Badge>
            </div>
            <p className="mt-2 text-2xl font-semibold text-slate-900">
              {formatCents(plan.priceCents)}
              <span className="text-sm font-normal text-slate-500">/{plan.interval === "MONTHLY" ? "mês" : "ano"}</span>
            </p>
            {plan.description && <p className="mt-2 text-sm text-slate-500">{plan.description}</p>}
            <div className="mt-3">
              <ToggleActiveButton planId={plan.id} active={plan.active} />
            </div>
          </div>
        ))}
        {plans.length === 0 && <p className="text-sm text-slate-500">Ainda não existem planos.</p>}
      </div>
    </div>
  );
}
