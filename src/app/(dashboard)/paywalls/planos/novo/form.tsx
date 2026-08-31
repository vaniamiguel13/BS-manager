"use client";

import { useActionState } from "react";
import { createPlanAction } from "../../actions";

export function NewPlanForm() {
  const [state, formAction, pending] = useActionState(createPlanAction, { error: null });

  return (
    <form action={formAction} className="max-w-md space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">Nome do plano</label>
        <input name="name" required className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">Descrição</label>
        <input name="description" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Preço (€)</label>
          <input name="priceCents" type="number" min="0" step="0.01" required className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Periodicidade</label>
          <select name="interval" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
            <option value="MONTHLY">Mensal</option>
            <option value="YEARLY">Anual</option>
          </select>
        </div>
      </div>

      {state.error && <p className="text-sm text-red-600">{state.error}</p>}

      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {pending ? "A guardar..." : "Guardar plano"}
      </button>
    </form>
  );
}
