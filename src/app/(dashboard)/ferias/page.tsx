import { db } from "@/lib/db";
import { requireUser } from "@/lib/auth-helpers";
import { formatDate } from "@/lib/format";
import { Badge } from "@/components/badge";
import { LeaveRequestForm } from "./request-form";
import { ReviewButtons } from "./review-buttons";

const TYPE_LABEL = { VACATION: "Férias", SICK: "Doença", OTHER: "Outro" };
const STATUS_BADGE = {
  PENDING: { label: "Pendente", color: "yellow" as const },
  APPROVED: { label: "Aprovado", color: "green" as const },
  REJECTED: { label: "Rejeitado", color: "red" as const },
};

export default async function FeriasPage() {
  const user = await requireUser();
  const isBackOffice = user.role === "ADMIN" || user.role === "HR" || user.role === "MANAGER";

  const ownRequests = user.employeeId
    ? await db.leaveRequest.findMany({
        where: { employeeId: user.employeeId },
        orderBy: { createdAt: "desc" },
      })
    : [];

  const pendingRequests = isBackOffice
    ? await db.leaveRequest.findMany({
        where: { status: "PENDING" },
        include: { employee: true },
        orderBy: { createdAt: "asc" },
      })
    : [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Férias e ausências</h1>
        <p className="mt-1 text-sm text-slate-500">Pede férias, baixas ou outras ausências.</p>
      </div>

      {user.employeeId ? (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <LeaveRequestForm />
        </div>
      ) : (
        <p className="rounded-md bg-amber-50 p-3 text-sm text-amber-700">
          A tua conta não tem um perfil de colaborador associado, por isso não podes submeter pedidos.
        </p>
      )}

      {ownRequests.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold text-slate-700">Os teus pedidos</h2>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-medium uppercase text-slate-500">
                <tr>
                  <th className="px-4 py-2">Tipo</th>
                  <th className="px-4 py-2">Início</th>
                  <th className="px-4 py-2">Fim</th>
                  <th className="px-4 py-2">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {ownRequests.map((r) => (
                  <tr key={r.id}>
                    <td className="px-4 py-2">{TYPE_LABEL[r.type]}</td>
                    <td className="px-4 py-2">{formatDate(r.startDate)}</td>
                    <td className="px-4 py-2">{formatDate(r.endDate)}</td>
                    <td className="px-4 py-2">
                      <Badge color={STATUS_BADGE[r.status].color}>{STATUS_BADGE[r.status].label}</Badge>
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
          {pendingRequests.length === 0 ? (
            <p className="text-sm text-slate-500">Não há pedidos pendentes.</p>
          ) : (
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs font-medium uppercase text-slate-500">
                  <tr>
                    <th className="px-4 py-2">Colaborador</th>
                    <th className="px-4 py-2">Tipo</th>
                    <th className="px-4 py-2">Início</th>
                    <th className="px-4 py-2">Fim</th>
                    <th className="px-4 py-2"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {pendingRequests.map((r) => (
                    <tr key={r.id}>
                      <td className="px-4 py-2">{r.employee.fullName}</td>
                      <td className="px-4 py-2">{TYPE_LABEL[r.type]}</td>
                      <td className="px-4 py-2">{formatDate(r.startDate)}</td>
                      <td className="px-4 py-2">{formatDate(r.endDate)}</td>
                      <td className="px-4 py-2">
                        <ReviewButtons requestId={r.id} />
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
