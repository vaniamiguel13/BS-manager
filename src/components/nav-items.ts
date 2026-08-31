import type { Role } from "@/generated/prisma";

export type NavItem = {
  href: string;
  label: string;
  roles: Role[];
};

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Início", roles: ["ADMIN", "HR", "MANAGER", "EMPLOYEE"] },
  { href: "/horas", label: "Horas", roles: ["ADMIN", "HR", "MANAGER", "EMPLOYEE"] },
  { href: "/ferias", label: "Férias", roles: ["ADMIN", "HR", "MANAGER", "EMPLOYEE"] },
  { href: "/rh", label: "RH", roles: ["ADMIN", "HR"] },
  { href: "/leads", label: "Leads", roles: ["ADMIN", "MANAGER"] },
  { href: "/paywalls", label: "Paywalls", roles: ["ADMIN"] },
  { href: "/contabilidade", label: "Contabilidade", roles: ["ADMIN"] },
];
