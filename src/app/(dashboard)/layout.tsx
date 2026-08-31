import { requireUser } from "@/lib/auth-helpers";
import { NAV_ITEMS } from "@/components/nav-items";
import { SidebarNav } from "@/components/sidebar-nav";
import { LogoutButton } from "@/components/logout-button";
import { ROLE_LABELS } from "@/lib/roles";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const user = await requireUser();
  const visibleItems = NAV_ITEMS.filter((item) => item.roles.includes(user.role));

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="flex w-60 flex-col border-r border-slate-200 bg-white p-4">
        <div className="mb-6 px-2">
          <p className="text-lg font-semibold text-slate-900">BS-manager</p>
          <p className="text-xs text-slate-500">Plataforma de gestão</p>
        </div>
        <SidebarNav items={visibleItems} />
        <div className="mt-auto border-t border-slate-200 pt-4">
          <p className="px-3 text-sm font-medium text-slate-900">{user.name}</p>
          <p className="px-3 text-xs text-slate-500">{ROLE_LABELS[user.role]}</p>
          <LogoutButton />
        </div>
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
