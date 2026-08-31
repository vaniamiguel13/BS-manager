import { notFound } from "next/navigation";
import { db } from "@/lib/db";
import { requireRole } from "@/lib/auth-helpers";
import { formatCents, formatDateTime } from "@/lib/format";
import { StatusSelect } from "../status-select";
import { NoteForm } from "./note-form";

export default async function LeadDetailPage({ params }: { params: Promise<{ id: string }> }) {
  await requireRole("ADMIN", "MANAGER");
  const { id } = await params;

  const lead = await db.lead.findUnique({
    where: { id },
    include: { notes: { include: { author: true }, orderBy: { createdAt: "desc" } }, owner: true },
  });

  if (!lead) {
    notFound();
  }

  return (
    <div className="max-w-2xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">{lead.name}</h1>
          {lead.company && <p className="mt-1 text-sm text-slate-500">{lead.company}</p>}
        </div>
        <StatusSelect leadId={lead.id} status={lead.status} />
      </div>

      <dl className="mt-6 grid grid-cols-2 gap-4 rounded-xl border border-slate-200 bg-white p-5 text-sm">
        <div>
          <dt className="text-slate-500">Email</dt>
          <dd className="font-medium text-slate-900">{lead.email ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Telefone</dt>
          <dd className="font-medium text-slate-900">{lead.phone ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Origem</dt>
          <dd className="font-medium text-slate-900">{lead.source ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Valor estimado</dt>
          <dd className="font-medium text-slate-900">{lead.valueCents != null ? formatCents(lead.valueCents) : "—"}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Responsável</dt>
          <dd className="font-medium text-slate-900">{lead.owner?.name ?? "—"}</dd>
        </div>
      </dl>

      <div className="mt-8">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">Notas</h2>
        <NoteForm leadId={lead.id} />

        <div className="mt-4 space-y-3">
          {lead.notes.map((note) => (
            <div key={note.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm">
              <p className="text-slate-800">{note.content}</p>
              <p className="mt-1 text-xs text-slate-400">
                {note.author?.name ?? "Desconhecido"} · {formatDateTime(note.createdAt)}
              </p>
            </div>
          ))}
          {lead.notes.length === 0 && <p className="text-sm text-slate-500">Ainda não há notas.</p>}
        </div>
      </div>
    </div>
  );
}
