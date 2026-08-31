"use client";

import { useTransition } from "react";
import { updateSubscriptionStatusAction } from "./actions";
import type { SubscriptionStatus } from "@/generated/prisma";

const OPTIONS: { value: SubscriptionStatus; label: string }[] = [
  { value: "ACTIVE", label: "Ativo" },
  { value: "PAST_DUE", label: "Em atraso" },
  { value: "CANCELED", label: "Cancelado" },
];

export function SubscriptionStatusSelect({ subscriptionId, status }: { subscriptionId: string; status: SubscriptionStatus }) {
  const [pending, startTransition] = useTransition();

  return (
    <select
      value={status}
      disabled={pending}
      onChange={(e) => {
        const next = e.target.value as SubscriptionStatus;
        startTransition(() => {
          updateSubscriptionStatusAction(subscriptionId, next);
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
