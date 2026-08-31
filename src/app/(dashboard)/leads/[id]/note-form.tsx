"use client";

import { useActionState } from "react";
import { addLeadNoteAction, type LeadFormState } from "../actions";

export function NoteForm({ leadId }: { leadId: string }) {
  const action = addLeadNoteAction.bind(null, leadId) as (
    prev: LeadFormState,
    formData: FormData,
  ) => Promise<LeadFormState>;
  const [state, formAction, pending] = useActionState(action, { error: null });

  return (
    <form action={formAction} className="space-y-2">
      <textarea
        name="content"
        required
        rows={3}
        placeholder="Escreve uma nota sobre este lead..."
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
      />
      {state.error && <p className="text-sm text-red-600">{state.error}</p>}
      <button
        type="submit"
        disabled={pending}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {pending ? "A guardar..." : "Adicionar nota"}
      </button>
    </form>
  );
}
