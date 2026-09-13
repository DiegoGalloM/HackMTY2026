import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { motion } from "framer-motion";

interface BottomSheetProps {
  /** Se anuncia como el nombre del diálogo. */
  label: string;
  onDismiss: () => void;
  children: ReactNode;
}

/**
 * Hoja que sube desde abajo, con backdrop y cierre por Escape.
 *
 * Se monta por portal en la pantalla del celular y no en el árbol de la
 * pantalla que la abre: esa vive dentro del contenedor con scroll de
 * <Screen />, que además anima con transform — cualquiera de las dos cosas
 * haría que `inset-0` se midiera contra el alto scrolleado y la hoja quedara
 * fuera de vista.
 */
export default function BottomSheet({
  label,
  onDismiss,
  children,
}: BottomSheetProps) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onDismiss();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onDismiss]);

  const overlay = (
    <div className="absolute inset-0 z-50 flex flex-col justify-end">
      <motion.button
        type="button"
        aria-label="Cerrar"
        onClick={onDismiss}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.18 }}
        className="absolute inset-0 h-full w-full cursor-default bg-black/40"
      />

      <motion.div
        role="dialog"
        aria-modal="true"
        aria-label={label}
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        exit={{ y: "100%" }}
        transition={{ type: "spring", stiffness: 380, damping: 34 }}
        className="relative max-h-full overflow-y-auto rounded-t-3xl bg-white px-5 pt-3 pb-[calc(1.25rem+var(--safe-bottom))] shadow-2xl"
      >
        {/* Asa: señala que la hoja se puede cerrar. */}
        <div className="mx-auto h-1 w-10 rounded-full bg-black/15" />
        {children}
      </motion.div>
    </div>
  );

  const host = document.querySelector(".phone-frame__screen");
  return host ? createPortal(overlay, host) : overlay;
}
