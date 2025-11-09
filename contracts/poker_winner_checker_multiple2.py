# v0.1.0
# { "Depends": "py-genlayer:latest" }

import json
import typing
from genlayer import *



class PokerWinnerCheckerMultiple(gl.Contract):
    has_resolved: bool
    player_hands: DynArray[str]  # Array of all player hands
    board_cards: str
    winner_index: u256  # Index of the winner in the array
    hand_ranks: DynArray[str]  # Array of hand ranks for each player
    tie_players: DynArray[u256]  # Array of player indices in case of tie

    def __init__(self, board_cards: str = ""):
        """
        Initializes a new instance of the poker winner checker for multiple players.

        Args:
            board_cards (str): The board cards in card notation (e.g., "♠A♥K♦Q♣J♠10"). Default is empty string.

        Attributes:
            has_resolved (bool): Indicates whether the game's resolution has been processed. Default is False.
            player_hands (DynArray[str]): Array of player hands in card notation.
            board_cards (str): The board cards in card notation.
            winner_index (u256): Index of the winning player (0-based), or 999999 if tie.
            hand_ranks (DynArray[str]): Array of hand ranks for each player.
            tie_players (DynArray[u256]): Array of player indices in case of tie.
        """
        self.has_resolved = False
        # DynArray se inicializan automáticamente por GenLayer, no los inicialices manualmente
        self.board_cards = board_cards
        self.winner_index = u256(0)

    @gl.public.write
    def add_player(self, hand: str):
        """
        Add a new player to the game.

        Args:
            hand (str): The player's hand in card notation (e.g., "♠A♠A", "♥K♥Q").
        """
        if self.has_resolved:
            raise Exception("Cannot add players after game is resolved")

        self.player_hands.append(hand)

    @gl.public.write
    def set_board_cards(self, board_cards: str):
        """
        Set or update the board cards.

        Args:
            board_cards (str): The board cards in card notation (e.g., "♠A♥K♦Q♣J♠10").
        """
        if self.has_resolved:
            raise Exception("Cannot change board cards after game is resolved")
        self.board_cards = board_cards

    @gl.public.write
    def calculate_winner(self) -> typing.Any:
        """
        Calculate the winner among all players.

        Returns:
            dict: Contains winner information, hand ranks, and tie information.
        """

        def determine_winner() -> str:
            hands_list = []
            for i in range(len(self.player_hands)):
                hands_list.append(f"Player {i}: {self.player_hands[i]}")

            task = f"""
Determine who wins in this poker hand texas hold'em situation with multiple players.

Card notation uses suit symbols: ♠ (spades), ♥ (hearts), ♦ (diamonds), ♣ (clubs)
Examples: ♠A♠A (pocket Aces of spades), ♥K♥K (pocket Kings of hearts), ♠A♠K (Ace-King suited)

Player hands:
{chr(10).join(hands_list)}
Board cards: {self.board_cards if self.board_cards else "None"}

Respond in JSON:
{{
    "winner_index": int, // Index of winning player (0-based), or -1 if tie
    "hand_ranks": [str], // Array of hand ranks for each player in order
    "tie_players": [int] // Array of player indices if there's a tie (empty if no tie)
}}
It is mandatory that you respond only using the JSON format above,
nothing else. Your output must be only JSON.
            """
            result = gl.nondet.exec_prompt(task, response_format="json")
            return json.dumps(result, sort_keys=True)

        if self.has_resolved:
            return "Already resolved"

        if len(self.player_hands) < 2:
            raise Exception("At least 2 players are required")

        result_json = gl.eq_principle.strict_eq(determine_winner)

        self.has_resolved = True

        winner_index = result_json.get("winner_index", -1)
        hand_ranks = result_json.get("hand_ranks", [])
        tie_players = result_json.get("tie_players", [])

        # Store winner index (use -1 to represent tie, but store as u256)
        if winner_index >= 0:
            self.winner_index = u256(winner_index)
        else:
            # For tie, we'll use a special value or handle differently
            # Since u256 can't be negative, we'll use a large number to represent tie
            self.winner_index = u256(999999)  # Special value for tie

        # Clear and populate hand_ranks array
        # Since calculate_winner can only be called once, we can safely clear and repopulate
        while len(self.hand_ranks) > 0:
            self.hand_ranks.pop()
        for rank in hand_ranks:
            self.hand_ranks.append(rank)

        # Clear and populate tie_players array
        while len(self.tie_players) > 0:
            self.tie_players.pop()
        for idx in tie_players:
            self.tie_players.append(u256(idx))

        return {
            "winner_index": winner_index,
            "hand_ranks": hand_ranks,
            "tie_players": tie_players,
            "is_tie": winner_index < 0,
        }

    @gl.public.view
    def get_winner(self) -> dict[str, typing.Any]:
        """
        Get the resolution data from the last resolve call.

        Returns:
            dict: Contains all players information, board cards, and winner status.
        """
        players_data = []
        for i in range(len(self.player_hands)):
            hand_rank = ""
            if i < len(self.hand_ranks):
                hand_rank = self.hand_ranks[i]

            is_winner = False
            if self.winner_index < u256(999999):  # Not a tie
                is_winner = u256(i) == self.winner_index
            else:
                # Check if this player is in the tie_players array
                for tie_idx in self.tie_players:
                    if u256(i) == tie_idx:
                        is_winner = True
                        break

            players_data.append(
                {
                    "index": i,
                    "hand": self.player_hands[i],
                    "hand_rank": hand_rank,
                    "is_winner": is_winner,
                }
            )

        winners = [p for p in players_data if p["is_winner"]]

        # Convert tie_players to list of ints for return
        tie_players_list = []
        for tie_idx in self.tie_players:
            tie_players_list.append(int(tie_idx))

        return {
            "has_resolved": self.has_resolved,
            "board_cards": self.board_cards,
            "players": players_data,
            "winners": winners,
            "total_players": len(self.player_hands),
            "winner_index": self.winner_index,
            "is_tie": self.winner_index >= u256(999999),
            "tie_players": tie_players_list,
        }

    @gl.public.view
    def get_players(self) -> dict[str, typing.Any]:
        """
        Get all players information without resolution data.

        Returns:
            dict: Contains all players and board cards.
        """
        players_data = []
        for i in range(len(self.player_hands)):
            hand_rank = ""
            if i < len(self.hand_ranks):
                hand_rank = self.hand_ranks[i]

            players_data.append(
                {"index": i, "hand": self.player_hands[i], "hand_rank": hand_rank}
            )

        return {
            "players": players_data,
            "board_cards": self.board_cards,
            "total_players": len(self.player_hands),
            "has_resolved": self.has_resolved,
        }

    @gl.public.view
    def get_hand_at(self, index: int) -> str:
        """
        Get the hand of a player at a specific index.

        Args:
            index (int): The index of the player (0-based).

        Returns:
            str: The player's hand, or empty string if index is invalid.
        """
        if index >= 0 and index < len(self.player_hands):
            return self.player_hands[index]
        return ""

    @gl.public.view
    def get_array_length(self) -> int:
        """
        Get the number of players in the game.

        Returns:
            int: The number of players.
        """
        return u256(len(self.player_hands))

    @gl.public.write
    def remove_last(self):
        """
        Remove the last player from the game (only if not resolved).
        """
        if self.has_resolved:
            raise Exception("Cannot remove players after game is resolved")

        if len(self.player_hands) > 0:
            self.player_hands.pop()
