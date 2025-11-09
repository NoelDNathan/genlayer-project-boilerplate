# v0.1.0
# { "Depends": "py-genlayer:latest" }

import json
import typing
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class PlayerElimination:
    player_index: u256
    player_address: Address
    player_hand: str
    opponent_hand: str
    board_cards: str
    is_cooler: bool
    hand_rank_player: str
    hand_rank_opponent: str


class PokerTournament(gl.Contract):
    player_balances: DynArray[
        u256
    ]  # Array of player balances (indexed by player position)
    player_addresses: DynArray[
        Address
    ]  # Array of player addresses (indexed by player position)
    player_hands: DynArray[str]  # Array of all player hands
    player_eliminations: DynArray[PlayerElimination]  # Array of player eliminations
    board_cards: str
    pot: u256  # Total pot amount
    hand_winner_index: u256  # Index of the winner of the last hand/round
    tie_players: DynArray[u256]  # Array of player indices in case of tie
    last_pot_distribution: DynArray[u256]  # Last pot distribution per player
    tournament_finished: bool  # Whether the tournament has ended
    tournament_winner_index: u256  # Index of the tournament winner
    set_players_done: bool  # Whether players have been set (can only be set once)
    has_cooler: bool  # Whether the last hand had a cooler situation
    cooler_player_indices: DynArray[
        u256
    ]  # Array of player indices who were eliminated in coolers
    winner_hand_rank: (
        str  # Hand rank of the winner (e.g., "Pocket Aces", "Flush", "Straight")
    )

    def __init__(self):
        # DynArray are automatically initialized by GenLayer
        self.board_cards = ""
        self.hand_winner_index = u256(0)
        self.pot = u256(0)
        self.tournament_finished = False
        self.tournament_winner_index = u256(0)
        self.set_players = False
        self.has_cooler = False
        self.winner_hand_rank = ""
        # cooler_player_indices is automatically initialized as DynArray

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
            "player_addresses": list(self.player_addresses),
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

    @gl.public.view
    def get_cooler_info(self) -> typing.Any:
        """
        Get information about whether there were coolers in the last hand.

        Returns:
            Dictionary with cooler information:
            - has_cooler: bool indicating if there was at least one cooler
            - cooler_player_indices: list of player indices who were eliminated in coolers (can be multiple)
        """
        cooler_indices_list = []
        for i in range(len(self.cooler_player_indices)):
            cooler_indices_list.append(int(self.cooler_player_indices[i]))

        return {
            "has_cooler": self.has_cooler,
            "cooler_player_indices": cooler_indices_list,
        }

    @gl.public.view
    def get_winner_info(self) -> typing.Any:
        """
        Get information about the winner of the last hand.

        Returns:
            Dictionary with winner information:
            - winner_index: int index of the winning player (999999 if tie)
            - winner_hand_rank: str describing the winning hand (e.g., "Pocket Aces", "Flush")
            - is_tie: bool indicating if there was a tie
            - tie_players: list of player indices who tied (empty if no tie)
        """
        tie_players_list = []
        for i in range(len(self.tie_players)):
            tie_players_list.append(int(self.tie_players[i]))

        return {
            "winner_index": int(self.hand_winner_index),
            "winner_hand_rank": self.winner_hand_rank,
            "is_tie": int(self.hand_winner_index) == 999999,
            "tie_players": tie_players_list,
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
    def set_players(
        self, balances: DynArray[int], addresses: DynArray[str]
    ) -> typing.Any:
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

        while len(self.player_addresses) > 0:
            self.player_addresses.pop()

        for address in addresses:
            self.player_addresses.append(Address(address))

        # Check if tournament has finished after balance update
        self._check_tournament_finished()
        self.set_players_done = True

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
        # Validate board_cards FIRST - before any other operations
        # This ensures we fail fast if board_cards is invalid
        if board_cards is None:
            board_cards = ""

        card_count = self._count_cards(board_cards)
        if card_count != 0 and card_count != 5:
            raise Exception(
                f"Board cards must have exactly 5 cards or be empty (pre-flop). Found {card_count} cards."
            )

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

        # Ensure player_balances array is large enough
        while len(self.player_balances) < len(players):
            self.player_balances.append(u256(0))

        # Save previous balances BEFORE deducting bets (to detect eliminations)
        previous_balances = []
        for i in range(len(players)):
            previous_balances.append(int(self.player_balances[i]))

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

HAND RANK FORMAT (CRITICAL - USE EXACTLY THESE FORMATS):
- Pocket pairs: "Pocket Aces", "Pocket Kings", "Pocket Queens", "Pocket Jacks", "Pocket Tens", "Pocket Nines", etc.
- Pairs on board: "Pair of Aces", "Pair of Kings", etc.
- Two Pair: "Two Pair, Aces and Kings", "Two Pair, Queens and Jacks", etc.
- Three of a Kind: "Three Aces", "Three Kings", etc.
- Straight: "Straight, Ace-high", "Straight, King-high", etc.
- Flush: "Flush, Ace-high", "Flush, King-high", etc.
- Full House: "Full House, Aces over Kings", "Full House, Queens over Jacks", etc.
- Four of a Kind: "Four Aces", "Four Kings", etc.
- Straight Flush: "Straight Flush, Ace-high", "Straight Flush, King-high", etc.
- Royal Flush: "Royal Flush"
- High Card: "High Card, Ace", "High Card, King", etc.

COOLER DEFINITION:
A "cooler" is a situation where:
1. A losing player had a very strong hand (e.g., pocket Aces, pocket Kings, top pair with top kicker, flush, straight)
2. The winning player had an even stronger hand
3. The losing player lost despite having a strong hand that would normally win
Examples of coolers:
- Pocket Kings vs Pocket Aces (KK loses to AA)
- Top pair top kicker vs Two pair or better
- Flush vs Higher flush
- Straight vs Higher straight
- Full house vs Higher full house
NOT a cooler if:
- The losing player had a weak hand (e.g., high card, low pair)
- The winning player had a weak hand
- Both players had weak hands

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
Also determine if there was a cooler situation and identify the hand ranks.

Respond in JSON with EXACTLY this structure (no extra fields, no missing fields):
{{
    "winner_index": int, // Index of winning player (0-based), or -1 if there is a tie
    "tie_players": [int], // Array of all player indices who tied for the win (empty array [] if no tie, all tied player indices if winner_index is -1)
    "winner_hand_rank": str, // Hand rank of the winner using EXACT format from HAND RANK FORMAT section above
    "has_cooler": bool, // true if there was at least one cooler situation in this hand, false otherwise
    "cooler_player_indices": [int], // Array of player indices who were eliminated in coolers (empty array [] if no coolers, can be multiple players)
    "hand_ranks": [str] // Array of hand ranks for each player in order (one entry per player, use EXACT format from HAND RANK FORMAT section above)
}}

CRITICAL REQUIREMENTS:
- If there is a single winner, set winner_index to that player's index (0-based) and tie_players to []
- If there is a tie, set winner_index to -1 and tie_players to an array containing ALL tied player indices
- winner_hand_rank MUST use one of the exact formats from HAND RANK FORMAT section above
- has_cooler MUST be true or false (boolean, not string)
- cooler_player_indices MUST be an array (empty [] if no coolers)
- hand_ranks MUST have exactly one entry per player, in player order (Player 0, Player 1, Player 2, etc.)
- Each hand_rank entry MUST use one of the exact formats from HAND RANK FORMAT section above
- Your response must be ONLY valid JSON, no markdown, no code blocks, no explanations, nothing else
- Do not include any text before or after the JSON
- Ensure all arrays are properly formatted (use [] for empty arrays, not null or undefined)
            """
            result = gl.nondet.exec_prompt(task, response_format="json")
            return json.dumps(result, sort_keys=True)

        result_json_str = gl.eq_principle.strict_eq(
            lambda: determine_winner(hands_list, board_cards_str)
        )

        # Parse the JSON string returned by strict_eq
        result_json = json.loads(result_json_str)

        # Validate required fields exist and normalize types
        if "winner_index" not in result_json:
            raise Exception("Missing winner_index in LLM response")
        if "tie_players" not in result_json:
            result_json["tie_players"] = []
        if "winner_hand_rank" not in result_json:
            result_json["winner_hand_rank"] = ""
        if "has_cooler" not in result_json:
            result_json["has_cooler"] = False
        if "cooler_player_indices" not in result_json:
            result_json["cooler_player_indices"] = []
        if "hand_ranks" not in result_json:
            result_json["hand_ranks"] = []

        # Normalize types to ensure consistency
        winner_index = int(result_json.get("winner_index", -1))
        tie_players = result_json.get("tie_players", [])
        if not isinstance(tie_players, list):
            tie_players = []
        winner_hand_rank = str(result_json.get("winner_hand_rank", ""))
        has_cooler = bool(result_json.get("has_cooler", False))
        cooler_player_indices = result_json.get("cooler_player_indices", [])
        if not isinstance(cooler_player_indices, list):
            cooler_player_indices = []
        hand_ranks = result_json.get("hand_ranks", [])
        if not isinstance(hand_ranks, list):
            hand_ranks = []

        if winner_index >= 0:
            self.hand_winner_index = u256(winner_index)
        else:
            self.hand_winner_index = u256(999999)

        # Store winner hand rank and cooler information
        self.winner_hand_rank = winner_hand_rank if winner_hand_rank else ""
        self.has_cooler = has_cooler

        # Reset and store cooler player indices
        while len(self.cooler_player_indices) > 0:
            self.cooler_player_indices.pop()
        for idx in cooler_player_indices:
            if idx >= 0:
                self.cooler_player_indices.append(u256(idx))

        # Reset tie_players storage array
        while len(self.tie_players) > 0:
            self.tie_players.pop()
        for idx in tie_players:
            self.tie_players.append(u256(idx))

        # Replace stored player_hands with provided players
        # Clear existing player_hands first
        while len(self.player_hands) > 0:
            self.player_hands.pop()
        # Add new player hands - iterate by index to handle DynArray correctly
        for i in range(len(players)):
            self.player_hands.append(players[i])

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

        # Track player eliminations (balance went from > 0 to == 0)
        for i in range(len(players)):
            previous_balance = previous_balances[i]
            current_balance = int(self.player_balances[i])

            # Player was eliminated if they had balance before and now have 0
            if previous_balance > 0 and current_balance == 0:
                # Player was eliminated in this hand
                # Get player address
                player_address = (
                    self.player_addresses[i]
                    if i < len(self.player_addresses)
                    else Address("0x0000000000000000000000000000000000000000")
                )

                # Determine opponent hand(s) - the winner(s)
                if winner_index >= 0:
                    opponent_hand = players[winner_index]
                elif len(tie_players) > 0:
                    opponent_hand = players[tie_players[0]]
                else:
                    opponent_hand = ""

                # Check if this player is in the list of cooler players
                is_cooler = False
                if has_cooler and cooler_player_indices and i in cooler_player_indices:
                    is_cooler = True

                # Get hand ranks from the determine_winner result
                if hand_ranks and i < len(hand_ranks):
                    hand_rank_player = hand_ranks[i]
                else:
                    hand_rank_player = "Unknown"

                # Get opponent hand rank
                if winner_index >= 0 and hand_ranks and winner_index < len(hand_ranks):
                    hand_rank_opponent = hand_ranks[winner_index]
                elif winner_hand_rank:
                    hand_rank_opponent = winner_hand_rank
                else:
                    hand_rank_opponent = "Unknown"

                # Create elimination record with cooler information
                elimination = PlayerElimination(
                    player_index=u256(i),
                    player_address=player_address,
                    player_hand=players[i],
                    opponent_hand=opponent_hand,
                    board_cards=board_cards,
                    is_cooler=is_cooler,
                    hand_rank_player=hand_rank_player,
                    hand_rank_opponent=hand_rank_opponent,
                )
                self.player_eliminations.append(elimination)

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
