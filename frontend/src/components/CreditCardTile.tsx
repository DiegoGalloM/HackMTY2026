import { motion } from "framer-motion";
import cardImage from "../assets/capital-one-venture-card.png";

export default function CreditCardTile() {
  return (
    <motion.div
      whileTap={{ scale: 0.98 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className="mx-5 overflow-hidden rounded-2xl drop-shadow-lg"
    >
      <img
        src={cardImage}
        alt="Tarjeta Capital One Business Venture"
        className="block h-auto w-full select-none"
        draggable={false}
      />
    </motion.div>
  );
}
