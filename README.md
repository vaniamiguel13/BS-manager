# BS-manager

Plataforma de gestão unificada para pequenas empresas: registo de horas, RH, leads/CRM, paywalls (planos e subscrições) e contabilidade simples (faturas e despesas).

## Stack

- [Next.js](https://nextjs.org) (App Router) + TypeScript + Tailwind CSS
- [Prisma](https://www.prisma.io) ORM — SQLite em desenvolvimento, Postgres recomendado em produção
- [Auth.js / NextAuth v5](https://authjs.dev) com login por email/palavra-passe e papéis (ADMIN, HR, MANAGER, EMPLOYEE)

## Módulos

- **Horas** — registo de entrada/saída dos colaboradores e aprovação por RH/gestão.
- **Férias** — pedidos de férias/ausências e aprovação.
- **RH** — ficha de colaboradores, criação de contas de acesso à plataforma.
- **Leads** — funil comercial simples (novo → contactado → proposta → ganho/perdido) com notas.
- **Paywalls** — planos e subscrições de clientes, com MRR e alertas de pagamentos em atraso.
- **Contabilidade** — faturação simples e registo de despesas, com resumo de receita/despesa mensal.

> **Nota sobre contabilidade**: este módulo cobre faturação e despesas para uso interno, mas **não é software de faturação certificado** (não emite ficheiros SAF-T nem cumpre os requisitos legais portugueses de faturação certificada). Para faturas a clientes finais, recomenda-se complementar com um programa certificado ou consultar um contabilista.

O acesso a cada módulo é limitado por papel (ver `src/components/nav-items.ts`):

| Papel | Acesso |
|---|---|
| EMPLOYEE | Início, Horas, Férias |
| MANAGER | + Leads |
| HR | + RH |
| ADMIN | Tudo, incluindo Paywalls e Contabilidade |

## Desenvolvimento local

```bash
npm install
cp .env.example .env   # ajusta AUTH_SECRET com `npx auth secret`
npm run db:migrate      # cria a base de dados SQLite local
npm run db:seed         # popula dados de demonstração
npm run dev
```

Abre [http://localhost:3000](http://localhost:3000). Contas de demonstração criadas pelo seed:

| Email | Palavra-passe | Papel |
|---|---|---|
| admin@bsmanager.pt | admin123 | Administrador |
| rh@bsmanager.pt | rh12345 | Recursos Humanos |
| gestor@bsmanager.pt | gestor123 | Gestor |
| joana@bsmanager.pt | colab123 | Colaboradora |

**Muda estas palavras-passe (ou apaga estas contas) antes de usar em produção.**

## Deploy barato (~€20/mês ou menos)

Sugestão de infraestrutura para até ~20 utilizadores:

1. **Base de dados Postgres**: [Neon](https://neon.tech) ou [Supabase](https://supabase.com) — plano gratuito costuma chegar para esta escala; se precisares de mais, ronda os €10-19/mês.
2. **Hosting da aplicação**: [Vercel](https://vercel.com) — plano gratuito (Hobby) para testar, ou €20/mês (Pro) para uso comercial contínuo.
3. Define as variáveis de ambiente no serviço de hosting: `DATABASE_URL` (a connection string do Postgres) e `AUTH_SECRET` (gera com `npx auth secret`).
4. No primeiro deploy, corre `npx prisma migrate deploy` apontado à base de dados de produção (localmente ou via um passo de build) e depois `npx prisma db seed` **apenas se quiseres dados de demonstração** — normalmente não em produção real.

Para mudar de SQLite para Postgres, altera o `datasource` em `prisma/schema.prisma`:

```prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}
```

## Scripts úteis

- `npm run dev` — servidor de desenvolvimento
- `npm run build` — build de produção (gera o Prisma Client e compila o Next.js)
- `npm run db:migrate` — cria/aplica migrações Prisma
- `npm run db:seed` — popula dados de demonstração
- `npm run db:studio` — interface visual para a base de dados
- `npm run lint` — linting
