"use client";

import { useActionState, useState } from "react";
import { createEmployeeAction } from "../actions";

export function NewEmployeeForm() {
  const [state, formAction, pending] = useActionState(createEmployeeAction, { error: null });
  const [createLogin, setCreateLogin] = useState(false);

  return (
    <form action={formAction} className="max-w-xl space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">Nome completo</label>
        <input name="fullName" required className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700">Email</label>
        <input name="email" type="email" required className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Telefone</label>
          <input name="phone" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Data de admissão</label>
          <input name="hireDate" type="date" required className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Cargo</label>
          <input name="jobTitle" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Departamento</label>
          <input name="department" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Salário (€/mês)</label>
          <input name="salaryCents" type="number" min="0" step="0.01" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
        </div>
      </div>

      <div className="rounded-md border border-slate-200 p-4">
        <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
          <input
            type="checkbox"
            name="createLogin"
            checked={createLogin}
            onChange={(e) => setCreateLogin(e.target.checked)}
          />
          Criar conta de acesso à plataforma para este colaborador
        </label>
        {createLogin && (
          <div className="mt-3">
            <label className="mb-1 block text-sm font-medium text-slate-700">Palavra-passe inicial</label>
            <input name="password" type="password" minLength={8} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
            <p className="mt-1 text-xs text-slate-500">O colaborador poderá iniciar sessão com o email indicado acima.</p>
          </div>
        )}
      </div>

      {state.error && <p className="text-sm text-red-600">{state.error}</p>}

      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {pending ? "A guardar..." : "Guardar colaborador"}
      </button>
    </form>
  );
}
