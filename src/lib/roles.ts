import type { Role } from "@/generated/prisma";

export const ROLE_LABELS: Record<Role, string> = {
  ADMIN: "Administrador",
  HR: "Recursos Humanos",
  MANAGER: "Gestor",
  EMPLOYEE: "Colaborador",
};
