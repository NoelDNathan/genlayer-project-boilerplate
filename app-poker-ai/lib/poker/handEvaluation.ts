import { ICard, HandCategory, HandEvaluation } from "./types";

const RANK_ORDER = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"];
const RANK_VALUE: Record<string, number> = Object.fromEntries(
  RANK_ORDER.map((r, i) => [r, i + 2])
);

const CATEGORY_WEIGHT: Record<HandCategory, number> = {
  "Royal Flush": 9,
  "Straight Flush": 8,
  "Four of a Kind": 7,
  "Full House": 6,
  Flush: 5,
  Straight: 4,
  "Three of a Kind": 3,
  "Two Pair": 2,
  "One Pair": 1,
  "High Card": 0,
};

function valueOf(card: ICard): number {
  return RANK_VALUE[card.rank] ?? 0;
}

function sortByRankDesc(cards: ICard[]): ICard[] {
  return [...cards].sort((a, b) => valueOf(b) - valueOf(a));
}

function groupByRank(cards: ICard[]): Map<number, ICard[]> {
  const map = new Map<number, ICard[]>();
  for (const c of cards) {
    const v = valueOf(c);
    const arr = map.get(v) ?? [];
    arr.push(c);
    map.set(v, arr);
  }
  return new Map([...map.entries()].sort((a, b) => b[0] - a[0]));
}

function groupBySuit(cards: ICard[]): Map<string, ICard[]> {
  const map = new Map<string, ICard[]>();
  for (const c of cards) {
    const arr = map.get(c.suit) ?? [];
    arr.push(c);
    map.set(c.suit, arr);
  }
  return map;
}

function findStraight(cards: ICard[]): ICard[] | null {
  const byValue = new Map<number, ICard>();
  for (const c of sortByRankDesc(cards)) {
    const v = valueOf(c);
    if (!byValue.has(v)) byValue.set(v, c);
  }
  const uniqueDesc = [...byValue.keys()].sort((a, b) => b - a);

  const hasA = byValue.has(14);
  const has2 = byValue.has(2);
  const has3 = byValue.has(3);
  const has4 = byValue.has(4);
  const has5 = byValue.has(5);
  if (hasA && has2 && has3 && has4 && has5) {
    return [
      byValue.get(5)!,
      byValue.get(4)!,
      byValue.get(3)!,
      byValue.get(2)!,
      byValue.get(14)!,
    ];
  }

  let run: ICard[] = [];
  for (let i = 0; i < uniqueDesc.length; i++) {
    if (run.length === 0) {
      run.push(byValue.get(uniqueDesc[i])!);
      continue;
    }
    const prev = valueOf(run[run.length - 1]);
    const cur = uniqueDesc[i];
    if (cur === prev - 1) {
      run.push(byValue.get(cur)!);
    } else if (cur !== prev) {
      run = [byValue.get(cur)!];
    }
    if (run.length === 5) return run;
  }
  return null;
}

function findStraightFlush(cards: ICard[]): ICard[] | null {
  const bySuit = groupBySuit(cards);
  for (const [, suited] of bySuit.entries()) {
    if (suited.length >= 5) {
      const straightFlush = findStraight(suited);
      if (straightFlush) return straightFlush;
    }
  }
  return null;
}

function pickBestFlush(cards: ICard[]): ICard[] | null {
  const bySuit = groupBySuit(cards);
  for (const [, suited] of bySuit.entries()) {
    if (suited.length >= 5) {
      return sortByRankDesc(suited).slice(0, 5);
    }
  }
  return null;
}

function buildScore(category: number, tiebreaker: number[]): bigint {
  let score = BigInt(category) * 10_000_000_000_000n;
  const basePows = [10_000_000_000n, 100_000_000n, 1_000_000n, 10_000n, 100n, 1n];
  for (let i = 0; i < Math.min(tiebreaker.length, basePows.length); i++) {
    score += BigInt(tiebreaker[i]) * BigInt(basePows[i]);
  }
  return score;
}

export function evaluateHand(
  privateCards: ICard[],
  communityCards: ICard[]
): HandEvaluation {
  const cards = sortByRankDesc([...privateCards, ...communityCards]).slice(0, 7);
  if (cards.length === 0) {
    return {
      name: "High Card",
      category: CATEGORY_WEIGHT["High Card"],
      bestFive: [],
      score: 0n,
      tiebreaker: [],
    };
  }

  const sf = findStraightFlush(cards);
  if (sf) {
    const isRoyal =
      sf.some((c) => c.rank === "A") &&
      sf.some((c) => c.rank === "K") &&
      sf.some((c) => c.rank === "Q") &&
      sf.some((c) => c.rank === "J") &&
      sf.some((c) => c.rank === "10");
    const name: HandCategory = isRoyal ? "Royal Flush" : "Straight Flush";
    const category = CATEGORY_WEIGHT[name];
    const high = isRoyal ? 14 : Math.max(...sf.map(valueOf));
    const tiebreaker = [high];
    return { name, category, bestFive: sf, score: buildScore(category, tiebreaker), tiebreaker };
  }

  const byRank = groupByRank(cards);
  const quadsEntry = [...byRank.entries()].find(([, arr]) => arr.length === 4);
  if (quadsEntry) {
    const quadVal = quadsEntry[0];
    const quadCards = quadsEntry[1];
    const kickers = sortByRankDesc(cards.filter((c) => valueOf(c) !== quadVal));
    const bestFive = [...quadCards, kickers[0]];
    const name: HandCategory = "Four of a Kind";
    const category = CATEGORY_WEIGHT[name];
    const tiebreaker = [quadVal, valueOf(kickers[0])];
    return { name, category, bestFive, score: buildScore(category, tiebreaker), tiebreaker };
  }

  const trips = [...byRank.entries()]
    .filter(([, arr]) => arr.length === 3)
    .map(([v, arr]) => ({ v, arr }));
  const pairs = [...byRank.entries()]
    .filter(([, arr]) => arr.length === 2)
    .map(([v, arr]) => ({ v, arr }));
  if (trips.length >= 1 && (pairs.length >= 1 || trips.length >= 2)) {
    const bestTrip = trips.sort((a, b) => b.v - a.v)[0];
    const remainingForPair = [
      ...pairs.map((p) => ({ v: p.v, arr: p.arr })),
      ...trips
        .filter((t) => t.v !== bestTrip.v)
        .map((t) => ({ v: t.v, arr: t.arr.slice(0, 2) })),
    ].sort((a, b) => b.v - a.v);
    if (remainingForPair.length >= 1) {
      const bestPair = remainingForPair[0];
      const bestFive = [...bestTrip.arr, ...bestPair.arr.slice(0, 2)];
      const name: HandCategory = "Full House";
      const category = CATEGORY_WEIGHT[name];
      const tiebreaker = [bestTrip.v, bestPair.v];
      return { name, category, bestFive, score: buildScore(category, tiebreaker), tiebreaker };
    }
  }

  const flush = pickBestFlush(cards);
  if (flush) {
    const name: HandCategory = "Flush";
    const category = CATEGORY_WEIGHT[name];
    const tiebreaker = flush.map(valueOf);
    return { name, category, bestFive: flush, score: buildScore(category, tiebreaker), tiebreaker };
  }

  const straight = findStraight(cards);
  if (straight) {
    const name: HandCategory = "Straight";
    const category = CATEGORY_WEIGHT[name];
    let high = Math.max(...straight.map(valueOf));
    const ranksSet = new Set(straight.map(valueOf));
    if (ranksSet.has(14) && ranksSet.has(5)) high = 5;
    const tiebreaker = [high];
    return { name, category, bestFive: straight, score: buildScore(category, tiebreaker), tiebreaker };
  }

  if (trips.length >= 1) {
    const bestTrip = trips.sort((a, b) => b.v - a.v)[0];
    const kickers = sortByRankDesc(cards.filter((c) => valueOf(c) !== bestTrip.v)).slice(0, 2);
    const bestFive = [...bestTrip.arr, ...kickers];
    const name: HandCategory = "Three of a Kind";
    const category = CATEGORY_WEIGHT[name];
    const tiebreaker = [bestTrip.v, ...kickers.map(valueOf)];
    return { name, category, bestFive, score: buildScore(category, tiebreaker), tiebreaker };
  }

  if (pairs.length >= 2) {
    const [highPair, lowPair] = pairs.sort((a, b) => b.v - a.v).slice(0, 2);
    const kickers = sortByRankDesc(
      cards.filter((c) => ![highPair.v, lowPair.v].includes(valueOf(c)))
    ).slice(0, 1);
    const bestFive = [...highPair.arr, ...lowPair.arr, ...kickers];
    const name: HandCategory = "Two Pair";
    const category = CATEGORY_WEIGHT[name];
    const tiebreaker = [highPair.v, lowPair.v, valueOf(kickers[0])];
    return { name, category, bestFive, score: buildScore(category, tiebreaker), tiebreaker };
  }

  if (pairs.length === 1) {
    const [pair] = pairs;
    const kickers = sortByRankDesc(cards.filter((c) => valueOf(c) !== pair.v)).slice(0, 3);
    const bestFive = [...pair.arr, ...kickers];
    const name: HandCategory = "One Pair";
    const category = CATEGORY_WEIGHT[name];
    const tiebreaker = [pair.v, ...kickers.map(valueOf)];
    return { name, category, bestFive, score: buildScore(category, tiebreaker), tiebreaker };
  }

  const bestFive = sortByRankDesc(cards).slice(0, 5);
  const name: HandCategory = "High Card";
  const category = CATEGORY_WEIGHT[name];
  const tiebreaker = bestFive.map(valueOf);
  return { name, category, bestFive, score: buildScore(category, tiebreaker), tiebreaker };
}

export function compareEvaluations(a: HandEvaluation, b: HandEvaluation): number {
  if (a.score === b.score) return 0;
  return a.score > b.score ? 1 : -1;
}

