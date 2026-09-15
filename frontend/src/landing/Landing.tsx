// frontend/src/landing/Landing.tsx
import { useEffect, useRef } from "react";
import { createTimeline } from "animejs";
import CapitalOneLogo from "../components/CapitalOneLogo";
import DemoNotice from "../components/DemoNotice";

interface LandingProps {
  onStart: () => void;
}

/** Duración total de la intro. Se exporta para que las pruebas la verifiquen. */
export const INTRO_DURATION_MS = 3000;

/**
 * Pantalla de bienvenida: logo + "Empezar". Es la única pantalla que usa
 * Anime.js, y solo para la animación de entrada; al dar clic no se anima nada,
 * simplemente se pasa a la bienvenida (ver App.tsx).
 *
 * El logo es el mismo CapitalOneLogo del resto de la app: se le pasan refs por
 * pieza (`partRefs`) para que "Capital", "One", el swoosh y "BUSINESS" vuelen
 * cada uno desde un lado distinto hasta juntarse. Así el logo vive en un solo
 * archivo y cualquier cambio de diseño se refleja también aquí.
 *
 * No fija su propio alto (nada de 100vh): `flex-1` la hace llenar el
 * `.phone-frame__screen`, que ya es 100dvh en móvil real y 844px en el mockup.
 */
export default function Landing({ onStart }: LandingProps) {
  const capitalRef = useRef<HTMLSpanElement>(null);
  const oneRef = useRef<HTMLSpanElement>(null);
  const swooshRef = useRef<HTMLSpanElement>(null);
  const businessRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const capital = capitalRef.current;
    const one = oneRef.current;
    const swoosh = swooshRef.current;
    const business = businessRef.current;
    const button = buttonRef.current;
    if (!capital || !one || !swoosh || !business || !button) return;

    const pieces = [capital, one, swoosh, business, button];

    // El reset de prefers-reduced-motion de index.css solo aplica a CSS;
    // Anime.js anima por JS, así que aquí se respeta a mano: sin animación,
    // todo visible de inmediato.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    // Las piezas se ocultan desde JS y no con una clase `opacity-0`: si el
    // bundle falla o tarda, el logo se ve completo en vez de quedarse en
    // blanco para siempre.
    for (const el of pieces) el.style.opacity = "0";

    // Posiciones absolutas en ms (tercer argumento de .add) para que la
    // secuencia sume exactamente INTRO_DURATION_MS:
    //   0    – 1300  "Capital" entra volando desde la izquierda
    //   250  – 1550  "One" entra desde la derecha
    //   500  – 1900  el swoosh cae desde arriba a la derecha y se acomoda
    //   1800 – 2500  "BUSINESS" aparece y cierra su espaciado
    //   2350 – 3000  el botón sube
    // outBack en las piezas del logo: un ligero rebote al llegar vende el
    // "se juntan"; el resto entra con outExpo, sin rebote. El desplazamiento
    // horizontal de las palabras NO rebota: con overshoot "One" se pasaba de
    // su lugar y se encimaba sobre la "l" de "Capital" por un instante.
    const tl = createTimeline({ defaults: { ease: "outExpo" } })
      .add(capital, { ease: "outBack(1.15)", opacity: [0, 1], translateX: { from: -160, to: 0, ease: "outExpo" }, translateY: [-24, 0], rotate: [-12, 0], scale: [0.7, 1], duration: 1300 }, 0)
      .add(one, { ease: "outBack(1.15)", opacity: [0, 1], translateX: { from: 160, to: 0, ease: "outExpo" }, translateY: [24, 0], rotate: [12, 0], scale: [0.7, 1], duration: 1300 }, 250)
      .add(swoosh, { ease: "outBack(1.15)", opacity: [0, 1], translateX: [120, 0], translateY: [-110, 0], rotate: [35, 0], scale: [0.3, 1], duration: 1400 }, 500)
      .add(business, { opacity: [0, 1], translateY: [8, 0], letterSpacing: ["0.75em", "0.35em"], duration: 700 }, 1800)
      .add(button, { opacity: [0, 1], translateY: [16, 0], duration: 650 }, INTRO_DURATION_MS - 650);

    // StrictMode monta dos veces en dev: revert deja los estilos inline como
    // estaban para que la segunda corrida no arranque a medias.
    return () => {
      tl.revert();
      for (const el of pieces) el.style.removeProperty("opacity");
    };
  }, []);

  return (
    // La pantalla scrollea (overflow-y-auto) para que el aviso de demo nunca
    // quede cortado en un celular chico; la animación vive en su propio bloque
    // con overflow-hidden, porque las piezas arrancan fuera de la pantalla y no
    // deben provocar scroll mientras vuelan hacia su lugar.
    <section className="flex flex-1 flex-col overflow-y-auto bg-white">
      <div className="flex flex-1 flex-col items-center justify-center gap-12 overflow-hidden px-6 py-10">
        <CapitalOneLogo
          business
          className="text-[44px]"
          partRefs={{
            capital: capitalRef,
            one: oneRef,
            swoosh: swooshRef,
            business: businessRef,
          }}
        />
        <button
          ref={buttonRef}
          type="button"
          onClick={onStart}
          className="min-h-12 w-full max-w-[280px] rounded-full bg-brand text-base font-semibold text-white shadow-[0_8px_20px_rgba(0,73,119,.28)] transition-transform active:scale-[.97] focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-accent"
        >
          Empezar
        </button>
      </div>
      {/* Fuera de la animación: se ve desde el primer instante, sin esperar la intro. */}
      <DemoNotice className="px-6 pb-[calc(var(--safe-bottom)+1.25rem)]" />
    </section>
  );
}
