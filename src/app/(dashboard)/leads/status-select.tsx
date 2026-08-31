"use client";

import { useTransition } from "react";
import { updateLeadStatusAction } from "./actions";
import type { LeadStatus } from "@/generated/prisma";

const OPTIONS: { value: LeadStatus; label: string }[] = [
  { value: "NEW", label: "Novo" },
  { value: "CONTACTED", label: "Contactado" },
  { value: "PROPOSAL", label: "Proposta" },
  { value: "WON", label: "Ganho" },
  { value: "LOST", label: "Perdido" },
];

export function StatusSelect({ leadId, status }: { leadId: string; status: LeadStatus }) {
  const [pending, startTransition] = useTransition();

  return (
    <select
      value={status}
      disabled={pending}
      onChange={(e) => {
        const next = e.target.value as LeadStatus;
        startTransition(() => {
          updateLeadStatusAction(leadId, next);
        });
      }}
      className="rounded-md border border-slate-300 px-2 py-1 text-xs"
    >
      {OPTIONS.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
