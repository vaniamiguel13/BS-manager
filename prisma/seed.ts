import bcrypt from "bcryptjs";
import { PrismaClient } from "../src/generated/prisma";

const db = new PrismaClient();

async function hash(password: string) {
  return bcrypt.hash(password, 10);
}

async function main() {
  const adminPassword = await hash("admin123");
  const admin = await db.user.upsert({
    where: { email: "admin@bsmanager.pt" },
    update: {},
    create: {
      email: "admin@bsmanager.pt",
      name: "Admin",
      role: "ADMIN",
      passwordHash: adminPassword,
    },
  });

  await db.user.upsert({
    where: { email: "rh@bsmanager.pt" },
    update: {},
    create: {
      email: "rh@bsmanager.pt",
      name: "Rita RH",
      role: "HR",
      passwordHash: await hash("rh12345"),
    },
  });

  const manager = await db.user.upsert({
    where: { email: "gestor@bsmanager.pt" },
    update: {},
    create: {
      email: "gestor@bsmanager.pt",
      name: "Miguel Gestor",
      role: "MANAGER",
      passwordHash: await hash("gestor123"),
    },
  });

  const employeeUser = await db.user.upsert({
    where: { email: "joana@bsmanager.pt" },
    update: {},
    create: {
      email: "joana@bsmanager.pt",
      name: "Joana Silva",
      role: "EMPLOYEE",
      passwordHash: await hash("colab123"),
    },
  });

  const joana = await db.employee.upsert({
    where: { email: "joana@bsmanager.pt" },
    update: {},
    create: {
      userId: employeeUser.id,
      fullName: "Joana Silva",
      email: "joana@bsmanager.pt",
      jobTitle: "Desenvolvedora",
      department: "Engenharia",
      hireDate: new Date("2024-03-01"),
      salaryCents: 180000,
    },
  });

  await db.employee.upsert({
    where: { email: "carlos@bsmanager.pt" },
    update: {},
    create: {
      fullName: "Carlos Mendes",
      email: "carlos@bsmanager.pt",
      jobTitle: "Vendas",
      department: "Comercial",
      hireDate: new Date("2023-09-15"),
      salaryCents: 150000,
    },
  });

  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayClockOut = new Date(yesterday);
  yesterdayClockOut.setHours(yesterday.getHours() + 8);

  await db.timeEntry.create({
    data: {
      employeeId: joana.id,
      clockIn: yesterday,
      clockOut: yesterdayClockOut,
      status: "APPROVED",
      approvedById: admin.id,
    },
  });

  await db.timeEntry.create({
    data: {
      employeeId: joana.id,
      clockIn: new Date(),
      status: "PENDING",
    },
  });

  const leaveStart = new Date();
  leaveStart.setDate(leaveStart.getDate() + 14);
  const leaveEnd = new Date(leaveStart);
  leaveEnd.setDate(leaveEnd.getDate() + 5);

  await db.leaveRequest.create({
    data: {
      employeeId: joana.id,
      type: "VACATION",
      startDate: leaveStart,
      endDate: leaveEnd,
      reason: "Férias de verão",
    },
  });

  await db.lead.create({
    data: {
      name: "Ana Ferreira",
      company: "Padaria Central",
      email: "ana@padariacentral.pt",
      phone: "912345678",
      source: "Website",
      status: "CONTACTED",
      valueCents: 50000,
      ownerId: manager.id,
      notes: {
        create: [{ authorId: manager.id, content: "Primeiro contacto feito por telefone, aguarda proposta." }],
      },
    },
  });

  await db.lead.create({
    data: {
      name: "Rui Santos",
      company: "Santos & Filhos, Lda",
      email: "rui@santosfilhos.pt",
      source: "Referência",
      status: "NEW",
      valueCents: 120000,
      ownerId: manager.id,
    },
  });

  const planBasic = await db.plan.create({
    data: {
      name: "Básico",
      description: "Plano de entrada",
      priceCents: 990,
      interval: "MONTHLY",
    },
  });

  const planPro = await db.plan.create({
    data: {
      name: "Pro",
      description: "Para equipas em crescimento",
      priceCents: 2990,
      interval: "MONTHLY",
    },
  });

  const periodEnd = new Date();
  periodEnd.setMonth(periodEnd.getMonth() + 1);

  await db.subscription.create({
    data: {
      customerName: "Café Aroma",
      customerEmail: "geral@cafearoma.pt",
      planId: planBasic.id,
      currentPeriodEnd: periodEnd,
    },
  });

  await db.subscription.create({
    data: {
      customerName: "Studio Criativo",
      customerEmail: "hello@studiocriativo.pt",
      planId: planPro.id,
      currentPeriodEnd: periodEnd,
      status: "PAST_DUE",
    },
  });

  const dueDate = new Date();
  dueDate.setDate(dueDate.getDate() + 15);

  await db.invoice.create({
    data: {
      number: "FT 2026/0001",
      customerName: "Café Aroma",
      customerEmail: "geral@cafearoma.pt",
      dueDate,
      status: "PAID",
      paidAt: new Date(),
      items: { create: [{ description: "Subscrição mensal - Básico", quantity: 1, unitPriceCents: 990 }] },
    },
  });

  await db.invoice.create({
    data: {
      number: "FT 2026/0002",
      customerName: "Studio Criativo",
      customerEmail: "hello@studiocriativo.pt",
      dueDate,
      status: "SENT",
      items: { create: [{ description: "Subscrição mensal - Pro", quantity: 1, unitPriceCents: 2990 }] },
    },
  });

  await db.expense.create({
    data: {
      description: "Alojamento do servidor (Vercel + base de dados)",
      category: "Infraestrutura",
      amountCents: 2000,
      date: new Date(),
    },
  });

  await db.expense.create({
    data: {
      description: "Material de escritório",
      category: "Escritório",
      amountCents: 3500,
      date: new Date(),
      paidBy: "Admin",
    },
  });

  console.log("Seed concluído. Contas de demonstração:");
  console.log("  admin@bsmanager.pt / admin123 (Administrador)");
  console.log("  rh@bsmanager.pt / rh12345 (Recursos Humanos)");
  console.log("  gestor@bsmanager.pt / gestor123 (Gestor)");
  console.log("  joana@bsmanager.pt / colab123 (Colaboradora)");
}

main()
  .catch((error) => {
    console.error(error);
    process.exit(1);
  })
  .finally(async () => {
    await db.$disconnect();
  });
