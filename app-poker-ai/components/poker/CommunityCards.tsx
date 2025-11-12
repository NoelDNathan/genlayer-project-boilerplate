"use client";

import { Card } from "./Card";
import { motion } from "framer-motion";
import { ICard } from "@/lib/poker/types";

interface CommunityCardsProps {
  cards: ICard[];
  visibleCards: number;
}

export const CommunityCards: React.FC<CommunityCardsProps> = ({ cards, visibleCards }) => {
  return (
    <motion.div
      className="flex space-x-2 justify-center"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.5, duration: 0.5 }}
    >
      {Array.from({ length: 5 }, (_, index) => {
        const card = cards[index];
        const isVisible = index < visibleCards;
        return (
          <Card
            key={index}
            suit={card?.suit || "♠"}
            rank={card?.rank || "A"}
            hidden={!card || !isVisible}
            isDealt={isVisible}
            isFolded={false}
          />
        );
      })}
    </motion.div>
  );
};

