import { togglePlanActiveAction } from "../actions";

export function ToggleActiveButton({ planId, active }: { planId: string; active: boolean }) {
  const action = togglePlanActiveAction.bind(null, planId, !active);

  return (
    <form action={action}>
      <button type="submit" className="text-xs font-medium text-slate-600 hover:underline">
        {active ? "Desativar" : "Ativar"}
      </button>
    </form>
  );
}
