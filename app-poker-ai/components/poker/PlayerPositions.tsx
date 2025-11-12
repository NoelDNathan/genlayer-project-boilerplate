"use client";

import React from "react";
import { Card } from "./Card";
import { Player } from "@/lib/poker/gameState";

interface PlayerPositionsProps {
  players: Player[];
  turnHolder: number;
  round: string;
  humanPlayerHand?: string | null;
  dealtCards: boolean[];
  userAddress?: string;
}

export const PlayerPositions: React.FC<PlayerPositionsProps> = ({
  players,
  turnHolder,
  round,
  humanPlayerHand,
  dealtCards,
}) => {
  if (players.length === 0) {
    return null;
  }

  const userPlayerIndex = players.findIndex((player) => player.isHuman);
  const startPlayerIndex = userPlayerIndex === -1 ? 0 : userPlayerIndex;

  const getPlayerPosition = (
    index: number,
    totalPlayers: number
  ): { top: string; left: string } => {
    const normalizedIndex =
      (((index - startPlayerIndex) % totalPlayers) + totalPlayers) % totalPlayers;
    const angle = (normalizedIndex * (360 / totalPlayers) + 90) * (Math.PI / 180);
    // Reduced radius to leave more space for buttons at the bottom
    const radiusX = 45;
    const radiusY = 45;
    const centerX = 50;
    const centerY = 50;

    const x = centerX + radiusX * Math.cos(angle);
    const y = centerY + radiusY * Math.sin(angle);
    return {
      top: `${y}%`,
      left: `${x}%`,
    };
  };

  const isShowdown = round === "showdown";

  return (
    <>
      {players.map((player, index) => {
        const position = getPlayerPosition(index, players.length);
        const isTurnHolder = turnHolder === player.chair;
        const isUser = player.isHuman;
        const isFolded = player.folded;

        return (
          <div
            key={player.id}
            style={{ top: position.top, left: position.left }}
            className={`absolute transform -translate-x-1/2 -translate-y-1/2 transition-all duration-300 ${
              isTurnHolder ? "scale-110 z-20" : "z-10"
            }`}
          >
            <div className="relative flex flex-col items-center">
              <div className="relative z-0 -mb-8 flex justify-center">
                <div className="flex space-x-2">
                  {player.hand.map((card, cardIndex) => (
                    <div key={cardIndex} style={{ position: "relative", zIndex: 10 + cardIndex }}>
                      <Card
                        suit={card.suit}
                        rank={card.rank}
                        hidden={!isUser && !isShowdown}
                        isDealt={dealtCards[index] || false}
                        isFolded={isFolded}
                      />
                    </div>
                  ))}
                </div>
              </div>
              <div
                className={`
                  relative z-10
                ${
                  isUser
                    ? "bg-gradient-to-r from-blue-700 to-blue-800 border-blue-500"
                    : "bg-gradient-to-r from-slate-700 to-slate-800 border-slate-600"
                } 
                ${isTurnHolder ? "ring-4 ring-yellow-400 ring-opacity-75 shadow-2xl" : "shadow-lg"}
                p-2 md:p-3 rounded-xl text-white border-2 min-w-[160px] md:min-w-[180px] text-center transition-all duration-300
              `}
              >
                <h2
                  className={`text-sm md:text-base font-bold mb-1 ${
                    isUser ? "text-blue-200" : "text-white"
                  }`}
                >
                  {player.name}
                  {player.chair !== undefined && (
                    <span className="ml-1 md:ml-2 text-xs bg-amber-600 px-1.5 md:px-2 py-0.5 md:py-1 rounded-full">
                      {player.chair}
                    </span>
                  )}
                </h2>

                <div className="space-y-0.5 text-xs">
                  <p className="flex justify-between">
                    <span className="text-gray-300">Balance:</span>
                    <span className="font-bold text-green-400">${player.balance}</span>
                  </p>
                  <p className="flex justify-between">
                    <span className="text-gray-300">Bet:</span>
                    <span className="font-bold text-yellow-400">${player.currentBet}</span>
                  </p>

                  {isFolded && (
                    <p className="text-red-400 font-bold text-xs bg-red-900 px-1.5 py-0.5 rounded">
                      FOLDED
                    </p>
                  )}
                  {player.isAllIn && (
                    <p className="text-purple-400 font-bold text-xs bg-purple-900 px-1.5 py-0.5 rounded">
                      ALL IN
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </>
  );
};

