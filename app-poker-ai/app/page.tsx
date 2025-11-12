"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useAccount } from "@/lib/AccountContext";
import { PokerPlayer } from "@/lib/PokerPlayer";
import { getBotActionFromGenLayer } from "@/lib/poker/genlayerBotAI";
import { GameState, createInitialGameState } from "@/lib/poker/gameState";
import {
  startNewHand,
  processPlayerAction,
  advanceToNextRound,
  isBettingRoundComplete,
  getNextActivePlayerIndex,
  determineWinners,
  type BotAction,
} from "@/lib/poker/gameEngine";
import { evaluateHand } from "@/lib/poker/handEvaluation";
import { Table } from "@/components/poker/Table";
import { BettingControls } from "@/components/poker/BettingControls";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2 } from "lucide-react";

export default function PokerAIGamePage() {
  const { account, connectAccount, accountAddress } = useAccount();
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [contract, setContract] = useState<PokerPlayer | null>(null);
  const [contractDeployed, setContractDeployed] = useState(false);
  const [isDeploying, setIsDeploying] = useState(false);
  const [deploymentError, setDeploymentError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [dealtCards, setDealtCards] = useState<boolean[]>([]);
  const [showNextHandButton, setShowNextHandButton] = useState(false);
  const [botGameIds, setBotGameIds] = useState<Map<number, string>>(new Map());
  const [botThinking, setBotThinking] = useState<Set<number>>(new Set());
  
  const isActionInProgressRef = useRef(false);
  const initialBalancesRef = useRef<number[]>([]);

  // Initialize account if needed
  useEffect(() => {
    if (!account) {
      connectAccount();
    }
  }, [account, connectAccount]);

  // Deploy contract
  useEffect(() => {
    const deployContract = async () => {
      if (!account || contractDeployed || isDeploying) return;

      setIsDeploying(true);
      setDeploymentError(null);

      try {
        const pokerPlayerContract = new PokerPlayer(null, account);
        
        // Read contract code from file
        const contractCodeResponse = await fetch("/contracts/poker_player.py");
        if (!contractCodeResponse.ok) {
          throw new Error("Failed to load contract code");
        }
        const contractCodeText = await contractCodeResponse.text();
        const contractCode = new TextEncoder().encode(contractCodeText);

        const address = await pokerPlayerContract.deployContract(contractCode);
        pokerPlayerContract.setContractAddress(address);
        setContract(pokerPlayerContract);
        setContractDeployed(true);
        console.log("[PokerAIGame] Contract deployed at:", address);
      } catch (error: any) {
        console.error("[PokerAIGame] Deployment error:", error);
        setDeploymentError(error.message || "Failed to deploy contract");
      } finally {
        setIsDeploying(false);
      }
    };

    deployContract();
  }, [account, contractDeployed, isDeploying]);

  // Start new hand when contract is deployed
  useEffect(() => {
    if (!contractDeployed) return;
    if (gameState) return; // Ya tenemos un gameState, no inicializar de nuevo

    const initialState = createInitialGameState("normal");
    initialBalancesRef.current = initialState.players.map((p) => p.balance);
    const newState = startNewHand(initialState);
    setGameState(newState);
    setDealtCards(Array(3).fill(true));
    setShowNextHandButton(false);
    setBotGameIds(new Map()); // Reset bot game IDs for new hand
  }, [contractDeployed, gameState]);

  // Handle bot turns
  useEffect(() => {
    if (!gameState || !contract || !contractDeployed || gameState.isHandComplete) return;
    if (gameState.currentRound === "showdown") return;

    const currentPlayer = gameState.players[gameState.currentTurnIndex];
    if (!currentPlayer || currentPlayer.isHuman) return;
    if (isProcessing || botThinking.has(currentPlayer.id)) return;

    const handleBotTurn = async () => {
      if (isActionInProgressRef.current) return;
      
      isActionInProgressRef.current = true;
      setIsProcessing(true);
      setBotThinking((prev) => new Set(prev).add(currentPlayer.id));

      try {
        const botGameId = botGameIds.get(currentPlayer.id) || null;
        const result = await getBotActionFromGenLayer(
          currentPlayer,
          gameState,
          contract,
          botGameId
        );

        // Store game_id if we got one
        if (result.gameId && result.gameId !== botGameId) {
          setBotGameIds((prev) => new Map(prev).set(currentPlayer.id, result.gameId!));
        }

        let newState = processPlayerAction(
          gameState,
          gameState.currentTurnIndex,
          result.decision.action as BotAction,
          result.decision.raiseAmount
        );

        const bettingRoundComplete = isBettingRoundComplete(newState);

        if (bettingRoundComplete) {
          newState = advanceToNextRound(newState);
        } else {
          const nextIndex = getNextActivePlayerIndex(newState);
          if (nextIndex >= 0) {
            newState.currentTurnIndex = nextIndex;
          } else {
            newState = advanceToNextRound(newState);
          }
        }

        setGameState(newState);
      } catch (error) {
        console.error("[PokerAIGame] Bot action error:", error);
        // Fallback: bot folds on error
        let newState = processPlayerAction(gameState, gameState.currentTurnIndex, "fold");
        const nextIndex = getNextActivePlayerIndex(newState);
        if (nextIndex >= 0) {
          newState.currentTurnIndex = nextIndex;
        } else {
          newState = advanceToNextRound(newState);
        }
        setGameState(newState);
      } finally {
        setIsProcessing(false);
        setBotThinking((prev) => {
          const next = new Set(prev);
          next.delete(currentPlayer.id);
          return next;
        });
        isActionInProgressRef.current = false;
      }
    };

    handleBotTurn();
  }, [gameState?.currentTurnIndex, gameState?.currentRound, contract, contractDeployed, botGameIds]);

  const handlePlayerAction = useCallback(
    (action: "fold" | "check" | "call" | "raise", raiseAmount?: number) => {
      if (isProcessing || isActionInProgressRef.current || !gameState) return;

      isActionInProgressRef.current = true;

      try {
        const humanPlayerIndex = gameState.players.findIndex((p) => p.isHuman);
        if (humanPlayerIndex === -1) return;

        let newState = processPlayerAction(gameState, humanPlayerIndex, action, raiseAmount);
        const bettingRoundComplete = isBettingRoundComplete(newState);

        if (bettingRoundComplete) {
          newState = advanceToNextRound(newState);
        } else {
          const nextIndex = getNextActivePlayerIndex(newState);
          if (nextIndex >= 0) {
            newState.currentTurnIndex = nextIndex;
          } else {
            newState = advanceToNextRound(newState);
          }
        }

        setGameState(newState);
      } finally {
        setTimeout(() => {
          isActionInProgressRef.current = false;
          setIsProcessing(false);
        }, 0);
      }
    },
    [gameState, isProcessing]
  );

  const handleNextHand = useCallback(() => {
    if (!gameState) return;
    initialBalancesRef.current = gameState.players.map((p) => p.balance);
    const newState = startNewHand(gameState);
    setGameState(newState);
    setDealtCards(Array(3).fill(true));
    setShowNextHandButton(false);
    setBotGameIds(new Map());
  }, [gameState]);

  // Determine winners at showdown
  useEffect(() => {
    if (!gameState || gameState.currentRound !== "showdown" || gameState.isHandComplete) return;

    const newState = determineWinners(gameState);
    setGameState(newState);
    setShowNextHandButton(true);
  }, [gameState?.currentRound, gameState?.isHandComplete]);

  if (isDeploying) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <Card className="bg-white/90 max-w-md">
          <CardContent className="p-6">
            <div className="flex flex-col items-center space-y-4">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              <h2 className="text-xl font-bold">Deploying Contract...</h2>
              <p className="text-sm text-gray-600 text-center">
                Please wait while we deploy the poker player contract.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (deploymentError) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <Card className="bg-white/90 max-w-md">
          <CardContent className="p-6">
            <Alert variant="destructive">
              <AlertDescription>
                <h2 className="text-xl font-bold mb-2">Deployment Error</h2>
                <p>{deploymentError}</p>
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!gameState) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <Card className="bg-white/90 max-w-md">
          <CardContent className="p-6">
            <div className="flex flex-col items-center space-y-4">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              <h2 className="text-xl font-bold">Loading Game...</h2>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const humanPlayer = gameState.players.find((p) => p.isHuman);
  const humanPlayerHand = humanPlayer
    ? evaluateHand(humanPlayer.hand, gameState.communityCards).name
    : null;
  const isHumanTurn =
    humanPlayer &&
    gameState.currentTurnIndex === gameState.players.indexOf(humanPlayer) &&
    !gameState.isHandComplete &&
    gameState.currentRound !== "showdown";

  const roundLabels: Record<string, string> = {
    preflop: "Preflop",
    flop: "Flop",
    turn: "Turn",
    river: "River",
    showdown: "Showdown",
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex flex-col overflow-hidden">
      <div className="p-2 md:p-4 flex justify-between items-center flex-shrink-0">
        <h1 className="text-xl md:text-2xl font-bold text-white">Poker AI Game</h1>
        <div className="text-white text-sm">
          Round: {roundLabels[gameState.currentRound] || gameState.currentRound}
        </div>
      </div>

      <div className="flex-1 flex items-start justify-center min-h-0 overflow-hidden pt-2">
        <Table
          pot={gameState.pot}
          currentRound={gameState.currentRound}
          lastBetAmount={gameState.currentBet}
          communityCards={gameState.communityCards}
          visibleCards={gameState.communityCards.length}
          players={gameState.players}
          turnHolder={gameState.players[gameState.currentTurnIndex]?.chair || 0}
          humanPlayerHand={humanPlayerHand || ""}
          dealtCards={dealtCards}
          userAddress={accountAddress || ""}
        />
      </div>

      <div className="p-4 flex-shrink-0">
        {isHumanTurn ? (
          <BettingControls
            onFold={() => handlePlayerAction("fold")}
            onCheck={() => handlePlayerAction("check")}
            onCall={() => handlePlayerAction("call")}
            onRaise={(amount) => handlePlayerAction("raise", amount)}
            currentBet={gameState.currentBet}
            playerBet={humanPlayer?.currentBet || 0}
            playerBalance={humanPlayer?.balance || 0}
            isLoading={isProcessing}
          />
        ) : (
          <div className="text-center text-white">
            {botThinking.size > 0 ? (
              <div className="flex items-center justify-center gap-2">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Bot is thinking...</span>
              </div>
            ) : (
              <span>Waiting for your turn...</span>
            )}
          </div>
        )}

        {showNextHandButton && (
          <div className="mt-4 flex justify-center">
            <Button onClick={handleNextHand} className="bg-blue-600 hover:bg-blue-700">
              Next Hand
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

