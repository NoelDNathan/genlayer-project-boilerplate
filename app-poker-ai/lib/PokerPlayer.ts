"use client";

import { getClient, type Account } from "./genlayer";
import type { Address, TransactionHash } from "genlayer-js/types";
import { TransactionStatus } from "genlayer-js/types";

export interface GameState {
  game_id: string;
  player_address: string;
  player_hand: string;
  board_cards: string;
  player_position: number;
  num_players: number;
  pot_size: number;
  small_blind: number;
  big_blind: number;
  player_stack: number;
  current_bet: number;
  game_stage: string;
  last_action: string;
  game_active: boolean;
}

export interface CreateGameResult {
  game_id: string;
  player_address: string;
  game_stage: string;
  game_active: boolean;
}

export interface GetActionResult {
  game_id: string;
  action: string;
  amount: number;
  game_stage: string;
  game_active: boolean;
  player_stack: number;
  amount_deducted: number;
}

export interface UpdateStageResult {
  game_id: string;
  board_cards: string;
  pot_size: number;
  current_bet: number;
  game_stage: string;
  game_active: boolean;
  player_stack: number;
}

export class PokerPlayer {
  private contractAddress: string | null;
  private account: Account | null;
  private studioUrl?: string;

  constructor(contractAddress: string | null = null, account: Account | null = null, studioUrl?: string) {
    this.contractAddress = contractAddress;
    this.account = account;
    this.studioUrl = studioUrl;
  }

  updateAccount(account: Account | null) {
    this.account = account;
  }

  setContractAddress(address: string) {
    this.contractAddress = address;
  }

  private getClient() {
    if (!this.account) {
      throw new Error("Account is required for this operation. Please connect an account first.");
    }
    return getClient(this.account, this.studioUrl);
  }

  async deployContract(contractCode: Uint8Array): Promise<string> {
    console.log("[PokerPlayer] Starting contract deployment...");
    const client = this.getClient();
    
    try {
      console.log("[PokerPlayer] Initializing consensus smart contract...");
      await client.initializeConsensusSmartContract();

      console.log("[PokerPlayer] Deploying contract...");
      const deployTransaction = await client.deployContract({
        code: contractCode,
        args: [],
      });
      console.log("[PokerPlayer] Deployment transaction sent, hash:", deployTransaction);

      console.log("[PokerPlayer] Waiting for transaction receipt...");
      const receipt = await client.waitForTransactionReceipt({
        hash: deployTransaction as TransactionHash,
        status: TransactionStatus.ACCEPTED,
        retries: 200,
      });
      console.log("[PokerPlayer] Transaction receipt received");

      // Check status - handle both camelCase and snake_case formats
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const receiptAny = receipt as any;
      const statusName = receiptAny.statusName || receiptAny.status_name;
      if (
        statusName !== TransactionStatus.ACCEPTED &&
        statusName !== TransactionStatus.FINALIZED
      ) {
        throw new Error(`Deployment failed. Receipt: ${JSON.stringify(receipt)}`);
      }

      // Extract contract address - try multiple possible locations
      let deployedContractAddress: string | undefined;
      
      if (receiptAny.data?.contract_address) {
        deployedContractAddress = receiptAny.data.contract_address;
      } else if (receiptAny.txDataDecoded?.contractAddress) {
        deployedContractAddress = receiptAny.txDataDecoded.contractAddress;
      } else if (receiptAny.recipient) {
        deployedContractAddress = receiptAny.recipient;
      } else if (receiptAny.to_address) {
        deployedContractAddress = receiptAny.to_address;
      }

      if (!deployedContractAddress || typeof deployedContractAddress !== "string") {
        throw new Error(`Failed to get contract address from deployment receipt. Receipt: ${JSON.stringify(receipt)}`);
      }

      this.contractAddress = deployedContractAddress;
      console.log("[PokerPlayer] Contract deployed successfully at address:", deployedContractAddress);
      return deployedContractAddress;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Error during deployment: ${errorMessage}`);
    }
  }

  async createGame(
    playerAddress: string,
    playerHand: string,
    position: number,
    numPlayers: number,
    potSize: number,
    smallBlind: number,
    bigBlind: number,
    playerStack: number,
    currentBet: number
  ): Promise<CreateGameResult> {
    if (!this.contractAddress) {
      throw new Error("Contract address is required. Please deploy the contract first.");
    }

    console.log("[PokerPlayer] Creating game:", { 
      playerAddress,
      playerHand,
      position,
      numPlayers,
      potSize,
      contractAddress: this.contractAddress 
    });
    const client = this.getClient();
    
    try {
      const txHash = await client.writeContract({
        address: this.contractAddress as Address,
        functionName: "create_game",
        args: [
          playerAddress,
          playerHand,
          position,
          numPlayers,
          potSize,
          smallBlind,
          bigBlind,
          playerStack,
          currentBet,
        ],
        value: BigInt(0),
      });
      console.log("[PokerPlayer] create_game transaction sent, hash:", txHash);
      
      const receipt = await client.waitForTransactionReceipt({
        hash: txHash,
        status: TransactionStatus.FINALIZED,
        interval: 10000,
        retries: 20,
      });
      
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const receiptAny = receipt as any;
      const statusName = receiptAny.statusName || receiptAny.status_name;
      
      if (
        statusName !== TransactionStatus.ACCEPTED &&
        statusName !== TransactionStatus.FINALIZED
      ) {
        throw new Error(`Transaction failed with status: ${statusName}`);
      }

      // Get the result from the receipt
      const result = receiptAny.result || receiptAny.data;
      if (!result) {
        throw new Error("No result in transaction receipt");
      }

      return {
        game_id: result.game_id || "",
        player_address: result.player_address || playerAddress,
        game_stage: result.game_stage || "preflop",
        game_active: result.game_active !== false,
      };
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error("[PokerPlayer] Error creating game:", errorMessage);
      throw error;
    }
  }

  async getAction(gameId: string): Promise<GetActionResult> {
    if (!this.contractAddress) {
      throw new Error("Contract address is required. Please deploy the contract first.");
    }

    console.log("[PokerPlayer] Getting action for game:", gameId);
    const client = this.getClient();
    
    try {
      const txHash = await client.writeContract({
        address: this.contractAddress as Address,
        functionName: "get_action",
        args: [gameId],
        value: BigInt(0),
      });
      console.log("[PokerPlayer] get_action transaction sent, hash:", txHash);
      
      const receipt = await client.waitForTransactionReceipt({
        hash: txHash,
        status: TransactionStatus.FINALIZED,
        interval: 10000,
        retries: 20,
      });
      
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const receiptAny = receipt as any;
      const statusName = receiptAny.statusName || receiptAny.status_name;
      
      if (
        statusName !== TransactionStatus.ACCEPTED &&
        statusName !== TransactionStatus.FINALIZED
      ) {
        throw new Error(`Transaction failed with status: ${statusName}`);
      }

      const result = receiptAny.result || receiptAny.data;
      if (!result) {
        throw new Error("No result in transaction receipt");
      }

      return {
        game_id: result.game_id || gameId,
        action: result.action || "fold",
        amount: result.amount || 0,
        game_stage: result.game_stage || "preflop",
        game_active: result.game_active !== false,
        player_stack: result.player_stack || 0,
        amount_deducted: result.amount_deducted || 0,
      };
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error("[PokerPlayer] Error getting action:", errorMessage);
      throw error;
    }
  }

  async updateStage(
    gameId: string,
    boardCards: string,
    potSize: number,
    currentBet: number,
    playerStack?: number
  ): Promise<UpdateStageResult> {
    if (!this.contractAddress) {
      throw new Error("Contract address is required. Please deploy the contract first.");
    }

    console.log("[PokerPlayer] Updating stage for game:", gameId);
    const client = this.getClient();
    
    try {
      const args: any[] = [gameId, boardCards, potSize, currentBet];
      if (playerStack !== undefined) {
        args.push(playerStack);
      }

      const txHash = await client.writeContract({
        address: this.contractAddress as Address,
        functionName: "update_stage",
        args,
        value: BigInt(0),
      });
      console.log("[PokerPlayer] update_stage transaction sent, hash:", txHash);
      
      const receipt = await client.waitForTransactionReceipt({
        hash: txHash,
        status: TransactionStatus.FINALIZED,
        interval: 10000,
        retries: 20,
      });
      
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const receiptAny = receipt as any;
      const statusName = receiptAny.statusName || receiptAny.status_name;
      
      if (
        statusName !== TransactionStatus.ACCEPTED &&
        statusName !== TransactionStatus.FINALIZED
      ) {
        throw new Error(`Transaction failed with status: ${statusName}`);
      }

      const result = receiptAny.result || receiptAny.data;
      if (!result) {
        throw new Error("No result in transaction receipt");
      }

      return {
        game_id: result.game_id || gameId,
        board_cards: result.board_cards || boardCards,
        pot_size: result.pot_size || potSize,
        current_bet: result.current_bet || currentBet,
        game_stage: result.game_stage || "preflop",
        game_active: result.game_active !== false,
        player_stack: result.player_stack || playerStack || 0,
      };
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error("[PokerPlayer] Error updating stage:", errorMessage);
      throw error;
    }
  }

  async getGameState(gameId: string): Promise<GameState> {
    if (!this.contractAddress) {
      throw new Error("Contract address is required. Please deploy the contract first.");
    }

    console.log("[PokerPlayer] Getting game state for:", gameId);
    const client = this.getClient();
    
    try {
      const result = await client.readContract({
        address: this.contractAddress as Address,
        functionName: "get_game_state",
        args: [gameId],
      });

      return {
        game_id: result.game_id || gameId,
        player_address: result.player_address || "",
        player_hand: result.player_hand || "",
        board_cards: result.board_cards || "",
        player_position: result.player_position || 0,
        num_players: result.num_players || 0,
        pot_size: result.pot_size || 0,
        small_blind: result.small_blind || 0,
        big_blind: result.big_blind || 0,
        player_stack: result.player_stack || 0,
        current_bet: result.current_bet || 0,
        game_stage: result.game_stage || "preflop",
        last_action: result.last_action || "",
        game_active: result.game_active !== false,
      };
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error("[PokerPlayer] Error getting game state:", errorMessage);
      throw error;
    }
  }
}

