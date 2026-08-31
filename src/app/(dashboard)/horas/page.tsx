import { db } from "@/lib/db";
import { requireUser } from "@/lib/auth-helpers";
import { formatDateTime } from "@/lib/format";
import { Badge } from "@/components/badge";
import { ClockWidget } from "./clock-widget";
import { ApprovalButtons } from "./approval-buttons";

const STATUS_BADGE = {
  PENDING: { label: "Pendente", color: "yellow" as const },
  APPROVED: { label: "Aprovado", color: "green" as const },
  REJECTED: { label: "Rejeitado", color: "red" as const },
};

function durationLabel(clockIn: Date, clockOut: Date | null) {
  if (!clockOut) return "Em curso";
  const minutes = Math.round((clockOut.getTime() - clockIn.getTime()) / 60000);
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return `${hours}h${rest.toString().padStart(2, "0")}`;
}

export default async function HorasPage() {
  const user = await requireUser();
  const isBackOffice = user.role === "ADMIN" || user.role === "HR" || user.role === "MANAGER";

  const ownEntries = user.employeeId
    ? await db.timeEntry.findMany({
        where: { employeeId: user.employeeId },
        orderBy: { clockIn: "desc" },
        take: 20,
      })
    : [];

  const hasOpenEntry = ownEntries.some((e) => !e.clockOut);

  const pendingEntries = isBackOffice
    ? await db.timeEntry.findMany({
        where: { status: "PENDING" },
        include: { employee: true },
        orderBy: { clockIn: "asc" },
        take: 50,
      })
    : [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Horas</h1>
        <p className="mt-1 text-sm text-slate-500">Regista as tuas entradas e saídas.</p>
      </div>

      {user.employeeId ? (
        <ClockWidget hasOpenEntry={hasOpenEntry} />
      ) : (
        <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-700">
          A tua conta não tem um perfil de colaborador associado, por isso não podes registar horas próprias.
        </p>
      )}

      {ownEntries.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Os teus últimos registos</h2>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-medium uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-2">Entrada</th>
                  <th className="px-4 py-2">Saída</th>
                  <th className="px-4 py-2">Duração</th>
                  <th className="px-4 py-2">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {ownEntries.map((entry) => (
                  <tr key={entry.id}>
                    <td className="px-4 py-2">{formatDateTime(entry.clockIn)}</td>
                    <td className="px-4 py-2">{entry.clockOut ? formatDateTime(entry.clockOut) : "—"}</td>
                    <td className="px-4 py-2">{durationLabel(entry.clockIn, entry.clockOut)}</td>
                    <td className="px-4 py-2">
                      <Badge color={STATUS_BADGE[entry.status].color}>{STATUS_BADGE[entry.status].label}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {isBackOffice && (
        <div>
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Aprovações pendentes</h2>
          {pendingEntries.length === 0 ? (
            <p className="text-sm text-slate-500">Não há registos pendentes.</p>
          ) : (
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs font-medium uppercase text-slate-500">
                  <tr>
                    <th className="px-4 py-2">Colaborador</th>
                    <th className="px-4 py-2">Entrada</th>
                    <th className="px-4 py-2">Saída</th>
                    <th className="px-4 py-2">Duração</th>
                    <th className="px-4 py-2"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {pendingEntries.map((entry) => (
                    <tr key={entry.id}>
                      <td className="px-4 py-2">{entry.employee.fullName}</td>
                      <td className="px-4 py-2">{formatDateTime(entry.clockIn)}</td>
                      <td className="px-4 py-2">{entry.clockOut ? formatDateTime(entry.clockOut) : "—"}</td>
                      <td className="px-4 py-2">{durationLabel(entry.clockIn, entry.clockOut)}</td>
                      <td className="px-4 py-2">
                        <ApprovalButtons entryId={entry.id} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
