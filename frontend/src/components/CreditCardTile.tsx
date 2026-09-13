import { useRef } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import {
  motion,
  useMotionTemplate,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform,
} from "framer-motion";
import mainPageCard from "../assets/capital-one-main-page-card.png";
import welcomeCard from "../assets/capital-one-welcome-demo-card.png";
import "./BusinessCard.css";

/** Inclinación máxima en grados, en cada eje. */
const MAX_TILT = 14;

export default function CreditCardTile({ artwork = "original" }: { artwork?: "original" | "demo" }) {
  const ref = useRef<HTMLDivElement>(null);
  const reducedMotion = useReducedMotion();

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
  const rotateY = useTransform(sx, [-0.5, 0.5], [MAX_TILT, -MAX_TILT]);

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
          style={{ rotateX, rotateY }}
          whileHover={reducedMotion ? undefined : { scale: 1.02 }}
          whileTap={reducedMotion ? undefined : { scale: 0.98 }}
          transition={{ type: "spring", stiffness: 400, damping: 30 }}
          className="business-card-surface"
        >
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
        </motion.div>
      </div>
    </div>
  );
}
