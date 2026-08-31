import { reviewTimeEntryAction } from "./actions";

export function ApprovalButtons({ entryId }: { entryId: string }) {
  const approve = reviewTimeEntryAction.bind(null, entryId, true);
  const reject = reviewTimeEntryAction.bind(null, entryId, false);

  return (
    <div className="flex gap-2">
      <form action={approve}>
        <button type="submit" className="text-xs font-medium text-emerald-600 hover:underline">
          Aprovar
        </button>
      </form>
      <form action={reject}>
        <button type="submit" className="text-xs font-medium text-red-600 hover:underline">
          Rejeitar
        </button>
      </form>
    </div>
  );
}
