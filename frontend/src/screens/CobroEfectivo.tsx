import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Plus, Trash2 } from "lucide-react";
import Banknote from "../components/Banknote";
import CantidadBilletesSheet from "../components/CantidadBilletesSheet";
import FichaDepositoSheet from "../components/FichaDepositoSheet";
import Screen from "../components/Screen";
import { denominations } from "../data/cash";
import { formatBalance } from "../data/mock";

/** Cuántos billetes lleva contados de cada denominación. */
type Counts = Record<number, number>;

/** Cuánto hay que dejar picado el billete para que abra la captura manual. */
const LONG_PRESS_MS = 450;

/**
 * Folio de la ficha: fecha + 4 dígitos. Es de demo — cuando exista el backend
 * el folio lo emite el servidor, que es quien puede garantizar que no se
 * repita entre dispositivos.
 */
function nuevoFolio(): string {
  const hoy = new Date();
  const fecha = [
    hoy.getFullYear(),
    String(hoy.getMonth() + 1).padStart(2, "0"),
    String(hoy.getDate()).padStart(2, "0"),
  ].join("");
  const azar = String(Math.floor(Math.random() * 10000)).padStart(4, "0");
  return `EF-${fecha}-${azar}`;
}

export default function CobroEfectivo() {
  const [counts, setCounts] = useState<Counts>({});
  /** Denominación cuya cantidad se está capturando a mano; null = sin hoja. */
  const [editing, setEditing] = useState<number | null>(null);
  /** Folio de la ficha abierta; null = no hay ficha. Se fija al crearla para
   *  que no se regenere en cada render de la hoja. */
  const [folio, setFolio] = useState<string | null>(null);

  const total = denominations.reduce(
    (sum, { value }) => sum + value * (counts[value] ?? 0),
    0,
  );

  const add = (value: number) =>
    setCounts((prev) => ({ ...prev, [value]: (prev[value] ?? 0) + 1 }));

  // Quita un solo billete. Al llegar a 0 se borra la llave para que la
  // barra del contador desaparezca en vez de quedarse mostrando "0".
  const remove = (value: number) =>
    setCounts((prev) => {
      const next = { ...prev };
      const remaining = (next[value] ?? 0) - 1;
      if (remaining > 0) next[value] = remaining;
      else delete next[value];
      return next;
    });

  // Fija la cantidad de golpe (lo que devuelve la hoja). Misma regla que
  // `remove`: 0 borra la llave en vez de guardarla.
  const setCount = (value: number, count: number) =>
    setCounts((prev) => {
      const next = { ...prev };
      if (count > 0) next[value] = count;
      else delete next[value];
      return next;
    });

  const pressTimer = useRef<number | null>(null);
  // El long press y el tap comparten el mismo botón: soltar el dedo después
  // de un long press igual dispara el click, así que hay que tragárselo para
  // no sumar un billete encima de la cantidad que el usuario va a capturar.
  const longPressFired = useRef(false);

  const cancelPress = () => {
    if (pressTimer.current !== null) {
      clearTimeout(pressTimer.current);
      pressTimer.current = null;
    }
  };

  const startPress = (value: number) => {
    longPressFired.current = false;
    cancelPress();
    pressTimer.current = window.setTimeout(() => {
      longPressFired.current = true;
      pressTimer.current = null;
      setEditing(value);
    }, LONG_PRESS_MS);
  };

  // Si la pantalla se desmonta con el dedo abajo, el timer seguiría vivo.
  useEffect(() => cancelPress, []);

  const editingDenomination =
    editing === null ? null : denominations.find((d) => d.value === editing);

  const desglose = denominations
    .map((denomination) => ({
      denomination,
      count: counts[denomination.value] ?? 0,
    }))
    .filter(({ count }) => count > 0);

  return (
    <Screen>
      <header className="px-5 pt-8 text-center">
        <h1 className="text-xl font-medium">Cobro en efectivo</h1>
        <p className="mt-4 text-4xl font-semibold tabular-nums">
          {formatBalance(total)}
        </p>
      </header>

      <div className="mt-2 grid grid-cols-2 items-start gap-4 px-5">
        {denominations.map((denomination) => {
          const count = counts[denomination.value] ?? 0;
          return (
            // div y no button: cuando hay contador, adentro van botones
            // propios, y un <button> dentro de otro es HTML inválido.
            <div
              key={denomination.value}
              className="flex flex-col gap-2 rounded-2xl px-3 pt-1 pb-3"
            >
              {/* Siempre presente aunque count sea 0: si apareciera y
                  desapareciera, el tile cambiaria de alto y el de junto se
                  deformaria para igualar la fila. */}
              <motion.div
                animate={{ opacity: count > 0 ? 1 : 0 }}
                transition={{ duration: 0.18, ease: "easeOut" }}
                aria-hidden={count === 0}
                className={count > 0 ? "" : "pointer-events-none"}
              >
                    <div className="flex items-center justify-between rounded-full bg-white px-2 py-1 shadow-sm ring-1 ring-black/5">
                      <button
                        type="button"
                        onClick={() => add(denomination.value)}
                        aria-label={`Agregar otro billete de ${denomination.value} pesos`}
                        tabIndex={count > 0 ? 0 : -1}
                        className="rounded-full p-1.5 transition-transform active:scale-90"
                      >
                        <Plus size={18} aria-hidden />
                      </button>

                      <span className="text-base font-semibold tabular-nums">
                        {count}
                      </span>

                      <button
                        type="button"
                        onClick={() => remove(denomination.value)}
                        aria-label={`Quitar un billete de ${denomination.value} pesos`}
                        tabIndex={count > 0 ? 0 : -1}
                        className="rounded-full p-1.5 text-muted transition-transform active:scale-90"
                      >
                        <Trash2 size={18} aria-hidden />
                      </button>
                    </div>
              </motion.div>

              <motion.button
                type="button"
                whileTap={{ scale: 0.96 }}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
                onClick={() => {
                  if (longPressFired.current) {
                    longPressFired.current = false;
                    return;
                  }
                  add(denomination.value);
                }}
                onPointerDown={() => startPress(denomination.value)}
                onPointerUp={cancelPress}
                onPointerLeave={cancelPress}
                onPointerCancel={cancelPress}
                // Sin esto, en móvil el long press abre el menú de "copiar
                // imagen" del sistema encima de la hoja.
                onContextMenu={(event) => event.preventDefault()}
                aria-label={`Agregar ${denomination.value} pesos. Manten presionado para capturar la cantidad`}
                className="flex touch-manipulation flex-col items-center gap-2 select-none"
              >
                <Banknote denomination={denomination} />
                <span className="text-base font-medium tabular-nums">
                  ${denomination.value}
                </span>
              </motion.button>
            </div>
          );
        })}
      </div>

      {/* Sin esto la pantalla es un callejón sin salida: el total solo sube. */}
      <div className="mt-6 px-5">
        <button
          type="button"
          onClick={() => setCounts({})}
          disabled={total === 0}
          className="w-full rounded-full bg-accent py-2 text-sm font-medium text-white transition-transform active:scale-[0.98] disabled:opacity-40"
        >
          Limpiar todo
        </button>

        <button
          type="button"
          onClick={() => setFolio(nuevoFolio())}
          disabled={total === 0}
          className="mt-3 w-full rounded-full bg-brand py-3 text-sm font-medium text-white transition-transform active:scale-[0.98] disabled:opacity-40"
        >
          Crear ficha de depósito
        </button>
      </div>

      <AnimatePresence>
        {editingDenomination && (
          <CantidadBilletesSheet
            key={editingDenomination.value}
            denomination={editingDenomination}
            initialCount={counts[editingDenomination.value] ?? 0}
            onCancel={() => setEditing(null)}
            onConfirm={(count) => {
              setCount(editingDenomination.value, count);
              setEditing(null);
            }}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {folio && (
          <FichaDepositoSheet
            desglose={desglose}
            total={total}
            folio={folio}
            // Aceptar da por depositado el efectivo, así que el conteo se
            // reinicia: dejarlo cargado invitaría a crear la misma ficha dos
            // veces sin darse cuenta.
            onAccept={() => {
              setFolio(null);
              setCounts({});
            }}
          />
        )}
      </AnimatePresence>
    </Screen>
  );
}
