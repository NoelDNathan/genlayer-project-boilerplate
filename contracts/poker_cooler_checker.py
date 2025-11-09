# v0.1.0
# { "Depends": "py-genlayer:latest" }
# # { "Runner": "py-genlayer:test" }

import json
import typing
from genlayer import *


class PokerCoolerChecker(gl.Contract):
    total_checks: u256
    has_resolved: bool
    player_hand: str
    opponent_hand: str
    board_cards: str
    is_cooler: bool
    player_hand_rank: str
    opponent_hand_rank: str
    explanation: str

    def __init__(self):
        self.total_checks = 0
        self.has_resolved = False
        self.player_hand = ""
        self.opponent_hand = ""
        self.board_cards = ""
        self.is_cooler = False
        self.player_hand_rank = ""
        self.opponent_hand_rank = ""
        self.explanation = ""

    def _check_cooler(
        self,
        player_hand: str,
        opponent_hand: str,
        board_cards: str = "",
    ) -> dict:
        def verify_cooler() -> str:
            task = f"""
Determine if this poker hand situation is a "cooler".

Card notation uses suit symbols: ♠ (spades), ♥ (hearts), ♦ (diamonds), ♣ (clubs)
Examples: ♠A♠A (pocket Aces of spades), ♥K♥K (pocket Kings of hearts), ♠A♠K (Ace-King suited)

Player hand: {player_hand}
Opponent hand: {opponent_hand}
Board cards: {board_cards if board_cards else "None"}

A "cooler" is defined as a situation where:
1. The player has a very strong hand (e.g., ♠A♠A, ♥K♥K, top pair with top kicker, flush, straight)
2. The opponent has an even stronger hand (e.g., ♠A♠A vs ♥K♥K, flush vs higher flush, straight vs higher straight)
3. The player loses despite having a strong hand that would normally win

Respond in JSON:
{{
    "is_cooler": bool, // true if this is a cooler situation
    "player_hand_rank": str, // e.g., "Pocket Aces", "Flush", "Straight", "Top Pair"
    "opponent_hand_rank": str, // e.g., "Pocket Aces", "Flush", "Straight", "Top Pair"
    "explanation": str // brief explanation of why it is or isn't a cooler
}}
It is mandatory that you respond only using the JSON format above,
nothing else. Don't include any other words or characters,
your output must be only JSON without any formatting prefix or suffix.
This result should be perfectly parsable by a JSON parser without errors.
            """
            result = gl.nondet.exec_prompt(task, response_format="json")
            return json.dumps(result, sort_keys=True)

        result_json = json.loads(gl.eq_principle.strict_eq(verify_cooler))
        return result_json

    @gl.public.write
    def resolve(
        self,
        player_hand: str,
        opponent_hand: str,
        board_cards: str = "",
    ) -> typing.Any:
        """
        Resolve if a poker hand situation is a cooler.

        Args:
            player_hand: The player's hand in card notation (e.g., "♠A♠A", "♥K♥Q")
            opponent_hand: The opponent's hand in card notation (e.g., "♠A♠A", "♥K♥Q")
            board_cards: Optional board cards if applicable (e.g., "♠A♥K♦Q♣J♠10")

        Returns:
            dict with is_cooler (bool), player_hand_rank (str), opponent_hand_rank (str), and explanation (str)
        """
        if not player_hand or not opponent_hand:
            raise Exception("Both player_hand and opponent_hand are required")

        result = self._check_cooler(player_hand, opponent_hand, board_cards)
        self.total_checks += 1

        self.has_resolved = True
        self.player_hand = player_hand
        self.opponent_hand = opponent_hand
        self.board_cards = board_cards
        self.is_cooler = result.get("is_cooler", False)
        self.player_hand_rank = result.get("player_hand_rank", "")
        self.opponent_hand_rank = result.get("opponent_hand_rank", "")
        self.explanation = result.get("explanation", "")

        return {
            "is_cooler": self.is_cooler,
            "player_hand_rank": self.player_hand_rank,
            "opponent_hand_rank": self.opponent_hand_rank,
            "explanation": self.explanation,
        }

    @gl.public.view
    def get_resolution_data(self) -> dict[str, typing.Any]:
        """Get the resolution data from the last resolve call."""
        return {
            "has_resolved": self.has_resolved,
            "player_hand": self.player_hand,
            "opponent_hand": self.opponent_hand,
            "board_cards": self.board_cards,
            "is_cooler": self.is_cooler,
            "player_hand_rank": self.player_hand_rank,
            "opponent_hand_rank": self.opponent_hand_rank,
            "explanation": self.explanation,
            "total_checks": self.total_checks,
        }
