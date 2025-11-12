"use client";

import { PlayerPositions } from "./PlayerPositions";
import { CommunityCards } from "./CommunityCards";
import { ICard } from "@/lib/poker/types";
import { Player } from "@/lib/poker/gameState";

interface TableProps {
  pot: number;
  currentRound: string;
  lastBetAmount: number;
  communityCards: ICard[];
  visibleCards: number;
  players: Player[];
  turnHolder: number;
  humanPlayerHand: string;
  dealtCards: boolean[];
  userAddress: string;
}

export const Table: React.FC<TableProps> = ({
  pot,
  currentRound,
  lastBetAmount,
  communityCards,
  visibleCards,
  players,
  turnHolder,
  humanPlayerHand,
  dealtCards,
  userAddress,
}) => {
  const getVisibleCardsCount = () => {
    switch (currentRound) {
      case "preflop":
        return 0;
      case "flop":
        return 3;
      case "turn":
        return 4;
      case "river":
      case "showdown":
        return 5;
      default:
        return visibleCards;
    }
  };

  return (
    <div className="w-full flex items-start justify-center px-4 pt-4 pb-2">
      <div className="relative w-full max-w-[75vw] md:max-w-3xl lg:max-w-4xl aspect-[5/3]">
        <div className="absolute inset-0 bg-gradient-to-br from-green-800 via-green-700 to-green-900 rounded-full border-8 border-amber-600 shadow-2xl flex items-center justify-center">
          <div className="absolute inset-4 bg-gradient-to-br from-green-600 to-green-800 rounded-full opacity-80"></div>
          <div className="absolute inset-0 rounded-full border-4 border-amber-700 shadow-inner"></div>

          <div className="absolute top-[70%] left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10">
            <div className="bg-gradient-to-r from-amber-600 to-amber-700 text-white px-3 py-1.5 rounded-lg shadow-lg border border-amber-500">
              <div className="flex items-center justify-center gap-3">
                <div>
                  <div className="text-base font-bold text-center"> ${pot}</div>
                  <div className="text-xs text-amber-200 text-center">Total Pot</div>
                </div>
                {lastBetAmount > 0 && (
                  <div className="border-l border-amber-400 pl-3">
                    <div className="text-base font-bold text-center"> ${lastBetAmount}</div>
                    <div className="text-xs text-amber-200 text-center">Current Bet</div>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="absolute top-[45%] left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10">
            <CommunityCards cards={communityCards} visibleCards={getVisibleCardsCount()} />
          </div>
        </div>

        <PlayerPositions
          players={players}
          turnHolder={turnHolder}
          round={currentRound}
          humanPlayerHand={humanPlayerHand}
          dealtCards={dealtCards}
          userAddress={userAddress}
        />
      </div>
    </div>
  );
};

