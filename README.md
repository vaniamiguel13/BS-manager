# BS-manager

Plataforma de gestão unificada para pequenas empresas: registo de horas, RH, leads/CRM, paywalls (planos e subscrições) e contabilidade simples (faturas e despesas).

## Stack

- [Next.js](https://nextjs.org) (App Router) + TypeScript + Tailwind CSS
- [Prisma](https://www.prisma.io) ORM sobre Postgres (recomendado: [Neon](https://neon.tech), tem plano gratuito)
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

A aplicação usa Postgres (não SQLite), incluindo em desenvolvimento. A forma mais simples de teres uma base de dados sem instalar nada é criar um projeto grátis na [Neon](https://neon.tech) (ver secção de deploy abaixo para o passo a passo de criar o projeto) e usar essa connection string também localmente.

```bash
npm install
cp .env.example .env   # preenche DATABASE_URL e DIRECT_URL (Neon) e gera o AUTH_SECRET
npx auth secret         # gera e insere um AUTH_SECRET seguro no .env
npm run db:migrate      # aplica as migrações à base de dados
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

## Deploy grátis: Vercel (Hobby) + Neon

> **Nota**: o plano gratuito (Hobby) da Vercel é, nos termos de serviço, destinado a uso pessoal/não-comercial. Para uma empresa pequena a testar a plataforma isto é geralmente aceitável, mas convém passar para o plano Pro (~€20/mês) assim que o uso passar a ser regular pela equipa. Também não há garantias de disponibilidade nem backups automáticos num plano gratuito — para dados de RH e horas, isto é um risco a ter em conta.

### 1. Criar a base de dados na Neon

1. Cria conta em [neon.tech](https://neon.tech) e cria um novo projeto (ex: `bsmanager`).
2. No dashboard do projeto, vai a **Connect** → copia as duas connection strings:
   - **Pooled connection** → vai para `DATABASE_URL`
   - **Direct connection** → vai para `DIRECT_URL`
3. Guarda as duas — vais precisar delas tanto localmente como na Vercel.

### 2. Aplicar as migrações

Localmente, com o `.env` preenchido com as connection strings da Neon:

```bash
npm run db:migrate    # cria as tabelas na base de dados Neon
npm run db:seed       # opcional: só se quiseres dados de demonstração
```

### 3. Criar o projeto na Vercel

1. Cria conta em [vercel.com](https://vercel.com) e faz **Import Project** a partir deste repositório GitHub.
2. Framework preset: Next.js (deteta automaticamente).
3. Em **Environment Variables**, adiciona:
   - `DATABASE_URL` — a pooled connection string da Neon
   - `DIRECT_URL` — a direct connection string da Neon
   - `AUTH_SECRET` — gera uma nova com `npx auth secret` (não reutilizes a de desenvolvimento)
4. Clica em **Deploy**. O comando de build (`npm run build`) já corre `prisma generate` automaticamente — não precisas de configurar nada extra.

### 4. Migrações em deploys futuros

Sempre que alterares o `prisma/schema.prisma`, corre `npx prisma migrate dev` localmente para criar a migração, faz commit da pasta `prisma/migrations/` e só depois faz deploy — a Vercel não corre `migrate deploy` automaticamente. Para aplicar migrações pendentes à base de dados de produção sem seres tu a correr localmente, corre `npx prisma migrate deploy` a partir de uma máquina com acesso ao `DATABASE_URL`/`DIRECT_URL` de produção antes ou depois do deploy.

## Scripts úteis

- `npm run dev` — servidor de desenvolvimento
- `npm run build` — build de produção (gera o Prisma Client e compila o Next.js)
- `npm run db:migrate` — cria/aplica migrações Prisma
- `npm run db:seed` — popula dados de demonstração
- `npm run db:studio` — interface visual para a base de dados
- `npm run lint` — linting
