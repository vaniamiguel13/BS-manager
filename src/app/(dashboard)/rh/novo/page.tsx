import { requireRole } from "@/lib/auth-helpers";
import { NewEmployeeForm } from "./form";

export default async function NovoColaboradorPage() {
  await requireRole("ADMIN", "HR");

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Novo colaborador</h1>
      <p className="mt-1 text-sm text-slate-500">Adiciona um novo colaborador à empresa.</p>
      <div className="mt-6">
        <NewEmployeeForm />
      </div>
    </div>
  );
}
