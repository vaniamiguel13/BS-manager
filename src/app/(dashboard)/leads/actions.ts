"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { z } from "zod";
import { db } from "@/lib/db";
import { requireRole, requireUser } from "@/lib/auth-helpers";
import type { LeadStatus } from "@/generated/prisma";

const leadSchema = z.object({
  name: z.string().min(1, "Nome obrigatório."),
  company: z.string().optional(),
  email: z.string().email("Email inválido.").optional().or(z.literal("")),
  phone: z.string().optional(),
  source: z.string().optional(),
  valueCents: z.coerce.number().int().nonnegative().optional(),
});

export type LeadFormState = { error: string | null };

export async function createLeadAction(_prev: LeadFormState, formData: FormData): Promise<LeadFormState> {
  const user = await requireRole("ADMIN", "MANAGER");

  const parsed = leadSchema.safeParse({
    name: formData.get("name"),
    company: formData.get("company") || undefined,
    email: formData.get("email") || undefined,
    phone: formData.get("phone") || undefined,
    source: formData.get("source") || undefined,
    valueCents: formData.get("valueCents") ? Number(formData.get("valueCents")) * 100 : undefined,
  });
  if (!parsed.success) {
    return { error: parsed.error.issues[0]?.message ?? "Dados inválidos." };
  }

  const lead = await db.lead.create({
    data: {
      name: parsed.data.name,
      company: parsed.data.company,
      email: parsed.data.email || undefined,
      phone: parsed.data.phone,
      source: parsed.data.source,
      valueCents: parsed.data.valueCents,
      ownerId: user.id,
    },
  });

  revalidatePath("/leads");
  redirect(`/leads/${lead.id}`);
}

export async function updateLeadStatusAction(leadId: string, status: LeadStatus) {
  await requireRole("ADMIN", "MANAGER");
  await db.lead.update({ where: { id: leadId }, data: { status } });
  revalidatePath("/leads");
  revalidatePath(`/leads/${leadId}`);
}

export async function addLeadNoteAction(leadId: string, _prev: LeadFormState, formData: FormData): Promise<LeadFormState> {
  const user = await requireUser();
  const content = String(formData.get("content") || "").trim();
  if (!content) {
    return { error: "Escreve uma nota." };
  }

  await db.leadNote.create({
    data: { leadId, authorId: user.id, content },
  });
  revalidatePath(`/leads/${leadId}`);
  return { error: null };
}
