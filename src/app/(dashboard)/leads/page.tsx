import Link from "next/link";
import { db } from "@/lib/db";
import { requireRole } from "@/lib/auth-helpers";
import { formatCents } from "@/lib/format";
import { StatusSelect } from "./status-select";
import type { LeadStatus } from "@/generated/prisma";

const COLUMNS: { status: LeadStatus; label: string }[] = [
  { status: "NEW", label: "Novo" },
  { status: "CONTACTED", label: "Contactado" },
  { status: "PROPOSAL", label: "Proposta" },
  { status: "WON", label: "Ganho" },
  { status: "LOST", label: "Perdido" },
];

export default async function LeadsPage() {
  await requireRole("ADMIN", "MANAGER");

  const leads = await db.lead.findMany({ orderBy: { updatedAt: "desc" } });

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Leads</h1>
          <p className="mt-1 text-sm text-slate-500">{leads.length} lead(s) no funil.</p>
        </div>
        <Link
          href="/leads/novo"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          Novo lead
        </Link>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-5">
        {COLUMNS.map((col) => {
          const columnLeads = leads.filter((l) => l.status === col.status);
          return (
            <div key={col.status} className="rounded-xl border border-slate-200 bg-white p-3">
              <p className="mb-3 text-xs font-semibold uppercase text-slate-500">
                {col.label} ({columnLeads.length})
              </p>
              <div className="space-y-2">
                {columnLeads.map((lead) => (
                  <div key={lead.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                    <Link href={`/leads/${lead.id}`} className="text-sm font-medium text-slate-900 hover:underline">
                      {lead.name}
                    </Link>
                    {lead.company && <p className="text-xs text-slate-500">{lead.company}</p>}
                    {lead.valueCents != null && (
                      <p className="mt-1 text-xs font-medium text-slate-700">{formatCents(lead.valueCents)}</p>
                    )}
                    <div className="mt-2">
                      <StatusSelect leadId={lead.id} status={lead.status} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
