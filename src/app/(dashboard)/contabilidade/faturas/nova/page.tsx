import { requireRole } from "@/lib/auth-helpers";
import { NewInvoiceForm } from "./form";

export default async function NovaFaturaPage() {
  await requireRole("ADMIN");

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Nova fatura</h1>
      <div className="mt-6">
        <NewInvoiceForm />
      </div>
    </div>
  );
}
