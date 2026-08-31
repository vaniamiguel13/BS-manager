"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { z } from "zod";
import { db } from "@/lib/db";
import { requireRole } from "@/lib/auth-helpers";
import type { SubscriptionStatus } from "@/generated/prisma";

export type FormState = { error: string | null };

const planSchema = z.object({
  name: z.string().min(1, "Nome obrigatório."),
  description: z.string().optional(),
  priceCents: z.coerce.number().int().positive("O preço tem de ser maior que zero."),
  interval: z.enum(["MONTHLY", "YEARLY"]),
});

export async function createPlanAction(_prev: FormState, formData: FormData): Promise<FormState> {
  await requireRole("ADMIN");

  const parsed = planSchema.safeParse({
    name: formData.get("name"),
    description: formData.get("description") || undefined,
    priceCents: formData.get("priceCents") ? Number(formData.get("priceCents")) * 100 : undefined,
    interval: formData.get("interval"),
  });
  if (!parsed.success) {
    return { error: parsed.error.issues[0]?.message ?? "Dados inválidos." };
  }

  await db.plan.create({ data: parsed.data });
  revalidatePath("/paywalls/planos");
  redirect("/paywalls/planos");
}

export async function togglePlanActiveAction(planId: string, active: boolean) {
  await requireRole("ADMIN");
  await db.plan.update({ where: { id: planId }, data: { active } });
  revalidatePath("/paywalls/planos");
}

const subscriptionSchema = z.object({
  customerName: z.string().min(1, "Nome obrigatório."),
  customerEmail: z.string().email("Email inválido."),
  planId: z.string().min(1, "Escolhe um plano."),
  currentPeriodEnd: z.string().min(1, "Data obrigatória."),
});

export async function createSubscriptionAction(_prev: FormState, formData: FormData): Promise<FormState> {
  await requireRole("ADMIN");

  const parsed = subscriptionSchema.safeParse({
    customerName: formData.get("customerName"),
    customerEmail: formData.get("customerEmail"),
    planId: formData.get("planId"),
    currentPeriodEnd: formData.get("currentPeriodEnd"),
  });
  if (!parsed.success) {
    return { error: parsed.error.issues[0]?.message ?? "Dados inválidos." };
  }

  await db.subscription.create({
    data: {
      customerName: parsed.data.customerName,
      customerEmail: parsed.data.customerEmail,
      planId: parsed.data.planId,
      currentPeriodEnd: new Date(parsed.data.currentPeriodEnd),
    },
  });

  revalidatePath("/paywalls");
  redirect("/paywalls");
}

export async function updateSubscriptionStatusAction(subscriptionId: string, status: SubscriptionStatus) {
  await requireRole("ADMIN");
  await db.subscription.update({
    where: { id: subscriptionId },
    data: {
      status,
      canceledAt: status === "CANCELED" ? new Date() : null,
    },
  });
  revalidatePath("/paywalls");
}
