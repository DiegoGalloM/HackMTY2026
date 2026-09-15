import type { ReactNode } from "react";
import { motion } from "framer-motion";

interface ScreenProps {
  title?: string;
  children: ReactNode;
}

/**
 * Contenedor de pantalla: hace el fade/slide de entrada y reserva el espacio
 * de la barra inferior (altura + franja de demo + safe area) para que nada
 * quede tapado.
 */
export default function Screen({ title, children }: ScreenProps) {
  return (
    <motion.main
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.22, ease: "easeOut" }}
      className="h-full overflow-y-auto pt-[var(--safe-top)] pb-[calc(var(--nav-height)+var(--demo-band-height)+var(--safe-bottom)+1.5rem)]"
    >
      {title && (
        <h1 className="px-5 pt-6 pb-4 text-2xl font-semibold tracking-tight">
          {title}
        </h1>
      )}
      {children}
    </motion.main>
  );
}
