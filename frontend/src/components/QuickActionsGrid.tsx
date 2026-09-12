import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { GraduationCap, QrCode, Receipt, Send } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { quickActions } from "../data/mock";
import type { QuickAction } from "../data/types";

const icons: Record<QuickAction["icon"], LucideIcon> = {
  send: Send,
  qr: QrCode,
  education: GraduationCap,
  receipt: Receipt,
};

/** Grid 2x2 de accesos rápidos. */
export default function QuickActionsGrid() {
  return (
    <nav aria-label="Accesos rápidos" className="grid grid-cols-2 gap-4 px-5">
      {quickActions.map((action, i) => {
        const Icon = icons[action.icon];
        return (
          <motion.div
            key={action.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 * i, duration: 0.25, ease: "easeOut" }}
          >
            <Link
              to={action.to}
              className="flex h-32 flex-col justify-between rounded-2xl bg-tile p-4 transition-transform active:scale-[0.97]"
            >
              <Icon size={22} className="text-ink/70" aria-hidden />
              <div>
                <p className="text-sm font-semibold">{action.label}</p>
                <p className="mt-0.5 text-xs text-muted">{action.caption}</p>
              </div>
            </Link>
          </motion.div>
        );
      })}
    </nav>
  );
}
