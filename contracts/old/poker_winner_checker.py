# v0.1.0
# { "Depends": "py-genlayer:latest" }

import json
import typing
from genlayer import *


class PokerWinnerChecker(gl.Contract):
    has_resolved: bool
    player_hand: str
    opponent_hand: str
    board_cards: str
    winner: u256
    player_hand_rank: str
    opponent_hand_rank: str

    def __init__(self, player_hand: str, opponent_hand: str, board_cards: str):
        """
        Initializes a new instance of the prediction market with the specified game date and teams.

        Args:
            player_hand (str): The player's hand in card notation (e.g., "♠A♠A", "♥K♥Q").
            opponent_hand (str): The opponent's hand in card notation (e.g., "♠A♠A", "♥K♥Q").
            board_cards (str): The board cards in card notation (e.g., "♠A♥K♦Q♣J♠10").

        Attributes:
            has_resolved (bool): Indicates whether the game's resolution has been processed. Default is False.
            player_hand (str): The player's hand in card notation (e.g., "♠A♠A", "♥K♥Q").
            opponent_hand (str): The opponent's hand in card notation (e.g., "♠A♠A", "♥K♥Q").
            board_cards (str): The board cards in card notation (e.g., "♠A♥K♦Q♣J♠10").
            player_hand_rank (str): The rank of the player's hand.
            opponent_hand_rank (str): The rank of the opponent's hand.
        """
        self.has_resolved = False
        self.player_hand = player_hand
        self.opponent_hand = opponent_hand
        self.board_cards = board_cards
        self.winner = u256(0)
        self.player_hand_rank = ""
        self.opponent_hand_rank = ""

    @gl.public.write
    def calculate_winner(
        self,
        player_hand: str,
        opponent_hand: str,
        board_cards: str = "",
    ) -> typing.Any:

        def determine_winner() -> str:
            task = f"""
Determine who wins in this poker hand  texas hold'em situation.

Card notation uses suit symbols: ♠ (spades), ♥ (hearts), ♦ (diamonds), ♣ (clubs)
Examples: ♠A♠A (pocket Aces of spades), ♥K♥K (pocket Kings of hearts), ♠A♠K (Ace-King suited)

Player hand: {player_hand}
Opponent hand: {opponent_hand}
Board cards: {board_cards if board_cards else "None"}

Respond in JSON:
{{
    "winner": str, // "player", "opponent", or "tie"
    "player_hand_rank": str, // e.g., "Pocket Aces", "Flush", "Straight", "Top Pair"
    "opponent_hand_rank": str, // e.g., "Pocket Aces", "Flush", "Straight", "Top Pair"
}}
It is mandatory that you respond only using the JSON format above,
nothing else. Your output must be only JSON.
            """
            result = gl.nondet.exec_prompt(task, response_format="json")
            return json.dumps(result, sort_keys=True)

        if self.has_resolved:
            return "Already resolved"

        if not player_hand or not opponent_hand:
            raise Exception("Both player_hand and opponent_hand are required")

        result_json = gl.eq_principle.strict_eq(determine_winner)

        self.has_resolved = True
        self.player_hand = player_hand
        self.opponent_hand = opponent_hand
        self.board_cards = board_cards
        self.winner = result_json.get("winner", "")
        self.player_hand_rank = result_json.get("player_hand_rank", "")
        self.opponent_hand_rank = result_json.get("opponent_hand_rank", "")

        return {
            "winner": self.winner,
            "player_hand_rank": self.player_hand_rank,
            "opponent_hand_rank": self.opponent_hand_rank,
        }

    @gl.public.view
    def get_winner(self) -> dict[str, typing.Any]:
        """Get the resolution data from the last resolve call."""
        return {
            "has_resolved": self.has_resolved,
            "player_hand": self.player_hand,
            "opponent_hand": self.opponent_hand,
            "board_cards": self.board_cards,
            "winner": self.winner,
            "player_hand_rank": self.player_hand_rank,
            "opponent_hand_rank": self.opponent_hand_rank,
        }
