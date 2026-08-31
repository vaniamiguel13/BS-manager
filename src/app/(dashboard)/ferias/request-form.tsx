"use client";

import { useActionState } from "react";
import { createLeaveRequestAction } from "./actions";

const TYPE_OPTIONS = [
  { value: "VACATION", label: "Férias" },
  { value: "SICK", label: "Doença" },
  { value: "OTHER", label: "Outro" },
];

export function LeaveRequestForm() {
  const [state, formAction, pending] = useActionState(createLeaveRequestAction, { error: null });

  return (
    <form action={formAction} className="grid grid-cols-1 gap-3 sm:grid-cols-4 sm:items-end">
      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">Tipo</label>
        <select name="type" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
          {TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">Início</label>
        <input type="date" name="startDate" required className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">Fim</label>
        <input type="date" name="endDate" required className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </div>
      <div>
        <button
          type="submit"
          disabled={pending}
          className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {pending ? "A enviar..." : "Pedir"}
        </button>
      </div>
      <div className="sm:col-span-4">
        <label className="mb-1 block text-xs font-medium text-slate-600">Motivo (opcional)</label>
        <input name="reason" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
      </div>
      {state.error && <p className="text-sm text-red-600 sm:col-span-4">{state.error}</p>}
    </form>
  );
}
