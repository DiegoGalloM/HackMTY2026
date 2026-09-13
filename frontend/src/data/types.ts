export interface User {
  firstName: string;
  lastName: string;
}

export interface Account {
  id: string;
  balance: number;
  currency: "MXN" | "USD";
  /** Cómo se etiqueta la cuenta en la UI ("Cuenta Monito"). */
  label: string;
  /** CLABE interbancaria a 18 dígitos, destino de las fichas de depósito. */
  clabe: string;
}

export interface CreditCard {
  id: string;
  /** Nombre que va impreso en el plástico. */
  holder: string;
  brand: "visa" | "mastercard";
  issuer: string;
  last4: string;
  expiry: string;
  contactless: boolean;
}

/** Acceso rápido del grid 2x2 de la pantalla principal. */
export interface QuickAction {
  id: string;
  label: string;
  caption: string;
  /** Nombre del ícono de lucide-react, resuelto en QuickActionsGrid. */
  icon: "send" | "qr" | "education" | "cash";
  to: string;
}

export interface Movement {
  id: string;
  title: string;
  category: string;
  /** Negativo = cargo, positivo = abono. */
  amount: number;
  date: string;
}

export interface Contact {
  id: string;
  name: string;
  bank: string;
  /** Solo los últimos dígitos de la CLABE, como en una app real. */
  clabeLast4: string;
}

export interface Service {
  id: string;
  name: string;
  category: string;
  dueDate: string;
  amount: number;
}
