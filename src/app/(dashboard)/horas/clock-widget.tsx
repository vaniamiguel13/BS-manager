"use client";

import { useActionState } from "react";
import { clockInAction, clockOutAction } from "./actions";

type State = { error: string | null };

async function clockIn(_prev: State): Promise<State> {
  try {
    await clockInAction();
    return { error: null };
  } catch (error) {
    return { error: error instanceof Error ? error.message : "Erro desconhecido." };
  }
}

async function clockOut(_prev: State): Promise<State> {
  try {
    await clockOutAction();
    return { error: null };
  } catch (error) {
    return { error: error instanceof Error ? error.message : "Erro desconhecido." };
  }
}

export function ClockWidget({ hasOpenEntry }: { hasOpenEntry: boolean }) {
  const [inState, inAction, inPending] = useActionState(clockIn, { error: null });
  const [outState, outAction, outPending] = useActionState(clockOut, { error: null });

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-500">Registo de ponto</p>
      <div className="mt-3 flex gap-3">
        <form action={inAction}>
          <button
            type="submit"
            disabled={hasOpenEntry || inPending}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            Entrada
          </button>
        </form>
        <form action={outAction}>
          <button
            type="submit"
            disabled={!hasOpenEntry || outPending}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            Saída
          </button>
        </form>
      </div>
      {(inState.error || outState.error) && (
        <p className="mt-2 text-sm text-red-600">{inState.error ?? outState.error}</p>
      )}
    </div>
  );
}
