import { useState } from "react";
import { Delete } from "lucide-react";
import Banknote from "./Banknote";
import BottomSheet from "./BottomSheet";
import type { Denomination } from "../data/cash";
import { formatBalance } from "../data/mock";

interface CantidadBilletesSheetProps {
  denomination: Denomination;
  /** Cantidad que ya llevaba contada, para arrancar el teclado con ella. */
  initialCount: number;
  onCancel: () => void;
  onConfirm: (count: number) => void;
}

/** Tope de dígitos: 999 billetes de cualquier denominación ya es absurdo. */
const MAX_DIGITS = 3;

const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "00", "0"] as const;

/**
 * Hoja para capturar de golpe cuántos billetes de una denominación hay, en
 * vez de picarle N veces al billete.
 *
 * Trae teclado propio en vez de un <input type="number">: la app vive dentro
 * del mockup de celular, donde el teclado del sistema no aparece, y en móvil
 * real el teclado nativo taparía la hoja completa.
 */
export default function CantidadBilletesSheet({
  denomination,
  initialCount,
  onCancel,
  onConfirm,
}: CantidadBilletesSheetProps) {
  // Se guarda como string y no como número porque el teclado trabaja por
  // dígitos: "0" y "" se ven igual en pantalla pero se escriben distinto.
  const [digits, setDigits] = useState(
    initialCount > 0 ? String(initialCount) : "",
  );

  const count = Number(digits || 0);

  const press = (key: string) =>
    setDigits((prev) => {
      const next = (prev + key).replace(/^0+(?=\d)/, "");
      return next.length > MAX_DIGITS ? prev : next;
    });

  const backspace = () => setDigits((prev) => prev.slice(0, -1));

  return (
    <BottomSheet
      label={`Cantidad de billetes de ${denomination.value} pesos`}
      onDismiss={onCancel}
    >
      <div className="mt-4 flex items-center gap-3">
        <div className="w-16 shrink-0">
          <Banknote denomination={denomination} />
        </div>
        <div>
          <p className="text-base font-medium">
            Billetes de ${denomination.value}
          </p>
          <p className="text-sm text-muted tabular-nums">
            {formatBalance(count * denomination.value)}
          </p>
        </div>

        <span
          aria-live="polite"
          className="ml-auto text-4xl font-semibold tabular-nums"
        >
          {digits || "0"}
        </span>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-2">
        {KEYS.map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => press(key)}
            className="rounded-2xl bg-tile py-3 text-xl font-medium tabular-nums transition-transform active:scale-95"
          >
            {key}
          </button>
        ))}

        <button
          type="button"
          onClick={backspace}
          aria-label="Borrar un dígito"
          className="flex items-center justify-center rounded-2xl bg-tile py-3 transition-transform active:scale-95"
        >
          <Delete size={22} aria-hidden />
        </button>
      </div>

      <div className="mt-4 flex gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 rounded-full py-3 text-sm font-medium text-muted ring-1 ring-black/10 transition-transform active:scale-[0.98]"
        >
          Cancelar
        </button>
        <button
          type="button"
          onClick={() => onConfirm(count)}
          className="flex-1 rounded-full bg-brand py-3 text-sm font-medium text-white transition-transform active:scale-[0.98]"
        >
          Guardar
        </button>
      </div>
    </BottomSheet>
  );
}
