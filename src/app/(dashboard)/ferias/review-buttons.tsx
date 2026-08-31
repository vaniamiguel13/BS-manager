import { reviewLeaveRequestAction } from "./actions";

export function ReviewButtons({ requestId }: { requestId: string }) {
  const approve = reviewLeaveRequestAction.bind(null, requestId, true);
  const reject = reviewLeaveRequestAction.bind(null, requestId, false);

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
