"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import bcrypt from "bcryptjs";
import { z } from "zod";
import { db } from "@/lib/db";
import { requireRole } from "@/lib/auth-helpers";

const employeeSchema = z.object({
  fullName: z.string().min(1, "Nome obrigatório."),
  email: z.string().email("Email inválido."),
  phone: z.string().optional(),
  jobTitle: z.string().optional(),
  department: z.string().optional(),
  hireDate: z.string().min(1, "Data de admissão obrigatória."),
  salaryCents: z.coerce.number().int().nonnegative().optional(),
  createLogin: z.coerce.boolean().optional(),
  password: z.string().optional(),
});

export type EmployeeFormState = { error: string | null };

export async function createEmployeeAction(
  _prev: EmployeeFormState,
  formData: FormData,
): Promise<EmployeeFormState> {
  await requireRole("ADMIN", "HR");

  const parsed = employeeSchema.safeParse({
    fullName: formData.get("fullName"),
    email: formData.get("email"),
    phone: formData.get("phone") || undefined,
    jobTitle: formData.get("jobTitle") || undefined,
    department: formData.get("department") || undefined,
    hireDate: formData.get("hireDate"),
    salaryCents: formData.get("salaryCents") ? Number(formData.get("salaryCents")) * 100 : undefined,
    createLogin: formData.get("createLogin") === "on",
    password: formData.get("password") || undefined,
  });

  if (!parsed.success) {
    return { error: parsed.error.issues[0]?.message ?? "Dados inválidos." };
  }

  if (parsed.data.createLogin && (!parsed.data.password || parsed.data.password.length < 8)) {
    return { error: "A palavra-passe deve ter pelo menos 8 caracteres." };
  }

  const existing = await db.employee.findUnique({ where: { email: parsed.data.email } });
  if (existing) {
    return { error: "Já existe um colaborador com este email." };
  }

  await db.employee.create({
    data: {
      fullName: parsed.data.fullName,
      email: parsed.data.email,
      phone: parsed.data.phone,
      jobTitle: parsed.data.jobTitle,
      department: parsed.data.department,
      hireDate: new Date(parsed.data.hireDate),
      salaryCents: parsed.data.salaryCents,
      ...(parsed.data.createLogin && parsed.data.password
        ? {
            user: {
              create: {
                email: parsed.data.email,
                name: parsed.data.fullName,
                role: "EMPLOYEE",
                passwordHash: await bcrypt.hash(parsed.data.password, 10),
              },
            },
          }
        : {}),
    },
  });

  revalidatePath("/rh");
  redirect("/rh");
}

export async function updateEmployeeStatusAction(employeeId: string, status: "ACTIVE" | "INACTIVE") {
  await requireRole("ADMIN", "HR");
  await db.employee.update({ where: { id: employeeId }, data: { status } });
  revalidatePath("/rh");
}
