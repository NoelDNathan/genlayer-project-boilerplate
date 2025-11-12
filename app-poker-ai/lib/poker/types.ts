export interface ICard {
  suit: string;
  rank: string;
}

export type HandCategory =
  | "Royal Flush"
  | "Straight Flush"
  | "Four of a Kind"
  | "Full House"
  | "Flush"
  | "Straight"
  | "Three of a Kind"
  | "Two Pair"
  | "One Pair"
  | "High Card";

export interface HandEvaluation {
  name: HandCategory;
  category: number;
  bestFive: ICard[];
  score: bigint;
  tiebreaker: number[];
}

