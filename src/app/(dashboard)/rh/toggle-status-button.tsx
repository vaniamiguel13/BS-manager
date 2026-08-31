import { updateEmployeeStatusAction } from "./actions";
import type { EmployeeStatus } from "@/generated/prisma";

export function ToggleStatusButton({ employeeId, status }: { employeeId: string; status: EmployeeStatus }) {
  const next = status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
  const action = updateEmployeeStatusAction.bind(null, employeeId, next);

  return (
    <form action={action}>
      <button type="submit" className="text-xs font-medium text-slate-600 hover:underline">
        {status === "ACTIVE" ? "Desativar" : "Reativar"}
      </button>
    </form>
  );
}
