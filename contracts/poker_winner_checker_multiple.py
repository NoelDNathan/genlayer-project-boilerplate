# v0.1.0
# { "Depends": "py-genlayer:latest" }

import json
import typing
from genlayer import *


class PokerWinnerCheckerMultiple(gl.Contract):
    player_hands: DynArray[str]  # Array of all player hands
    board_cards: str
    winner_index: u256  # Index of the winner in the array
    tie_players: DynArray[u256]  # Array of player indices in case of tie

    def __init__(self):
        # DynArray se inicializan automáticamente por GenLayer
        self.board_cards = ""
        self.winner_index = u256(0)

    @gl.public.view
    def get_state(self) -> typing.Any:
        """
        Returns the current state of the contract.
        """
        tie_players_list = []
        for i in range(len(self.tie_players)):
            tie_players_list.append(int(self.tie_players[i]))

        return {
            "player_hands": list(self.player_hands),
            "board_cards": self.board_cards,
            "winner_index": int(self.winner_index),
            "tie_players": tie_players_list,
            "is_tie": int(self.winner_index) == 999999,
        }

    def _count_cards(self, cards_str: str) -> int:
        """
        Count the number of cards in a string representation.
        Each card is represented by a suit symbol (♠, ♥, ♦, ♣) followed by a rank.
        """
        if not cards_str:
            return 0

        suit_symbols = ["♠", "♥", "♦", "♣"]
        count = 0
        for symbol in suit_symbols:
            count += cards_str.count(symbol)
        return count

    @gl.public.write
    def calculate_winner_and_store(
        self, players: DynArray[str], board_cards: str
    ) -> typing.Any:
        """
        Calculate winner from the provided players and board, and store the result into contract state.
        This replaces the stored player_hands with 'players', sets winner/tie state.
        """
        if len(players) < 2:
            raise Exception("At least 2 players are required")

        # Validate board_cards: must be empty (pre-flop) or have exactly 5 cards
        card_count = self._count_cards(board_cards)
        if card_count != 0 and card_count != 5:
            raise Exception(
                f"Board cards must have exactly 5 cards or be empty (pre-flop). Found {card_count} cards."
            )

        # Build input and call the same internal prompt
        hands_list = []
        for i in range(len(players)):
            hands_list.append(f"Player {i}: {players[i]}")
        board_cards_str = board_cards if board_cards else "None"

        def determine_winner(hands_list: list[str], board_cards_str: str) -> str:
            task = f"""
You are an expert poker judge determining the winner in a Texas Hold'em poker hand with multiple players.

TEXAS HOLD'EM RULES:
- Each player has 2 private cards (their "hand")
- There are 5 community cards on the board (shared by all players)
- Each player makes their best 5-card poker hand using any combination of their 2 private cards and the 5 community cards
- You can use 0, 1, or 2 of your private cards, and 5, 4, or 3 of the community cards respectively
- The player with the highest-ranking 5-card hand wins

HAND RANKINGS (from highest to lowest):
1. Royal Flush: A-K-Q-J-10 all of the same suit
2. Straight Flush: Five consecutive cards of the same suit (e.g., 9-8-7-6-5 of hearts)
3. Four of a Kind: Four cards of the same rank (e.g., four Kings)
4. Full House: Three of a kind + a pair (e.g., three 7s and two Aces)
5. Flush: Five cards of the same suit, not in sequence
6. Straight: Five consecutive cards of different suits (e.g., 10-9-8-7-6)
7. Three of a Kind: Three cards of the same rank (e.g., three Queens)
8. Two Pair: Two different pairs (e.g., two Kings and two 5s)
9. One Pair: Two cards of the same rank (e.g., two Jacks)
10. High Card: No pair, highest card wins

COMPARING HANDS:
- If two players have the same hand type, compare the rank values:
  - Card ranks: 2 < 3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A
- For pairs/trips/quads: compare the rank of the pair/trip/quad first
- For full house: compare the three-of-a-kind rank first, then the pair rank
- For two pair: compare the higher pair first, then the lower pair, then the kicker
- For one pair: compare the pair rank first, then kickers in descending order
- For high card: compare cards in descending order
- If all 5 cards are identical in rank (but different suits), it's a tie

TIE RULES:
- If multiple players have identical 5-card hands (same ranks, regardless of suits), they tie
- Example: Player 1 has K♠K♥ and Player 2 has K♦K♣ with board K♠Q♠J♠10♠9♠ - both have King-high flush, it's a tie

CARD NOTATION:
- Suit symbols: ♠ (spades), ♥ (hearts), ♦ (diamonds), ♣ (clubs)
- Ranks: A (Ace), K (King), Q (Queen), J (Jack), 10, 9, 8, 7, 6, 5, 4, 3, 2
- Example: "♠A♥K" means Ace of spades and King of hearts

CURRENT GAME:
Player hands:
{chr(10).join(hands_list)}
Board cards: {board_cards_str}

Analyze each player's best possible 5-card hand by combining their 2 private cards with the 5 community cards.
Determine which player(s) have the highest-ranking hand.

Respond in JSON:
{{
    "winner_index": int, // Index of winning player (0-based), or -1 if there is a tie
    "tie_players": [int] // Array of all player indices who tied for the win (empty array if no tie, all tied players if winner_index is -1)
}}

IMPORTANT: 
- If there is a single winner, set winner_index to that player's index and tie_players to []
- If there is a tie, set winner_index to -1 and tie_players to an array containing all tied player indices
- Your response must be ONLY valid JSON, nothing else.
            """
            result = gl.nondet.exec_prompt(task, response_format="json")
            return json.dumps(result, sort_keys=True)

        result_json_str = gl.eq_principle.strict_eq(
            lambda: determine_winner(hands_list, board_cards_str)
        )

        # Parse the JSON string returned by strict_eq
        result_json = json.loads(result_json_str)

        # Persist state
        winner_index = result_json.get("winner_index", -1)
        tie_players = result_json.get("tie_players", [])

        if winner_index >= 0:
            self.winner_index = u256(winner_index)
        else:
            self.winner_index = u256(999999)

        # reset tie_players storage array
        while len(self.tie_players) > 0:
            self.tie_players.pop()
        for idx in tie_players:
            self.tie_players.append(u256(idx))

        # replace stored player_hands with provided players
        # Clear existing player_hands first
        while len(self.player_hands) > 0:
            self.player_hands.pop()
        # Add new player hands
        for hand in players:
            self.player_hands.append(hand)

        self.board_cards = board_cards

        return {
            "winner_index": winner_index,
            "tie_players": tie_players,
            "is_tie": winner_index < 0,
        }
