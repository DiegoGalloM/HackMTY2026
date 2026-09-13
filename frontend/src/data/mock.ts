import { formatBalance, formatMoney } from "../api/format";
import type {
  Account,
  Contact,
  CreditCard,
  Movement,
  QuickAction,
  Service,
  User,
} from "./types";

// Datos de demo. Cuando el backend esté listo, esto se reemplaza por las
// llamadas a FastAPI (ver AGENTS.md) — la forma de los tipos ya coincide.

export const user: User = {
  firstName: "Carlos",
  lastName: "Tabares",
};

export const account: Account = {
  id: "acc_1",
  balance: 0,
  currency: "USD",
  label: "Cuenta de negocio",
  clabe: "012180015739024615",
};

export const creditCard: CreditCard = {
  id: "card_1",
  holder: "CARLOS TABARES",
  brand: "visa",
  issuer: "Capital One",
  number: "4147209388431234",
  last4: "1234",
  expiry: "09/29",
  contactless: true,
};

export const quickActions: QuickAction[] = [
  {
    id: "qa_qr",
    label: "Cobrar con QR",
    caption: "Vende y se registra solo",
    icon: "qr",
    to: "/vender",
  },
  {
    id: "qa_inventory",
    label: "Inventario",
    caption: "Lo que tienes y lo que falta",
    icon: "inventory",
    to: "/inventario",
  },
  {
    id: "qa_assistant",
    label: "Asistente",
    caption: "Pregúntale a tu negocio",
    icon: "assistant",
    to: "/asistente",
  },
  {
    id: "qa_education",
    label: "ONE Education",
    caption: "Ideas para tu negocio",
    icon: "education",
    to: "/educacion",
  },
];

export const movements: Movement[] = [
  {
    id: "mov_1",
    title: "Oxxo Tec de Monterrey",
    category: "Compras",
    amount: -87.5,
    date: "2026-09-11",
  },
  {
    id: "mov_2",
    title: "Transferencia de Diego G.",
    category: "Recibido",
    amount: 450,
    date: "2026-09-10",
  },
  {
    id: "mov_3",
    title: "Spotify Premium",
    category: "Suscripciones",
    amount: -129,
    date: "2026-09-09",
  },
  {
    id: "mov_4",
    title: "Retiro cajero Banorte",
    category: "Efectivo",
    amount: -500,
    date: "2026-09-08",
  },
  {
    id: "mov_5",
    title: "Depósito nómina",
    category: "Ingreso",
    amount: 2400,
    date: "2026-09-05",
  },
];

export const contacts: Contact[] = [
  { id: "ct_1", name: "Diego Gallo", bank: "BBVA", clabeLast4: "8834" },
  { id: "ct_2", name: "Ana Sofía R.", bank: "Banorte", clabeLast4: "1207" },
  { id: "ct_3", name: "Luis Fernando", bank: "Santander", clabeLast4: "6519" },
  { id: "ct_4", name: "Mariana P.", bank: "Nu", clabeLast4: "3348" },
];

export const services: Service[] = [
  {
    id: "sv_1",
    name: "CFE",
    category: "Luz",
    dueDate: "2026-09-18",
    amount: 642.3,
  },
  {
    id: "sv_2",
    name: "Totalplay",
    category: "Internet",
    dueDate: "2026-09-20",
    amount: 599,
  },
  {
    id: "sv_3",
    name: "Telcel",
    category: "Celular",
    dueDate: "2026-09-25",
    amount: 350,
  },
];

/** Cajeros y sucursales cercanas, para la pantalla de Retiros. */
export const atms = [
  { id: "atm_1", name: "Sucursal Valle Oriente", distance: "350 m", fee: 0 },
  { id: "atm_2", name: "Cajero Oxxo Garza Sada", distance: "1.2 km", fee: 12 },
  { id: "atm_3", name: "Plaza Fiesta San Agustín", distance: "2.8 km", fee: 0 },
];

// El formato de dinero vive en api/format.ts (USD, un solo lugar); estos
// alias se conservan para las pantallas de demo que ya los importaban.
export const formatCurrency = formatMoney;
export { formatBalance };

/** Agrupa los dígitos de 4 en 4, como vienen impresos en el plástico. */
export function formatCardNumber(number: string): string {
  return number.replace(/\D/g, "").replace(/(.{4})(?=.)/g, "$1 ");
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("es-MX", {
    day: "numeric",
    month: "short",
  }).format(new Date(`${iso}T12:00:00`));
}
