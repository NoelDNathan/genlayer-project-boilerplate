import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { ICard } from "./poker/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Converts an array of ICard to the string format expected by the contract.
 * Format: "♠A♥K" (suit + rank for each card)
 */
export function cardsToString(cards: ICard[]): string {
  return cards.map((card) => `${card.suit}${card.rank}`).join("");
}

/**
 * Generates a random Ethereum address for bot players.
 */
export function generateRandomAddress(): string {
  const chars = "0123456789abcdef";
  let address = "0x";
  for (let i = 0; i < 40; i++) {
    address += chars[Math.floor(Math.random() * chars.length)];
  }
  return address;
}

