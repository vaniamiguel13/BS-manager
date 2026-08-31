import Link from "next/link";
import { db } from "@/lib/db";
import { requireRole } from "@/lib/auth-helpers";
import { formatDate, formatCents } from "@/lib/format";
import { Badge } from "@/components/badge";
import { ToggleStatusButton } from "./toggle-status-button";

export default async function RHPage() {
  await requireRole("ADMIN", "HR");

  const employees = await db.employee.findMany({
    orderBy: { fullName: "asc" },
  });

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Recursos Humanos</h1>
          <p className="mt-1 text-sm text-slate-500">{employees.length} colaborador(es) registados.</p>
        </div>
        <Link
          href="/rh/novo"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          Novo colaborador
        </Link>
      </div>

      <div className="mt-6 overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-medium uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Nome</th>
              <th className="px-4 py-2">Cargo</th>
              <th className="px-4 py-2">Departamento</th>
              <th className="px-4 py-2">Admissão</th>
              <th className="px-4 py-2">Salário</th>
              <th className="px-4 py-2">Estado</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {employees.map((emp) => (
              <tr key={emp.id}>
                <td className="px-4 py-2">
                  <p className="font-medium text-slate-900">{emp.fullName}</p>
                  <p className="text-xs text-slate-500">{emp.email}</p>
                </td>
                <td className="px-4 py-2">{emp.jobTitle ?? "—"}</td>
                <td className="px-4 py-2">{emp.department ?? "—"}</td>
                <td className="px-4 py-2">{formatDate(emp.hireDate)}</td>
                <td className="px-4 py-2">{emp.salaryCents ? formatCents(emp.salaryCents) : "—"}</td>
                <td className="px-4 py-2">
                  <Badge color={emp.status === "ACTIVE" ? "green" : "slate"}>
                    {emp.status === "ACTIVE" ? "Ativo" : "Inativo"}
                  </Badge>
                </td>
                <td className="px-4 py-2">
                  <ToggleStatusButton employeeId={emp.id} status={emp.status} />
                </td>
              </tr>
            ))}
            {employees.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-slate-500">
                  Ainda não existem colaboradores.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
