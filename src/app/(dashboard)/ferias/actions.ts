"use server";

import { revalidatePath } from "next/cache";
import { z } from "zod";
import { db } from "@/lib/db";
import { requireRole, requireUser } from "@/lib/auth-helpers";

const requestSchema = z
  .object({
    type: z.enum(["VACATION", "SICK", "OTHER"]),
    startDate: z.string().min(1),
    endDate: z.string().min(1),
    reason: z.string().optional(),
  })
  .refine((data) => new Date(data.endDate) >= new Date(data.startDate), {
    message: "A data de fim tem de ser igual ou posterior à data de início.",
    path: ["endDate"],
  });

export type LeaveFormState = { error: string | null };

export async function createLeaveRequestAction(
  _prev: LeaveFormState,
  formData: FormData,
): Promise<LeaveFormState> {
  const user = await requireUser();
  if (!user.employeeId) {
    return { error: "A tua conta não tem um perfil de colaborador associado." };
  }

  const parsed = requestSchema.safeParse({
    type: formData.get("type"),
    startDate: formData.get("startDate"),
    endDate: formData.get("endDate"),
    reason: formData.get("reason") || undefined,
  });
  if (!parsed.success) {
    return { error: parsed.error.issues[0]?.message ?? "Dados inválidos." };
  }

  await db.leaveRequest.create({
    data: {
      employeeId: user.employeeId,
      type: parsed.data.type,
      startDate: new Date(parsed.data.startDate),
      endDate: new Date(parsed.data.endDate),
      reason: parsed.data.reason,
    },
  });

  revalidatePath("/ferias");
  return { error: null };
}

export async function reviewLeaveRequestAction(requestId: string, approve: boolean) {
  const user = await requireRole("ADMIN", "HR", "MANAGER");

  await db.leaveRequest.update({
    where: { id: requestId },
    data: {
      status: approve ? "APPROVED" : "REJECTED",
      reviewedById: user.id,
    },
  });
  revalidatePath("/ferias");
}
