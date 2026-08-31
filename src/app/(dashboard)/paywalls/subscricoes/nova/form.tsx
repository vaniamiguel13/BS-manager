"use client";

import { useActionState } from "react";
import { createSubscriptionAction } from "../../actions";
import type { Plan } from "@/generated/prisma";
import { formatCents } from "@/lib/format";

export function NewSubscriptionForm({ plans }: { plans: Plan[] }) {
  const [state, formAction, pending] = useActionState(createSubscriptionAction, { error: null });

  return (
    <form action={formAction} className="max-w-md space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">Nome do cliente</label>
        <input name="customerName" required className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">Email do cliente</label>
        <input name="customerEmail" type="email" required className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">Plano</label>
        <select name="planId" required className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
          {plans.map((plan) => (
            <option key={plan.id} value={plan.id}>
              {plan.name} — {formatCents(plan.priceCents)}/{plan.interval === "MONTHLY" ? "mês" : "ano"}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">Próxima renovação</label>
        <input name="currentPeriodEnd" type="date" required className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </div>

      {state.error && <p className="text-sm text-red-600">{state.error}</p>}

      <button
        type="submit"
        disabled={pending || plans.length === 0}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {pending ? "A guardar..." : "Guardar subscrição"}
      </button>
      {plans.length === 0 && <p className="text-xs text-amber-600">Cria primeiro um plano em Paywalls → Gerir planos.</p>}
    </form>
  );
}
