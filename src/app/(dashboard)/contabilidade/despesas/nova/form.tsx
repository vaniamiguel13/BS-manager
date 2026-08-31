"use client";

import { useActionState } from "react";
import { createExpenseAction } from "../../actions";

export function NewExpenseForm() {
  const [state, formAction, pending] = useActionState(createExpenseAction, { error: null });

  return (
    <form action={formAction} className="max-w-md space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">Descrição</label>
        <input name="description" required className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Categoria</label>
          <input name="category" required placeholder="ex: software, escritório" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Valor (€)</label>
          <input name="amountCents" type="number" min="0" step="0.01" required className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Data</label>
          <input name="date" type="date" required className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Pago por (opcional)</label>
          <input name="paidBy" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
        </div>
      </div>

      {state.error && <p className="text-sm text-red-600">{state.error}</p>}

      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {pending ? "A guardar..." : "Registar despesa"}
      </button>
    </form>
  );
}
