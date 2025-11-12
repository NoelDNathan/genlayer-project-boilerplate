import { ICard } from "./types";
import { GameMode } from "./gameState";

const SUITS = ["♠", "♥", "♦", "♣"];
const RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"];

export function createDeck(): ICard[] {
  const deck: ICard[] = [];
  for (const suit of SUITS) {
    for (const rank of RANKS) {
      deck.push({ suit, rank });
    }
  }
  return deck;
}

export function shuffleDeck(deck: ICard[]): ICard[] {
  const shuffled = [...deck];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

export function dealCards(
  deck: ICard[],
  numPlayers: number,
  numCardsPerPlayer: number
): { hands: ICard[][]; remainingDeck: ICard[] } {
  const hands: ICard[][] = Array.from({ length: numPlayers }, () => []);
  let deckIndex = 0;

  for (let cardIndex = 0; cardIndex < numCardsPerPlayer; cardIndex++) {
    for (let playerIndex = 0; playerIndex < numPlayers; playerIndex++) {
      hands[playerIndex].push(deck[deckIndex++]);
    }
  }

  return { hands, remainingDeck: deck.slice(deckIndex) };
}

export function dealCommunityCards(deck: ICard[], count: number): {
  cards: ICard[];
  remainingDeck: ICard[];
} {
  return { cards: deck.slice(0, count), remainingDeck: deck.slice(count) };
}

// Cooler scenarios: Player gets strong hand but loses
const COOLER_SCENARIOS = [
  {
    // Specific 3-player cooler scenario
    playerHand: [
      { suit: "♥", rank: "2" },
      { suit: "♠", rank: "A" },
    ],
    botHands: [
      [
        { suit: "♠", rank: "10" },
        { suit: "♣", rank: "10" },
      ],
      [
        { suit: "♠", rank: "6" },
        { suit: "♦", rank: "7" },
      ],
    ],
    communityCards: [
      { suit: "♣", rank: "A" },
      { suit: "♠", rank: "2" },
      { suit: "♦", rank: "2" },
      { suit: "♦", rank: "10" },
      { suit: "♥", rank: "10" },
    ],
  },
  {
    playerHand: [
      { suit: "♠", rank: "K" },
      { suit: "♥", rank: "K" },
    ],
    botHand: [
      { suit: "♠", rank: "A" },
      { suit: "♥", rank: "A" },
    ],
    communityCards: [
      { suit: "♦", rank: "10" },
      { suit: "♣", rank: "9" },
      { suit: "♠", rank: "8" },
      { suit: "♥", rank: "7" },
      { suit: "♦", rank: "6" },
    ],
  },
  {
    playerHand: [
      { suit: "♠", rank: "A" },
      { suit: "♠", rank: "K" },
    ],
    botHand: [
      { suit: "♠", rank: "A" },
      { suit: "♠", rank: "A" },
    ],
    communityCards: [
      { suit: "♠", rank: "Q" },
      { suit: "♠", rank: "J" },
      { suit: "♠", rank: "10" },
      { suit: "♥", rank: "5" },
      { suit: "♦", rank: "3" },
    ],
  },
];

// Epic win scenarios: Player gets premium hand
const EPIC_SCENARIOS = [
  {
    playerHand: [
      { suit: "♠", rank: "A" },
      { suit: "♠", rank: "K" },
    ],
    communityCards: [
      { suit: "♠", rank: "Q" },
      { suit: "♠", rank: "J" },
      { suit: "♠", rank: "10" },
      { suit: "♥", rank: "5" },
      { suit: "♦", rank: "3" },
    ],
  },
  {
    playerHand: [
      { suit: "♠", rank: "10" },
      { suit: "♠", rank: "J" },
    ],
    communityCards: [
      { suit: "♠", rank: "Q" },
      { suit: "♠", rank: "K" },
      { suit: "♠", rank: "A" },
      { suit: "♥", rank: "5" },
      { suit: "♦", rank: "3" },
    ],
  },
];

function getRandomCards(deck: ICard[], count: number): { cards: ICard[]; remaining: ICard[] } {
  const cards: ICard[] = [];
  const remaining: ICard[] = [];
  const used = new Set<number>();

  for (let i = 0; i < count; i++) {
    let index;
    do {
      index = Math.floor(Math.random() * deck.length);
    } while (used.has(index));
    used.add(index);
    cards.push(deck[index]);
  }

  for (let i = 0; i < deck.length; i++) {
    if (!used.has(i)) {
      remaining.push(deck[i]);
    }
  }

  return { cards, remaining };
}

export function dealModeSpecificCards(
  mode: GameMode,
  isFirstHand: boolean,
  numBots: number
): {
  playerHand: ICard[];
  botHands: ICard[][];
  communityCards: ICard[];
} | null {
  if (!isFirstHand) {
    return null;
  }

  if (mode === "cooler") {
    // Always use the first scenario (3-player specific cooler scenario)
    const scenario = COOLER_SCENARIOS[0];
    
    // Check if scenario has botHands array (for 3-player specific scenarios)
    if (scenario.botHands && Array.isArray(scenario.botHands)) {
      return {
        playerHand: scenario.playerHand,
        botHands: scenario.botHands,
        communityCards: scenario.communityCards,
      };
    }
    
    // Fallback to old format with single botHand
    if (scenario.botHand) {
      const botHands: ICard[][] = [scenario.botHand];
      for (let i = 1; i < numBots; i++) {
        const deck = shuffleDeck(createDeck());
        const usedCards = new Set<string>();
        [
          ...scenario.playerHand,
          ...scenario.botHand,
          ...scenario.communityCards,
        ].forEach((card) => {
          usedCards.add(`${card.suit}-${card.rank}`);
        });
        const available = deck.filter(
          (card) => !usedCards.has(`${card.suit}-${card.rank}`)
        );
        botHands.push([available[0], available[1]]);
      }
      return {
        playerHand: scenario.playerHand,
        botHands,
        communityCards: scenario.communityCards,
      };
    }
  }

  if (mode === "epic") {
    const scenario = EPIC_SCENARIOS[Math.floor(Math.random() * EPIC_SCENARIOS.length)];
    const deck = shuffleDeck(createDeck());
    const usedCards = new Set<string>();
    [...scenario.playerHand, ...scenario.communityCards].forEach((card) => {
      usedCards.add(`${card.suit}-${card.rank}`);
    });
    const available = deck.filter(
      (card) => !usedCards.has(`${card.suit}-${card.rank}`)
    );

    const botHands: ICard[][] = [];
    for (let i = 0; i < numBots; i++) {
      botHands.push([available[i * 2], available[i * 2 + 1]]);
    }

    return {
      playerHand: scenario.playerHand,
      botHands,
      communityCards: scenario.communityCards,
    };
  }

  return null;
}

