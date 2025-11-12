import { GameState, Player } from "./gameState";
import { ICard } from "./types";
import { evaluateHand, compareEvaluations } from "./handEvaluation";
import {
  createDeck,
  shuffleDeck,
  dealCards,
  dealCommunityCards,
  dealModeSpecificCards,
} from "./cardDealer";

const SMALL_BLIND = 10;
const BIG_BLIND = 20;

export type BotAction = "fold" | "check" | "call" | "raise";

export function startNewHand(gameState: GameState): GameState {
  const newState = { ...gameState };
  newState.handNumber += 1;
  newState.currentRound = "preflop";
  newState.pot = 0;
  newState.currentBet = 0;
  newState.isHandComplete = false;
  newState.winners = [];
  newState.communityCards = [];

  // Reset players
  newState.players = newState.players.map((player) => ({
    ...player,
    hand: [],
    currentBet: 0,
    folded: false,
    inGame: true,
    isAllIn: false,
  }));

  // Rotate dealer
  newState.dealerPosition = (newState.dealerPosition + 1) % newState.players.length;

  // Deal cards
  const isFirstHand = !newState.firstHandPlayed;
  const modeSpecific = dealModeSpecificCards(
    newState.gameMode,
    isFirstHand,
    newState.players.filter((p) => !p.isHuman).length
  );

  if (modeSpecific) {
    // Use mode-specific dealing
    const humanPlayerIndex = newState.players.findIndex((p) => p.isHuman);
    if (humanPlayerIndex >= 0) {
      newState.players[humanPlayerIndex].hand = modeSpecific.playerHand;
    }
    let botIndex = 0;
    for (let i = 0; i < newState.players.length; i++) {
      if (!newState.players[i].isHuman) {
        newState.players[i].hand = modeSpecific.botHands[botIndex++];
      }
    }
    newState.communityCards = modeSpecific.communityCards;
    newState.firstHandPlayed = true;
  } else {
    // Normal random dealing
    const deck = shuffleDeck(createDeck());
    const { hands } = dealCards(deck, newState.players.length, 2);
    newState.players = newState.players.map((player, index) => ({
      ...player,
      hand: hands[index],
    }));

    // Deal community cards will happen in betting rounds
  }

  // Post blinds
  const smallBlindIndex = (newState.dealerPosition + 1) % newState.players.length;
  const bigBlindIndex = (newState.dealerPosition + 2) % newState.players.length;

  const smallBlindPlayer = newState.players[smallBlindIndex];
  const bigBlindPlayer = newState.players[bigBlindIndex];

  const smallBlindAmount = Math.min(SMALL_BLIND, smallBlindPlayer.balance);
  const bigBlindAmount = Math.min(BIG_BLIND, bigBlindPlayer.balance);

  smallBlindPlayer.balance -= smallBlindAmount;
  smallBlindPlayer.currentBet = smallBlindAmount;
  bigBlindPlayer.balance -= bigBlindAmount;
  bigBlindPlayer.currentBet = bigBlindAmount;

  // Check if players went all-in with blinds
  if (smallBlindPlayer.balance === 0) {
    smallBlindPlayer.isAllIn = true;
  }
  if (bigBlindPlayer.balance === 0) {
    bigBlindPlayer.isAllIn = true;
  }

  newState.pot = smallBlindAmount + bigBlindAmount;
  newState.currentBet = bigBlindAmount;

  // Reset counter: number of active players (not all-in) that need to act
  newState.playersToActInRound = newState.players.filter(
    (p) => !p.folded && p.inGame && !p.isAllIn
  ).length;

  // Start with player after big blind (first active player)
  newState.currentTurnIndex = (bigBlindIndex + 1) % newState.players.length;
  const nextActive = getNextActivePlayerIndexFromPosition(newState, bigBlindIndex);
  if (nextActive >= 0) {
    newState.currentTurnIndex = nextActive;
  }

  return newState;
}

export function processPlayerAction(
  gameState: GameState,
  playerIndex: number,
  action: BotAction,
  raiseAmount?: number
): GameState {
  const newState = { ...gameState };
  const player = newState.players[playerIndex];

  if (player.folded || player.isAllIn) {
    return newState;
  }

  const newBet = newState.currentBet - player.currentBet;

  switch (action) {
    case "fold":
      player.folded = true;
      player.inGame = false;
      newState.playersToActInRound--;
      break;

    case "check":
      if (newBet > 0) {
        throw new Error("Cannot check when there is a bet");
      }
      newState.playersToActInRound--;
      break;

    case "call":
      if (newBet === 0) {
        // Actually a check
        newState.playersToActInRound--;
        break;
      }
      const callAmount = Math.min(newBet, player.balance);
      player.balance -= callAmount;
      player.currentBet += callAmount;
      newState.pot += callAmount;
      newState.playersToActInRound--;
      if (player.balance === 0) {
        player.isAllIn = true;
      }
      break;

    case "raise":
      if (!raiseAmount || raiseAmount <= newState.currentBet) {
        throw new Error("Invalid raise amount");
      }
      const totalNeeded = raiseAmount - player.currentBet;
      const raiseCallAmount = Math.min(totalNeeded, player.balance);
      player.balance -= raiseCallAmount;
      player.currentBet = raiseAmount;
      newState.pot += raiseCallAmount;
      newState.currentBet = raiseAmount;
      // Reset counter when someone raises - all active players need to act again
      newState.playersToActInRound = newState.players.filter(
        (p) => !p.folded && p.inGame && (p.currentBet < raiseAmount && !p.isAllIn)
      ).length;
      // Decrement because the raiser just acted
      if (player.balance === 0) {
        player.isAllIn = true;
      }
      break;
  }

  return newState;
}

export function advanceToNextRound(gameState: GameState): GameState {
  const newState = { ...gameState };

  if (newState.currentRound === "preflop") {
    newState.currentRound = "flop";
    if (newState.communityCards.length === 0) {
      // Only deal if we don't already have community cards (normal mode)
      const deck = shuffleDeck(createDeck());
      const usedCards = new Set<string>();
      newState.players.forEach((p) => {
        p.hand.forEach((c) => usedCards.add(`${c.suit}-${c.rank}`));
      });
      const available = deck.filter((c) => !usedCards.has(`${c.suit}-${c.rank}`));
      const { cards } = dealCommunityCards(available, 3);
      newState.communityCards = cards;
    }
    newState.currentBet = 0;
    newState.players.forEach((p) => {
      p.currentBet = 0;
    });
    // Reset counter: number of active players (not all-in) that need to act
    newState.playersToActInRound = newState.players.filter(
      (p) => !p.folded && p.inGame && !p.isAllIn
    ).length;
    // Start from player after dealer, but find the first active player
    newState.currentTurnIndex = (newState.dealerPosition + 1) % newState.players.length;
    const nextActive = getNextActivePlayerIndexFromPosition(newState, newState.dealerPosition);
    if (nextActive >= 0) {
      newState.currentTurnIndex = nextActive;
    }
  } else if (newState.currentRound === "flop") {
    newState.currentRound = "turn";
    if (newState.communityCards.length < 4) {
      // Only deal if we don't already have the turn card (normal mode)
      const deck = shuffleDeck(createDeck());
      const usedCards = new Set<string>();
      newState.players.forEach((p) => {
        p.hand.forEach((c) => usedCards.add(`${c.suit}-${c.rank}`));
      });
      newState.communityCards.forEach((c) => usedCards.add(`${c.suit}-${c.rank}`));
      const available = deck.filter((c) => !usedCards.has(`${c.suit}-${c.rank}`));
      const { cards } = dealCommunityCards(available, 1);
      newState.communityCards.push(cards[0]);
    }
    newState.currentBet = 0;
    newState.players.forEach((p) => {
      p.currentBet = 0;
    });
    // Reset counter: number of active players (not all-in) that need to act
    newState.playersToActInRound = newState.players.filter(
      (p) => !p.folded && p.inGame && !p.isAllIn
    ).length;
    // Start from player after dealer, but find the first active player
    newState.currentTurnIndex = (newState.dealerPosition + 1) % newState.players.length;
    const nextActive = getNextActivePlayerIndexFromPosition(newState, newState.dealerPosition);
    if (nextActive >= 0) {
      newState.currentTurnIndex = nextActive;
    }
  } else if (newState.currentRound === "turn") {
    newState.currentRound = "river";
    if (newState.communityCards.length < 5) {
      // Only deal if we don't already have the river card (normal mode)
      const deck = shuffleDeck(createDeck());
      const usedCards = new Set<string>();
      newState.players.forEach((p) => {
        p.hand.forEach((c) => usedCards.add(`${c.suit}-${c.rank}`));
      });
      newState.communityCards.forEach((c) => usedCards.add(`${c.suit}-${c.rank}`));
      const available = deck.filter((c) => !usedCards.has(`${c.suit}-${c.rank}`));
      const { cards } = dealCommunityCards(available, 1);
      newState.communityCards.push(cards[0]);
    }

    // Reset counter: number of active players (not all-in) that need to act
    newState.playersToActInRound = newState.players.filter(
      (p) => !p.folded && p.inGame && !p.isAllIn
    ).length;
    // Start from player after dealer, but find the first active player
    newState.currentTurnIndex = (newState.dealerPosition + 1) % newState.players.length;
    const nextActive = getNextActivePlayerIndexFromPosition(newState, newState.dealerPosition);
    if (nextActive >= 0) {
      newState.currentBet = 0;
      newState.players.forEach((p) => {
        p.currentBet = 0;
      });
      newState.currentTurnIndex = nextActive;
    }
  } else if (newState.currentRound === "river") {
    newState.currentRound = "showdown";
    newState.isHandComplete = true;
  }

  return newState;
}

export function determineWinners(gameState: GameState, skipPotDistribution: boolean = false): GameState {
  const newState = { ...gameState };
  const activePlayers = newState.players.filter((p) => !p.folded && p.inGame);

  if (activePlayers.length === 0) {
    newState.isHandComplete = true;
    return newState;
  }

  const evaluations = activePlayers.map((player) => ({
    playerIndex: player.id,
    evaluation: evaluateHand(player.hand, newState.communityCards),
  }));

  evaluations.sort((a, b) => compareEvaluations(b.evaluation, a.evaluation));

  const bestScore = evaluations[0].evaluation.score;
  const winners = evaluations
    .filter((e) => e.evaluation.score === bestScore)
    .map((e) => e.playerIndex);

  newState.winners = winners;
  
  // Only distribute pot if not already distributed by contract
  if (!skipPotDistribution) {
    const potPerWinner = Math.floor(newState.pot / winners.length);
    const remainder = newState.pot % winners.length;

    winners.forEach((winnerId, index) => {
      const winner = newState.players.find((p) => p.id === winnerId);
      if (winner) {
        winner.balance += potPerWinner + (index < remainder ? 1 : 0);
      }
    });
  }

  newState.isHandComplete = true;
  return newState;
}

export function isBettingRoundComplete(gameState: GameState): boolean {
  const activePlayers = gameState.players.filter(
    (p) => !p.folded && (p.inGame || p.isAllIn)
  );

  if (activePlayers.length <= 1) {
    return true;
  }

  // Round is complete when counter reaches 0 (all active players have acted)
  return gameState.playersToActInRound <= 0;
}

// Helper function to find next active player from a given position
function getNextActivePlayerIndexFromPosition(gameState: GameState, startIndex: number): number {
  let currentIndex = startIndex;
  for (let i = 0; i < gameState.players.length; i++) {
    currentIndex = (currentIndex + 1) % gameState.players.length;
    const player = gameState.players[currentIndex];
    if (!player.folded && player.inGame && !player.isAllIn) {
      return currentIndex;
    }
  }

  return -1;
}

export function getNextActivePlayerIndex(gameState: GameState): number {
  return getNextActivePlayerIndexFromPosition(gameState, gameState.currentTurnIndex);
}

