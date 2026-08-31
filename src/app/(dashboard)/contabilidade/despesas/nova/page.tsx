import { requireRole } from "@/lib/auth-helpers";
import { NewExpenseForm } from "./form";

export default async function NovaDespesaPage() {
  await requireRole("ADMIN");

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Nova despesa</h1>
      <div className="mt-6">
        <NewExpenseForm />
      </div>
    </div>
  );
}
