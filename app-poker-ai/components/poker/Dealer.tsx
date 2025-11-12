"use client";

import { motion } from "framer-motion";
import Image from "next/image";

interface DealerProps {
  isDealing: boolean;
  dealingCardIndex?: number;
}

export const Dealer: React.FC<DealerProps> = ({ isDealing, dealingCardIndex = 0 }) => {
  const dealerVariants = {
    idle: {
      y: 0,
      rotate: 0,
      scale: 1,
    },
    dealing: {
      y: [0, -8, 0],
      rotate: [0, -3, 3, 0],
      scale: [1, 1.03, 1],
      transition: {
        duration: 0.8,
        repeat: Infinity,
        ease: "easeInOut",
      },
    },
  };

  const cardVariants = {
    hidden: {
      opacity: 0,
      scale: 0,
      y: 0,
      x: 0,
      rotate: 0,
    },
    dealing: (index: number) => ({
      opacity: [0, 1, 1, 1, 0],
      scale: [0, 0.8, 1, 1, 0.6],
      y: [0, -30, -80, -120, -150],
      x: [0, (index % 2 === 0 ? -15 : 15), (index % 2 === 0 ? -20 : 20), 0, 0],
      rotate: [0, index % 2 === 0 ? -20 : 20, index % 2 === 0 ? -10 : 10, 0, 0],
      transition: {
        duration: 1.5,
        delay: index * 0.15,
        times: [0, 0.2, 0.5, 0.8, 1],
        ease: "easeOut",
      },
    }),
  };

  return (
    <div className="absolute top-[15%] left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-30 pointer-events-none">
      <motion.div
        variants={dealerVariants}
        animate={isDealing ? "dealing" : "idle"}
        className="relative"
      >
        <div className="relative w-32 h-40 md:w-40 md:h-48 lg:w-48 lg:h-56">
          <Image
            src="/introduction/dealer-no.bg.png"
            alt="Dealer"
            fill
            className="object-contain drop-shadow-2xl"
            priority
          />
        </div>
        
        {isDealing && (
          <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-full">
            {Array.from({ length: 6 }, (_, index) => (
              <motion.div
                key={index}
                custom={index}
                variants={cardVariants}
                initial="hidden"
                animate="dealing"
                className="absolute w-10 h-14 bg-white rounded-md shadow-xl border-2 border-black/20"
                style={{
                  left: `${(index - 2.5) * 18}px`,
                }}
              >
                <div className="w-full h-full bg-gradient-to-br from-blue-600 via-blue-700 to-blue-800 rounded flex items-center justify-center border border-blue-500">
                  <div className="text-white text-lg font-bold">🂠</div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
};

