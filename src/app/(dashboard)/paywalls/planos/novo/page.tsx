import { requireRole } from "@/lib/auth-helpers";
import { NewPlanForm } from "./form";

export default async function NovoPlanoPage() {
  await requireRole("ADMIN");

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Novo plano</h1>
      <div className="mt-6">
        <NewPlanForm />
      </div>
    </div>
  );
}
