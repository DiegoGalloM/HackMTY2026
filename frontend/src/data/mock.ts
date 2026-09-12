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
  greeting: "Hola Carlos!",
};

export const account: Account = {
  id: "acc_1",
  balance: 3000,
  currency: "MXN",
  label: "Cuenta Monito",
};

export const creditCard: CreditCard = {
  id: "card_1",
  holder: "Monito",
  brand: "visa",
  issuer: "BBVA",
  last4: "4021",
  expiry: "09/29",
  contactless: true,
};

export const quickActions: QuickAction[] = [
  {
    id: "qa_transfer",
    label: "Transferir",
    caption: "A cualquier banco",
    icon: "send",
    to: "/transferencias",
  },
  {
    id: "qa_qr",
    label: "Cobrar con QR",
    caption: "Recibe al instante",
    icon: "qr",
    to: "/transferencias",
  },
  {
    id: "qa_topup",
    label: "Recargas",
    caption: "Tiempo aire",
    icon: "phone",
    to: "/pagos",
  },
  {
    id: "qa_bills",
    label: "Servicios",
    caption: "Luz, agua, internet",
    icon: "receipt",
    to: "/pagos",
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

const currencyFormat = new Intl.NumberFormat("es-MX", {
  style: "currency",
  currency: "MXN",
  minimumFractionDigits: 2,
});

export function formatCurrency(amount: number): string {
  return currencyFormat.format(amount);
}

/** Saldo del header: entero cuando no hay centavos, como en la maqueta. */
export function formatBalance(amount: number): string {
  const hasCents = amount % 1 !== 0;
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    minimumFractionDigits: hasCents ? 2 : 0,
    maximumFractionDigits: hasCents ? 2 : 0,
  }).format(amount);
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("es-MX", {
    day: "numeric",
    month: "short",
  }).format(new Date(`${iso}T12:00:00`));
}
