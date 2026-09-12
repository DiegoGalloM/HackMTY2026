import { motion } from "framer-motion";
import { creditCard } from "../data/mock";

/** Logo de la marca. Texto con tracking, no imagen — así escala sin assets. */
function BrandMark({ brand }: { brand: "visa" | "mastercard" }) {
  if (brand === "mastercard") {
    return (
      <div className="flex items-center" aria-label="Mastercard">
        <span className="h-6 w-6 rounded-full bg-[#eb001b]/90" />
        <span className="-ml-2.5 h-6 w-6 rounded-full bg-[#f79e1b]/90" />
      </div>
    );
  }
  return (
    <span className="text-xl font-bold italic tracking-tight text-white">
      VISA
    </span>
  );
}

/** Ícono de contactless: arcos concéntricos, como en el plástico real. */
function ContactlessIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      role="img"
      aria-label="Pago sin contacto"
      className="text-white/90"
    >
      <path d="M6 8.5a6 6 0 0 1 0 7" />
      <path d="M10 5.5a11 11 0 0 1 0 13" />
      <path d="M14 3a16 16 0 0 1 0 18" />
    </svg>
  );
}

export default function CreditCardTile() {
  return (
    <motion.div
      whileTap={{ scale: 0.98 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className="relative mx-5 aspect-[1.62/1] overflow-hidden rounded-3xl bg-linear-120 from-brand via-brand to-brand-deep p-5 text-white shadow-lg shadow-brand/25"
    >
      {/* Brillo diagonal que cruza la tarjeta, como en la maqueta. */}
      <div
        aria-hidden
        className="pointer-events-none absolute -top-1/3 -right-1/4 h-[180%] w-2/3 rotate-25 bg-white/10 blur-2xl"
      />

      <div className="relative flex h-full flex-col justify-between">
        <span className="text-xl font-bold tracking-tight">
          {creditCard.issuer}
        </span>

        {creditCard.contactless && <ContactlessIcon />}

        <div className="flex items-end justify-between">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium">{creditCard.holder}</p>
            <p className="mt-0.5 text-xs text-white/70 tabular-nums">
              •••• {creditCard.last4} · {creditCard.expiry}
            </p>
          </div>
          <BrandMark brand={creditCard.brand} />
        </div>
      </div>
    </motion.div>
  );
}
