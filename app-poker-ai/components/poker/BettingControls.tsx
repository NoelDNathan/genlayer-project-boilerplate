"use client";
import React, { useState } from "react";

interface BettingControlsProps {
  onFold: () => void;
  onCheck: () => void;
  onCall: () => void;
  onRaise: (amount: number) => void;
  currentBet: number;
  playerBet: number;
  playerBalance: number;
  isLoading: boolean;
}

export const BettingControls: React.FC<BettingControlsProps> = ({
  onFold,
  onCheck,
  onCall,
  onRaise,
  currentBet,
  playerBet,
  playerBalance,
  isLoading,
}) => {
  const [raiseAmount, setRaiseAmount] = useState("");
  const [showRaiseInput, setShowRaiseInput] = useState(true);

  const handleRaise = () => {
    const amount = parseFloat(raiseAmount);
    if (amount > currentBet && amount <= playerBalance + playerBet) {
      onRaise(amount);
      setRaiseAmount("");
      setShowRaiseInput(true);
    }
  };

  const callAmount = currentBet - playerBet;
  const canCheck = currentBet === playerBet;
  const canCall = currentBet > playerBet && playerBalance >= callAmount;
  const canRaise = playerBalance > 0 && currentBet < playerBalance + playerBet;

  return (
    <div className="rounded-xl p-2 shadow-xl max-w-md mx-auto bg-gradient-to-br from-slate-800/90 via-slate-700/90 to-slate-800/90 backdrop-blur-md border border-slate-600/50">
      <div className="flex items-center gap-1.5 md:gap-2 flex-wrap">
        {canCheck ? (
          <button
            onClick={onCheck}
            disabled={isLoading}
            className="flex-1 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 disabled:from-gray-500 disabled:to-gray-600 text-white px-2.5 py-1.5 rounded-lg font-bold text-xs shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105 disabled:transform-none disabled:cursor-not-allowed border border-green-500/50"
          >
            Check
          </button>
        ) : (
          <>
            <button
              onClick={onFold}
              disabled={isLoading}
              className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 disabled:from-gray-500 disabled:to-gray-600 text-white px-2.5 py-1.5 rounded-lg font-bold text-xs shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105 disabled:transform-none disabled:cursor-not-allowed border border-red-500/50 min-w-[70px]"
            >
              Fold
            </button>
            <button
              onClick={onCall}
              disabled={isLoading || !canCall}
              className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-gray-500 disabled:to-gray-600 text-white px-2.5 py-1.5 rounded-lg font-bold text-xs shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105 disabled:transform-none disabled:cursor-not-allowed border border-blue-500/50 min-w-[85px]"
            >
              Call ${callAmount.toFixed(0)}
            </button>
          </>
        )}

        {canRaise && (
          <>
            {!showRaiseInput ? (
              <button
                onClick={() => setShowRaiseInput(true)}
                disabled={isLoading}
                className="flex-1 bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-700 hover:to-amber-800 disabled:from-gray-500 disabled:to-gray-600 text-white px-2.5 py-1.5 rounded-lg font-bold text-xs shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105 disabled:transform-none disabled:cursor-not-allowed border border-amber-500/50"
              >
                Raise
              </button>
            ) : (
              <div className="flex gap-1.5 flex-1 min-w-0">
                <input
                  type="number"
                  value={raiseAmount}
                  onChange={(e) => setRaiseAmount(e.target.value)}
                  placeholder="Amount"
                  className="flex-1 min-w-0 border-2 border-slate-500 rounded-lg px-2 py-1.5 bg-slate-900/80 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500 text-xs font-medium shadow-inner"
                  min={currentBet + 1}
                  max={playerBalance + playerBet}
                  step="1"
                />
                <button
                  onClick={handleRaise}
                  disabled={
                    isLoading ||
                    !raiseAmount ||
                    parseFloat(raiseAmount) <= currentBet ||
                    parseFloat(raiseAmount) > playerBalance + playerBet
                  }
                  className="bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-700 hover:to-amber-800 disabled:from-gray-500 disabled:to-gray-600 text-white px-2.5 py-1.5 rounded-lg font-bold text-xs shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105 disabled:transform-none disabled:cursor-not-allowed border border-amber-500/50 whitespace-nowrap flex-shrink-0"
                >
                  Raise
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

