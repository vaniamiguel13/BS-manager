import { db } from "@/lib/db";
import { requireRole } from "@/lib/auth-helpers";
import { NewSubscriptionForm } from "./form";

export default async function NovaSubscricaoPage() {
  await requireRole("ADMIN");
  const plans = await db.plan.findMany({ where: { active: true }, orderBy: { priceCents: "asc" } });

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Nova subscrição</h1>
      <div className="mt-6">
        <NewSubscriptionForm plans={plans} />
      </div>
    </div>
  );
}
