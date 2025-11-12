"use client";

import { useState, useEffect, useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { Table } from "@/components/poker/Table";
import { Dealer } from "@/components/poker/Dealer";
import { createInitialGameState, Player } from "@/lib/poker/gameState";
import { ICard } from "@/lib/poker/types";

export default function DogPokerClubPage() {
  const [gameState, setGameState] = useState(createInitialGameState("normal"));
  const [isDealing, setIsDealing] = useState(false);
  const [dealtCards, setDealtCards] = useState<boolean[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end end"],
  });

  // Transform scroll progress to control animations
  const opacity = useTransform(scrollYProgress, [0, 0.3, 0.7, 1], [1, 1, 0.8, 0.5]);
  const scale = useTransform(scrollYProgress, [0, 0.3, 0.7, 1], [1, 1, 0.95, 0.9]);
  const scrollIndicatorOpacity = useTransform(scrollYProgress, [0, 0.3], [1, 0]);

  // Initialize game state with sample players and cards
  useEffect(() => {
    const samplePlayers: Player[] = [
      {
        id: 0,
        name: "Player 1",
        isHuman: false,
        chair: 0,
        balance: 1000,
        currentBet: 50,
        inGame: true,
        isAllIn: false,
        folded: false,
        hand: [
          { suit: "♠", rank: "A" },
          { suit: "♠", rank: "K" },
        ],
      },
      {
        id: 1,
        name: "Player 2",
        isHuman: false,
        chair: 1,
        balance: 950,
        currentBet: 50,
        inGame: true,
        isAllIn: false,
        folded: false,
        hand: [
          { suit: "♥", rank: "Q" },
          { suit: "♥", rank: "J" },
        ],
      },
      {
        id: 2,
        name: "Player 3",
        isHuman: false,
        chair: 2,
        balance: 900,
        currentBet: 100,
        inGame: true,
        isAllIn: false,
        folded: false,
        hand: [
          { suit: "♦", rank: "10" },
          { suit: "♦", rank: "9" },
        ],
      },
    ];

    const sampleCommunityCards: ICard[] = [
      { suit: "♠", rank: "Q" },
      { suit: "♣", rank: "J" },
      { suit: "♥", rank: "10" },
      { suit: "♦", rank: "8" },
      { suit: "♠", rank: "7" },
    ];

    setGameState((prev) => ({
      ...prev,
      players: samplePlayers,
      communityCards: sampleCommunityCards,
      currentRound: "river",
      pot: 200,
      currentBet: 100,
    }));

    // Initialize dealt cards array
    setDealtCards(new Array(samplePlayers.length * 2).fill(false));

    // Start dealing animation after a short delay
    setTimeout(() => {
      setIsDealing(true);
      // Animate cards being dealt one by one
      const dealSequence = async () => {
        for (let i = 0; i < samplePlayers.length * 2; i++) {
          await new Promise((resolve) => setTimeout(resolve, 250));
          setDealtCards((prev) => {
            const newDealt = [...prev];
            newDealt[i] = true;
            return newDealt;
          });
        }
        // After dealing player cards, deal community cards
        setTimeout(() => {
          setIsDealing(false);
        }, 1500);
      };
      dealSequence();
    }, 800);
  }, []);

  return (
    <div 
      ref={containerRef}
      className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900"
    >
      {/* Scroll Story Container */}
      <div className="relative">
        {/* First Scene: Poker Table with Dealer */}
        <section className="min-h-screen flex items-center justify-center relative overflow-hidden">
          <motion.div
            style={{ opacity, scale }}
            className="w-full h-full flex items-center justify-center py-8"
          >
            <div className="relative w-full max-w-7xl mx-auto px-4">
              <div className="relative">
                {/* Dealer Component */}
                <Dealer isDealing={isDealing} />

                {/* Poker Table */}
                <div className="mt-16 md:mt-20">
                  <Table
                    pot={gameState.pot}
                    currentRound={gameState.currentRound}
                    lastBetAmount={gameState.currentBet}
                    communityCards={gameState.communityCards}
                    visibleCards={5}
                    players={gameState.players}
                    turnHolder={gameState.players[0]?.chair ?? -1}
                    humanPlayerHand=""
                    dealtCards={dealtCards.length > 0 ? dealtCards : [true, true, true, true, true, true]}
                    userAddress=""
                  />
                </div>
              </div>
            </div>
          </motion.div>

          {/* Scroll Indicator */}
          <motion.div
            className="absolute bottom-10 left-1/2 transform -translate-x-1/2 text-white/60 text-sm"
            style={{
              opacity: scrollIndicatorOpacity,
            }}
          >
            <div className="flex flex-col items-center gap-2">
              <span>Scroll to continue</span>
              <motion.div
                animate={{ y: [0, 10, 0] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                className="text-2xl"
              >
                ↓
              </motion.div>
            </div>
          </motion.div>
        </section>

        {/* Additional scroll story sections can be added here */}
        <section className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-800 via-slate-700 to-slate-800">
          <div className="max-w-4xl mx-auto px-4 text-center text-white">
            <motion.h2
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="text-4xl md:text-6xl font-bold mb-8"
            >
              Welcome to Dog Poker Club
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="text-lg md:text-xl text-gray-300 leading-relaxed"
            >
              Experience the future of decentralized poker tournaments powered by GenLayer Intelligent Contracts.
            </motion.p>
          </div>
        </section>
      </div>
    </div>
  );
}

