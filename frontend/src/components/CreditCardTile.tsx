import { motion } from "framer-motion";
import CapitalOneLogo, { Swoosh } from "./CapitalOneLogo";
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

/** Chip EMV dorado. */
function Chip() {
  return (
    <span
      aria-hidden
      className="block h-7 w-9 rounded-md bg-linear-140 from-[#e8c877] to-[#b08d3c] ring-1 ring-black/10"
    >
      <span className="mx-auto block h-full w-px bg-black/15" />
    </span>
  );
}

export default function CreditCardTile() {
  return (
    <motion.div
      whileTap={{ scale: 0.98 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className="relative mx-5 aspect-[1.62/1] overflow-hidden rounded-3xl bg-linear-140 from-brand via-navy to-navy p-5 text-white shadow-lg shadow-navy/30"
    >
      {/* El swoosh cruza la tarjeta de lado a lado, sangrado por la derecha —
          es el elemento de diseño del plástico de Capital One. */}
      <Swoosh
        className="pointer-events-none absolute -top-2 -right-14 w-[115%] text-accent-bright/90"
      />
      {/* Velo oscuro sobre el swoosh para que el texto encima siga legible. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-linear-to-t from-navy/70 via-navy/10 to-transparent"
      />

      <div className="relative flex h-full flex-col justify-between">
        <div className="flex items-start justify-between">
          <CapitalOneLogo className="text-lg" withSwoosh={false} />
          {creditCard.contactless && <ContactlessIcon />}
        </div>

        <Chip />

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
