# v0.1.0
# { "Depends": "py-genlayer:latest" }

import json
import typing
from genlayer import *


class PokerTournament(gl.Contract):
    player_balances: DynArray[
        u256
    ]  # Array of player balances (indexed by player position)
    player_hands: DynArray[str]  # Array of all player hands
    board_cards: str
    pot: u256  # Total pot amount
    hand_winner_index: u256  # Index of the winner of the last hand/round
    tie_players: DynArray[u256]  # Array of player indices in case of tie
    last_pot_distribution: DynArray[u256]  # Last pot distribution per player
    tournament_finished: bool  # Whether the tournament has ended
    tournament_winner_index: u256  # Index of the tournament winner

    def __init__(self):
        # DynArray are automatically initialized by GenLayer
        self.board_cards = ""
        self.hand_winner_index = u256(0)
        self.pot = u256(0)
        self.tournament_finished = False
        self.tournament_winner_index = u256(0)

    @gl.public.view
    def get_state(self) -> typing.Any:
        """
        Returns the current state of the tournament contract.
        """
        tie_players_list = []
        for i in range(len(self.tie_players)):
            tie_players_list.append(int(self.tie_players[i]))

        balances_list = []
        for i in range(len(self.player_balances)):
            balances_list.append(int(self.player_balances[i]))

        last_distribution_list = []
        for i in range(len(self.last_pot_distribution)):
            last_distribution_list.append(int(self.last_pot_distribution[i]))

        return {
            "player_balances": balances_list,
            "player_hands": list(self.player_hands),
            "board_cards": self.board_cards,
            "pot": int(self.pot),
            "hand_winner_index": int(self.hand_winner_index),
            "tie_players": tie_players_list,
            "is_tie": int(self.hand_winner_index) == 999999,
            "last_pot_distribution": last_distribution_list,
            "tournament_finished": self.tournament_finished,
            "tournament_winner_index": int(self.tournament_winner_index),
        }

    @gl.public.view
    def get_last_winner(self) -> typing.Any:
        """
        Returns the last winner information, similar to get_state in poker_winner_checker_multiple.
        """
        tie_players_list = []
        for i in range(len(self.tie_players)):
            tie_players_list.append(int(self.tie_players[i]))

        return {
            "player_hands": list(self.player_hands),
            "board_cards": self.board_cards,
            "hand_winner_index": int(self.hand_winner_index),
            "tie_players": tie_players_list,
            "is_tie": int(self.hand_winner_index) == 999999,
            "tournament_finished": self.tournament_finished,
            "tournament_winner_index": int(self.tournament_winner_index),
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

    def _check_tournament_finished(self) -> None:
        """
        Check if the tournament has finished (only one player has balance > 0).
        Tournament is only finished if there are at least 2 players registered and only one has balance.
        If so, set tournament_finished to True and tournament_winner_index to that player's index.
        If there are multiple players with balance, reset tournament_finished to False.
        """
        players_with_balance = []
        for i in range(len(self.player_balances)):
            if int(self.player_balances[i]) > 0:
                players_with_balance.append(i)

        total_players = len(self.player_balances)

        if len(players_with_balance) == 1 and total_players >= 2:
            # Tournament finished: at least 2 players were registered, only one has balance
            self.tournament_finished = True
            self.tournament_winner_index = u256(players_with_balance[0])
        elif len(players_with_balance) == 0:
            # Edge case: all players have 0 balance (shouldn't happen, but handle it)
            self.tournament_finished = True
            self.tournament_winner_index = u256(999999)  # No winner
        else:
            # Multiple players with balance, or only one player registered (tournament not started)
            self.tournament_finished = False

    @gl.public.write
    def set_player_balances(self, balances: DynArray[int]) -> typing.Any:
        """
        Set the balances for all players.

        Args:
            balances: Array of balances for each player (must be >= 0 for each)
        """
        # Validate all balances are non-negative
        for i, balance in enumerate(balances):
            if balance < 0:
                raise Exception(f"Balance for player {i} cannot be negative")

        # Clear existing balances
        while len(self.player_balances) > 0:
            self.player_balances.pop()

        # Set new balances
        for balance in balances:
            self.player_balances.append(u256(balance))

        # Check if tournament has finished after balance update
        self._check_tournament_finished()

        return {
            "player_balances": [int(b) for b in self.player_balances],
            "tournament_finished": self.tournament_finished,
            "tournament_winner_index": (
                int(self.tournament_winner_index) if self.tournament_finished else -1
            ),
        }

    @gl.public.write
    def calculate_winners(
        self,
        players: DynArray[str],
        board_cards: str,
        player_bets: DynArray[int],
    ) -> typing.Any:
        """
        Calculate winners from the provided players and board, update player balances based on bets and pot distribution.
        This replaces the stored player_hands with 'players', sets winner/tie state, and distributes the pot.
        The pot amount is automatically calculated as the sum of all player_bets.

        Args:
            players: Array of player hands (each player has 2 cards)
            board_cards: The 5 community cards (or empty string for pre-flop)
            player_bets: Array of bets made by each player (must match players length)
        """
        if len(players) < 2:
            raise Exception("At least 2 players are required")

        if len(player_bets) != len(players):
            raise Exception(
                f"player_bets length ({len(player_bets)}) must match players length ({len(players)})"
            )

        # Calculate pot amount as sum of all bets
        pot_amount = 0
        for bet in player_bets:
            if int(bet) < 0:
                raise Exception("Player bet cannot be negative")
            pot_amount += int(bet)

        # Validate board_cards: must be empty (pre-flop) or have exactly 5 cards
        card_count = self._count_cards(board_cards)
        if card_count != 0 and card_count != 5:
            raise Exception(
                f"Board cards must have exactly 5 cards or be empty (pre-flop). Found {card_count} cards."
            )

        # Ensure player_balances array is large enough
        while len(self.player_balances) < len(players):
            self.player_balances.append(u256(0))

        # Validate that each player has sufficient balance for their bet
        for i in range(len(players)):
            current_balance = int(self.player_balances[i])
            bet_amount = int(player_bets[i])
            if current_balance < bet_amount:
                raise Exception(
                    f"Player {i} has insufficient balance ({current_balance}) for bet ({bet_amount})"
                )

        # Deduct bets from player balances
        for i in range(len(players)):
            current_balance = int(self.player_balances[i])
            bet_amount = int(player_bets[i])
            self.player_balances[i] = u256(current_balance - bet_amount)

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
            self.hand_winner_index = u256(winner_index)
        else:
            self.hand_winner_index = u256(999999)

        # Reset tie_players storage array
        while len(self.tie_players) > 0:
            self.tie_players.pop()
        for idx in tie_players:
            self.tie_players.append(u256(idx))

        # Replace stored player_hands with provided players
        # Clear existing player_hands first
        while len(self.player_hands) > 0:
            self.player_hands.pop()
        # Add new player hands
        for hand in players:
            self.player_hands.append(hand)

        self.board_cards = board_cards
        self.pot = u256(pot_amount)

        # Distribute pot and update balances
        # Reset last_pot_distribution
        while len(self.last_pot_distribution) > 0:
            self.last_pot_distribution.pop()

        # Initialize distribution array to match player count
        for i in range(len(players)):
            self.last_pot_distribution.append(u256(0))

        if winner_index >= 0:
            # Single winner gets the entire pot
            current_balance = int(self.player_balances[winner_index])
            self.player_balances[winner_index] = u256(current_balance + pot_amount)
            self.last_pot_distribution[winner_index] = u256(pot_amount)
        elif len(tie_players) > 0:
            # Split pot equally among tied players
            pot_per_player = pot_amount // len(tie_players)
            remainder = pot_amount % len(tie_players)

            # Distribute pot equally
            for i, tied_idx in enumerate(tie_players):
                current_balance = int(self.player_balances[tied_idx])
                # Give remainder to first player(s) if pot doesn't divide evenly
                amount = pot_per_player + (1 if i < remainder else 0)
                self.player_balances[tied_idx] = u256(current_balance + amount)
                self.last_pot_distribution[tied_idx] = u256(amount)

        # Check if tournament has finished after pot distribution
        self._check_tournament_finished()

        return {
            "hand_winner_index": winner_index,
            "tie_players": tie_players,
            "is_tie": winner_index < 0,
            "pot_distributed": pot_amount,
            "player_balances": [int(b) for b in self.player_balances],
            "tournament_finished": self.tournament_finished,
            "tournament_winner_index": (
                int(self.tournament_winner_index) if self.tournament_finished else -1
            ),
        }
