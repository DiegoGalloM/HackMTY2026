import { useEffect, useRef, useState } from "react";
import type { MouseEvent, PointerEvent as ReactPointerEvent, Ref } from "react";
import {
  animate,
  motion,
  useMotionTemplate,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform,
} from "framer-motion";
import { Check, Copy, RotateCcw } from "lucide-react";
import mainPageCard from "../assets/capital-one-main-page-card.png";
import welcomeCard from "../assets/capital-one-welcome-demo-card.png";
import { creditCard, formatCardNumber } from "../data/mock";
import "./BusinessCard.css";

/** Inclinación máxima en grados, en cada eje. */
const MAX_TILT = 14;

interface CreditCardTileProps {
  artwork?: "original" | "demo";
  /** Si la tarjeta se voltea al tocarla para mostrar número y titular. */
  flippable?: boolean;
  /** Nombre completo del reverso. Por defecto, el titular de demo. */
  holder?: string;
}

export default function CreditCardTile({
  artwork = "original",
  flippable = false,
  holder = creditCard.holder,
}: CreditCardTileProps) {
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const firstFieldRef = useRef<HTMLButtonElement>(null);
  const reducedMotion = useReducedMotion();
  const [face, setFace] = useState<"front" | "back">("front");
  // Espejos síncronos del estado para el bucle del giro, que corre entre
  // renders y no puede leer `face` sin quedarse con un valor viejo.
  const shownFace = useRef<"front" | "back">("front");
  const wantedFace = useRef<"front" | "back">("front");
  const turning = useRef(false);
  const flipped = face === "back";

  // Posición del cursor dentro de la tarjeta, normalizada a [-0.5, 0.5]:
  // (-0.5,-0.5) = esquina superior izquierda, (0.5, 0.5) = inferior derecha.
  const px = useMotionValue(0);
  const py = useMotionValue(0);

  // El spring es lo que hace que la tarjeta "persiga" al cursor con inercia
  // en vez de saltar de golpe, y que regrese sola a plano al salir.
  const spring = { stiffness: 220, damping: 22, mass: 0.6 };
  const sx = useSpring(px, spring);
  const sy = useSpring(py, spring);

  // Signos: en CSS el eje Y apunta hacia ABAJO y el Z hacia el espectador,
  // así que rotateX positivo levanta el borde INFERIOR, y rotateY positivo
  // hunde el borde DERECHO. Por eso rotateY va invertido: así la esquina
  // que está debajo del cursor es siempre la que sube.
  const rotateX = useTransform(sy, [-0.5, 0.5], [-MAX_TILT, MAX_TILT]);
  const tiltY = useTransform(sx, [-0.5, 0.5], [MAX_TILT, -MAX_TILT]);

  // El giro vive en su propio motion value y se SUMA a la inclinación: las
  // dos cosas escriben rotateY, así que una sola ganaría.
  const flip = useMotionValue(0);
  const rotateY = useTransform([tiltY, flip], ([tilt, spin]: number[]) => tilt + spin);

  // El giro va en dos tiempos y la cara se cambia a 90°, con la tarjeta de
  // canto: ahí no se ve nada, así que el cambio es invisible y en ningún
  // momento hay una cara espejeada (ver BusinessCard.css).
  //
  // El bucle apunta siempre a la última cara pedida en vez de ignorar lo que
  // llegue a media animación: si tocas y te arrepientes, la tarjeta termina
  // el medio giro y se regresa sola.
  const turn = (next: "front" | "back") => {
    wantedFace.current = next;
    if (reducedMotion) {
      shownFace.current = next;
      setFace(next);
      return;
    }
    if (turning.current) return;
    void (async () => {
      turning.current = true;
      while (wantedFace.current !== shownFace.current) {
        const target = wantedFace.current;
        const edge = target === "back" ? 90 : -90;
        await animate(flip, edge, { duration: 0.2, ease: "easeIn" });
        shownFace.current = target;
        setFace(target);
        flip.jump(-edge);
        await animate(flip, 0, { duration: 0.24, ease: "easeOut" });
      }
      turning.current = false;
    })();
  };

  // El foco sigue a la cara visible: la que queda atrás es inerte, así que
  // el foco se perdería en el aire. El primer render no mueve nada.
  const mounted = useRef(false);
  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true;
      return;
    }
    // preventScroll: la tarjeta ya está a la vista y el scroll automático
    // del foco empujaría la pantalla justo cuando gira.
    if (flipped) firstFieldRef.current?.focus({ preventScroll: true });
    else triggerRef.current?.focus({ preventScroll: true });
  }, [flipped]);

  // Brillo que sigue al cursor, para que se lea como que la luz pega justo
  // donde la tarjeta se levanta.
  const glareX = useTransform(sx, [-0.5, 0.5], ["0%", "100%"]);
  const glareY = useTransform(sy, [-0.5, 0.5], ["0%", "100%"]);
  const glare = useMotionTemplate`radial-gradient(circle at ${glareX} ${glareY}, rgba(255,255,255,0.18), transparent 65%)`;

  // La opacidad se maneja a mano y no con whileHover: la capa del brillo es
  // pointer-events-none, así que nunca recibiría el hover ella misma.
  const glareOpacity = useSpring(useMotionValue(0), { stiffness: 180, damping: 30 });

  const handlePointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    // Solo con mouse: en touch no hay hover y el gesto pelearía con el
    // scroll de la pantalla.
    if (event.pointerType !== "mouse" || reducedMotion) return;
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;
    px.set(Math.max(-0.5, Math.min(0.5, (event.clientX - rect.left) / rect.width - 0.5)));
    py.set(Math.max(-0.5, Math.min(0.5, (event.clientY - rect.top) / rect.height - 0.5)));
    glareOpacity.set(1);
  };

  // Al salir el cursor, los motion values vuelven a 0 y el spring devuelve
  // la tarjeta a plano sola.
  const handlePointerLeave = () => {
    px.set(0);
    py.set(0);
    glareOpacity.set(0);
  };

  return (
    // La perspectiva va en el CONTENEDOR, no en el elemento que rota: si se
    // pone en el mismo elemento, cada esquina se proyecta igual y el giro se
    // ve plano en vez de levantarse hacia el espectador.
    <div className="business-card-stage">
      <div className="business-card-angle">
        <motion.div
          ref={ref}
          onPointerMove={handlePointerMove}
          onPointerLeave={handlePointerLeave}
          // El clic se atiende en toda la superficie y no solo en los
          // botones: si la tarjeta se inclina entre el mousedown y el mouseup,
          // el click se dispara en el ancestro común de los dos, y un botón
          // que cubre la cara se lo perdería. Los datos del reverso cortan la
          // propagación para copiar sin voltear.
          onClick={() => turn(flipped ? "front" : "back")}
          onKeyDown={(event) => {
            if (event.key === "Escape" && flipped) turn("front");
          }}
          style={{ rotateX, rotateY }}
          whileHover={reducedMotion ? undefined : { scale: 1.02 }}
          whileTap={reducedMotion ? undefined : { scale: 0.98 }}
          transition={{ type: "spring", stiffness: 400, damping: 30 }}
          className="business-card-surface"
        >
          <div className={`business-card-face${flipped ? " business-card-face--hidden" : ""}`}>
            <div className="reference-card">
              <img
                src={artwork === "demo" ? welcomeCard : mainPageCard}
                alt={artwork === "demo" ? "Tarjeta Capital One Business Venture. NEGOCIO DEMO, terminada en 4242." : "Tarjeta Capital One Business Venture"}
                draggable={false}
              />
            </div>
            <motion.div
              aria-hidden
              style={{ backgroundImage: glare, opacity: glareOpacity }}
              className="pointer-events-none absolute inset-0"
            />
            {flippable && (
              <button
                ref={triggerRef}
                type="button"
                inert={flipped}
                aria-label={`Ver los datos de la tarjeta terminada en ${creditCard.last4}`}
                className="business-card-flip-trigger"
              />
            )}
          </div>

          {flippable && (
            <div
              inert={!flipped}
              className={`business-card-face business-card-face--back card-back${
                flipped ? "" : " business-card-face--hidden"
              }`}
            >
              <div className="card-back__stripe" aria-hidden />
              <div className="card-back__body">
                <CopyField
                  ref={firstFieldRef}
                  label="Número de tarjeta"
                  display={formatCardNumber(creditCard.number)}
                  value={creditCard.number}
                  mono
                />
                <CopyField label="Titular" display={holder} value={holder} />
                <button type="button" className="card-back__flip">
                  <RotateCcw size={12} aria-hidden /> Voltear
                </button>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}

interface CopyFieldProps {
  ref?: Ref<HTMLButtonElement>;
  label: string;
  /** Cómo se ve en la tarjeta, agrupado con espacios. */
  display: string;
  /** Lo que se pega: sin espacios, listo para usar. */
  value: string;
  mono?: boolean;
}

/** Dato de la tarjeta que se copia al portapapeles al tocarlo. */
function CopyField({ ref, label, display, value, mono }: CopyFieldProps) {
  // null = todavía no se intenta; false = el navegador negó el portapapeles
  // (contexto no seguro, permiso denegado), así que el fallo se avisa.
  const [copied, setCopied] = useState<boolean | null>(null);

  useEffect(() => {
    if (copied === null) return;
    const timer = setTimeout(() => setCopied(null), 2000);
    return () => clearTimeout(timer);
  }, [copied]);

  const copy = async (event: MouseEvent<HTMLButtonElement>) => {
    // Sin esto el clic llega a la tarjeta y la voltea en vez de copiar.
    event.stopPropagation();
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <button
      ref={ref}
      type="button"
      onClick={copy}
      aria-label={`Copiar ${label.toLowerCase()}: ${display}`}
      className="card-back__field"
    >
      <span
        role="status"
        className={`card-back__label${copied === true ? " card-back__label--ok" : ""}${
          copied === false ? " card-back__label--fail" : ""
        }`}
      >
        {copied === true ? "Copiado" : copied === false ? "No se pudo copiar" : label}
      </span>
      <span className={`card-back__value${mono ? " card-back__value--mono" : ""}`}>
        {display}
      </span>
      <span className="card-back__copy" aria-hidden>
        {copied === true ? <Check size={15} /> : <Copy size={15} />}
      </span>
    </button>
  );
}
