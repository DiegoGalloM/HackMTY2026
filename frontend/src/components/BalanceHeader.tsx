import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { account, formatBalance } from "../data/mock";

interface BalanceHeaderProps {
  /** Nombre capturado en la encuesta, o "Usuario" si se la saltó. */
  firstName: string;
  /** Efectivo real (caja + banco) desde los libros; null mientras carga o sin sesión. */
  balance?: number | null;
  /** Etiqueta bajo el saldo; por defecto la cuenta de demo. */
  label?: string;
}

/** Saldo grande a la izquierda, saludo a la derecha. */
export default function BalanceHeader({ firstName, balance = null, label }: BalanceHeaderProps) {
  const [visible, setVisible] = useState(true);
  const amount = balance ?? account.balance;

  return (
    <header className="flex items-start justify-between gap-4 px-5 pt-12 pb-5">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h1 className="truncate text-4xl font-semibold tracking-tight tabular-nums">
            {visible ? formatBalance(amount) : "$•••••"}
          </h1>
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            aria-label={visible ? "Ocultar saldo" : "Mostrar saldo"}
            aria-pressed={!visible}
            className="shrink-0 rounded-full p-1.5 text-muted transition-colors hover:bg-tile active:bg-tile"
          >
            {visible ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
        <p className="mt-1 truncate text-sm text-muted">{label ?? account.label}</p>
      </div>

      <p className="shrink-0 pt-2 text-base font-semibold">Hola {firstName}!</p>
    </header>
  );
}
