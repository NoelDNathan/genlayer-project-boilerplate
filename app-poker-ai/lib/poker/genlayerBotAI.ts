import { ICard } from "./types";
import { GameState, Player } from "./gameState";
import { PokerPlayer, GetActionResult } from "../PokerPlayer";
import { cardsToString } from "../utils";

export interface BotDecision {
  action: "fold" | "check" | "call" | "raise" | "all-in";
  raiseAmount?: number;
}

/**
 * Calculate player position relative to dealer for contract
 * Position mapping: 0=UTG, 1=UTG+1, 2=MP, 3=MP+1, 4=Cutoff, 5=Button, 6=SB, 7=BB
 */
function calculatePosition(playerIndex: number, dealerPosition: number, numPlayers: number): number {
  // Calculate relative position (how many seats after dealer)
  let relativePos = (playerIndex - dealerPosition - 1 + numPlayers) % numPlayers;
  
  // Map to contract position (0-7)
  // For 3 players: positions are typically Button (5), SB (6), BB (7)
  if (numPlayers === 3) {
    if (relativePos === 0) return 5; // Button
    if (relativePos === 1) return 6; // Small Blind
    if (relativePos === 2) return 7; // Big Blind
  }
  
  // For more players, map more positions
  // This is a simplified mapping - adjust based on actual table structure
  return Math.min(relativePos, 7);
}

/**
 * Get bot action from GenLayer contract
 */
export async function getBotActionFromGenLayer(
  bot: Player,
  gameState: GameState,
  contract: PokerPlayer,
  botGameId: string | null
): Promise<{ decision: BotDecision; gameId: string | null }> {
  try {
    // If no game_id exists, create a new game first
    if (!botGameId) {
      const playerHand = cardsToString(bot.hand);
      const boardCards = cardsToString(gameState.communityCards);
      const position = calculatePosition(bot.id, gameState.dealerPosition, gameState.players.length);
      
      // Calculate current bet for this bot (how much more they need to call)
      const botCurrentBet = bot.currentBet;
      const amountToCall = gameState.currentBet - botCurrentBet;
      
      console.log(`[GenLayerBotAI] Creating game for ${bot.name}:`, {
        hand: playerHand,
        board: boardCards,
        position,
        stack: bot.balance,
        currentBet: amountToCall,
      });

      const createResult = await contract.createGame(
        `0x${bot.id.toString().padStart(40, '0')}`, // Bot address (simplified)
        playerHand,
        position,
        gameState.players.length,
        gameState.pot,
        10, // Small blind
        20, // Big blind
        bot.balance,
        amountToCall
      );

      botGameId = createResult.game_id;
      console.log(`[GenLayerBotAI] Created game ${botGameId} for ${bot.name}`);
    } else {
      // Update the game state if needed (when new cards are dealt or pot changes)
      const boardCards = cardsToString(gameState.communityCards);
      const botCurrentBet = bot.currentBet;
      const amountToCall = gameState.currentBet - botCurrentBet;
      
      // Determine stage from community cards
      const cardCount = gameState.communityCards.length;
      let stage = "preflop";
      if (cardCount === 3) stage = "flop";
      else if (cardCount === 4) stage = "turn";
      else if (cardCount === 5) stage = "river";

      // Get current game state to check if update is needed
      const currentState = await contract.getGameState(botGameId);
      
      // Update if board cards changed or pot/bet changed significantly
      if (
        currentState.board_cards !== boardCards ||
        Math.abs(currentState.pot_size - gameState.pot) > 1 ||
        Math.abs(currentState.current_bet - amountToCall) > 1
      ) {
        console.log(`[GenLayerBotAI] Updating game ${botGameId} for ${bot.name}`);
        await contract.updateStage(
          botGameId,
          boardCards,
          gameState.pot,
          amountToCall,
          bot.balance
        );
      }
    }

    // Get action recommendation from contract
    console.log(`[GenLayerBotAI] Getting action for ${bot.name} (game: ${botGameId})`);
    const actionResult: GetActionResult = await contract.getAction(botGameId);

    // Map contract action to game engine action
    const action = actionResult.action.toLowerCase();
    let botDecision: BotDecision;

    if (action === "fold") {
      botDecision = { action: "fold" };
    } else if (action === "check") {
      botDecision = { action: "check" };
    } else if (action === "call") {
      botDecision = { action: "call" };
    } else if (action === "raise") {
      botDecision = { 
        action: "raise", 
        raiseAmount: actionResult.amount 
      };
    } else if (action === "all-in") {
      botDecision = { 
        action: "raise", 
        raiseAmount: bot.balance + bot.currentBet // All-in amount
      };
    } else {
      // Fallback to call if unknown action
      console.warn(`[GenLayerBotAI] Unknown action "${action}", defaulting to call`);
      botDecision = { action: "call" };
    }

    console.log(`[GenLayerBotAI] ${bot.name} decision:`, botDecision);
    return { decision: botDecision, gameId: botGameId };

  } catch (error) {
    console.error(`[GenLayerBotAI] Error getting action for ${bot.name}:`, error);
      // Fallback to simple call/check logic
      const amountToCall = gameState.currentBet - bot.currentBet;
      if (amountToCall === 0) {
        return { decision: { action: "check" }, gameId: botGameId };
      }
      return { decision: { action: "call" }, gameId: botGameId };
  }
}

