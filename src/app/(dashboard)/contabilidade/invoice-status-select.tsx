"use client";

import { useTransition } from "react";
import { updateInvoiceStatusAction } from "./actions";
import type { InvoiceStatus } from "@/generated/prisma";

const OPTIONS: { value: InvoiceStatus; label: string }[] = [
  { value: "DRAFT", label: "Rascunho" },
  { value: "SENT", label: "Enviada" },
  { value: "PAID", label: "Paga" },
  { value: "OVERDUE", label: "Em atraso" },
  { value: "CANCELED", label: "Cancelada" },
];

export function InvoiceStatusSelect({ invoiceId, status }: { invoiceId: string; status: InvoiceStatus }) {
  const [pending, startTransition] = useTransition();

  return (
    <select
      value={status}
      disabled={pending}
      onChange={(e) => {
        const next = e.target.value as InvoiceStatus;
        startTransition(() => {
          updateInvoiceStatusAction(invoiceId, next);
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
