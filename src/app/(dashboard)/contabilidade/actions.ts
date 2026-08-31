"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { z } from "zod";
import { db } from "@/lib/db";
import { requireRole } from "@/lib/auth-helpers";
import type { InvoiceStatus } from "@/generated/prisma";

export type FormState = { error: string | null };

async function nextInvoiceNumber() {
  const year = new Date().getFullYear();
  const count = await db.invoice.count({
    where: { number: { startsWith: `FT ${year}/` } },
  });
  return `FT ${year}/${String(count + 1).padStart(4, "0")}`;
}

const invoiceSchema = z.object({
  customerName: z.string().min(1, "Nome do cliente obrigatório."),
  customerEmail: z.string().email("Email inválido.").optional().or(z.literal("")),
  description: z.string().min(1, "Descrição obrigatória."),
  amountCents: z.coerce.number().int().positive("O valor tem de ser maior que zero."),
  dueDate: z.string().min(1, "Data de vencimento obrigatória."),
});

export async function createInvoiceAction(_prev: FormState, formData: FormData): Promise<FormState> {
  await requireRole("ADMIN");

  const parsed = invoiceSchema.safeParse({
    customerName: formData.get("customerName"),
    customerEmail: formData.get("customerEmail") || undefined,
    description: formData.get("description"),
    amountCents: formData.get("amountCents") ? Number(formData.get("amountCents")) * 100 : undefined,
    dueDate: formData.get("dueDate"),
  });
  if (!parsed.success) {
    return { error: parsed.error.issues[0]?.message ?? "Dados inválidos." };
  }

  await db.invoice.create({
    data: {
      number: await nextInvoiceNumber(),
      customerName: parsed.data.customerName,
      customerEmail: parsed.data.customerEmail || undefined,
      dueDate: new Date(parsed.data.dueDate),
      status: "SENT",
      items: {
        create: [{ description: parsed.data.description, quantity: 1, unitPriceCents: parsed.data.amountCents }],
      },
    },
  });

  revalidatePath("/contabilidade");
  redirect("/contabilidade");
}

export async function updateInvoiceStatusAction(invoiceId: string, status: InvoiceStatus) {
  await requireRole("ADMIN");
  await db.invoice.update({
    where: { id: invoiceId },
    data: { status, paidAt: status === "PAID" ? new Date() : null },
  });
  revalidatePath("/contabilidade");
}

const expenseSchema = z.object({
  description: z.string().min(1, "Descrição obrigatória."),
  category: z.string().min(1, "Categoria obrigatória."),
  amountCents: z.coerce.number().int().positive("O valor tem de ser maior que zero."),
  date: z.string().min(1, "Data obrigatória."),
  paidBy: z.string().optional(),
});

export async function createExpenseAction(_prev: FormState, formData: FormData): Promise<FormState> {
  await requireRole("ADMIN");

  const parsed = expenseSchema.safeParse({
    description: formData.get("description"),
    category: formData.get("category"),
    amountCents: formData.get("amountCents") ? Number(formData.get("amountCents")) * 100 : undefined,
    date: formData.get("date"),
    paidBy: formData.get("paidBy") || undefined,
  });
  if (!parsed.success) {
    return { error: parsed.error.issues[0]?.message ?? "Dados inválidos." };
  }

  await db.expense.create({
    data: {
      description: parsed.data.description,
      category: parsed.data.category,
      amountCents: parsed.data.amountCents,
      date: new Date(parsed.data.date),
      paidBy: parsed.data.paidBy,
    },
  });

  revalidatePath("/contabilidade");
  redirect("/contabilidade");
}
