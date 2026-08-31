"use server";

import { revalidatePath } from "next/cache";
import { db } from "@/lib/db";
import { requireRole, requireUser } from "@/lib/auth-helpers";

async function getOwnEmployeeId() {
  const user = await requireUser();
  if (!user.employeeId) {
    throw new Error("Não existe um perfil de colaborador associado a esta conta.");
  }
  return user.employeeId;
}

export async function clockInAction() {
  const employeeId = await getOwnEmployeeId();

  const openEntry = await db.timeEntry.findFirst({
    where: { employeeId, clockOut: null },
  });
  if (openEntry) {
    throw new Error("Já tens um registo de horas em aberto.");
  }

  await db.timeEntry.create({
    data: { employeeId, clockIn: new Date() },
  });
  revalidatePath("/horas");
}

export async function clockOutAction() {
  const employeeId = await getOwnEmployeeId();

  const openEntry = await db.timeEntry.findFirst({
    where: { employeeId, clockOut: null },
    orderBy: { clockIn: "desc" },
  });
  if (!openEntry) {
    throw new Error("Não existe nenhum registo em aberto.");
  }

  await db.timeEntry.update({
    where: { id: openEntry.id },
    data: { clockOut: new Date() },
  });
  revalidatePath("/horas");
}

export async function reviewTimeEntryAction(entryId: string, approve: boolean) {
  const user = await requireRole("ADMIN", "HR", "MANAGER");

  await db.timeEntry.update({
    where: { id: entryId },
    data: {
      status: approve ? "APPROVED" : "REJECTED",
      approvedById: user.id,
    },
  });
  revalidatePath("/horas");
}
