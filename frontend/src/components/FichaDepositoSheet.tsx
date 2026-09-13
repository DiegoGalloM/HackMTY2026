import { useState } from "react";
import { Check, Copy } from "lucide-react";
import BottomSheet from "./BottomSheet";
import type { Denomination } from "../data/cash";
import { account, formatBalance } from "../data/mock";

interface FichaDepositoSheetProps {
  /** Denominaciones con cantidad > 0, ya filtradas por la pantalla. */
  desglose: { denomination: Denomination; count: number }[];
  total: number;
  /** Folio de la ficha. Lo genera la pantalla para que no cambie al re-render. */
  folio: string;
  onAccept: () => void;
}

/** CLABE en bloques de 4, como la imprimen los bancos. */
function formatClabe(clabe: string): string {
  return clabe.replace(/(.{4})/g, "$1 ").trim();
}

/**
 * Ficha de depósito: el resumen del efectivo contado y la cuenta destino,
 * listo para copiarse y mandarse a quien va a hacer el depósito.
 *
 * El texto que se copia es el mismo que se ve en pantalla, en plano — se pega
 * igual en WhatsApp que en la ventanilla.
 */
export default function FichaDepositoSheet({
  desglose,
  total,
  folio,
  onAccept,
}: FichaDepositoSheetProps) {
  // null = todavía no intenta copiar. El navegador puede negar el portapapeles
  // (contexto no seguro, permiso denegado), así que el fallo se avisa.
  const [copied, setCopied] = useState<boolean | null>(null);

  const plainText = [
    "Ficha de depósito",
    `Folio: ${folio}`,
    `Cuenta: ${account.label}`,
    `CLABE: ${account.clabe}`,
    `Monto: ${formatBalance(total)}`,
    "Desglose:",
    ...desglose.map(
      ({ denomination, count }) =>
        `  ${count} x $${denomination.value} = ${formatBalance(count * denomination.value)}`,
    ),
  ].join("\n");

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(plainText);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <BottomSheet label="Ficha de depósito" onDismiss={onAccept}>
      <div className="mt-4">
        <p className="text-base font-medium">Ficha de depósito</p>
        <p className="mt-1 text-sm text-muted">Folio {folio}</p>
      </div>

      <div className="mt-4 rounded-2xl bg-tile p-4">
        <p className="text-xs text-muted">Depositar a</p>
        <p className="mt-0.5 text-base font-medium">{account.label}</p>
        <p className="text-sm tracking-wide text-muted tabular-nums">
          {formatClabe(account.clabe)}
        </p>

        <div className="mt-3 border-t border-black/10 pt-3">
          <p className="text-xs text-muted">Monto</p>
          <p className="text-3xl font-semibold tabular-nums">
            {formatBalance(total)}
          </p>
        </div>
      </div>

      <ul className="mt-4 space-y-1">
        {desglose.map(({ denomination, count }) => (
          <li
            key={denomination.value}
            className="flex justify-between text-sm tabular-nums"
          >
            <span className="text-muted">
              {count} × ${denomination.value}
            </span>
            <span>{formatBalance(count * denomination.value)}</span>
          </li>
        ))}
      </ul>

      <div className="mt-5 flex gap-3">
        <button
          type="button"
          onClick={copy}
          className="flex flex-1 items-center justify-center gap-2 rounded-full py-3 text-sm font-medium ring-1 ring-black/10 transition-transform active:scale-[0.98]"
        >
          {copied ? <Check size={18} aria-hidden /> : <Copy size={18} aria-hidden />}
          {copied === null ? "Copiar" : copied ? "Copiado" : "No se pudo copiar"}
        </button>
        <button
          type="button"
          onClick={onAccept}
          className="flex-1 rounded-full bg-brand py-3 text-sm font-medium text-white transition-transform active:scale-[0.98]"
        >
          Aceptar
        </button>
      </div>

      {/* El estado del copiado también se anuncia, el icono solo no basta. */}
      <p aria-live="polite" className="sr-only">
        {copied === true ? "Ficha copiada al portapapeles" : ""}
        {copied === false ? "No se pudo copiar la ficha" : ""}
      </p>
    </BottomSheet>
  );
}
