import { requireRole } from "@/lib/auth-helpers";
import { NewLeadForm } from "./form";

export default async function NovoLeadPage() {
  await requireRole("ADMIN", "MANAGER");

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Novo lead</h1>
      <p className="mt-1 text-sm text-slate-500">Adiciona um novo lead ao funil comercial.</p>
      <div className="mt-6">
        <NewLeadForm />
      </div>
    </div>
  );
}
