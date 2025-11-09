# v0.1.0
# { "Depends": "py-genlayer:latest" }

import json
import typing
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class Player:
    address: Address
    hand: str
    hand_rank: str
    is_winner: bool


class PokerWinnerChecker(gl.Contract):
    has_resolved: bool
    players: DynArray[Player]
    board_cards: str

    def __init__(self, board_cards: str = ""):
        """
        Initializes a new instance of the poker winner checker.

        Args:
            board_cards (str): The board cards in card notation (e.g., "♠A♥K♦Q♣J♠10"). Default is empty string.

        Attributes:
            has_resolved (bool): Indicates whether the game's resolution has been processed. Default is False.
            players (DynArray[Player]): Array of players with their hands and information.
            board_cards (str): The board cards in card notation.
        """
        self.has_resolved = False
        self.players = DynArray[Player]()
        self.board_cards = board_cards

    @gl.public.write
    def add_player(self, address: str, hand: str):
        """
        Add a new player to the game.

        Args:
            address (str): The player's address.
            hand (str): The player's hand in card notation (e.g., "♠A♠A", "♥K♥Q").
        """
        if self.has_resolved:
            raise Exception("Cannot add players after game is resolved")

        player = Player(
            address=Address(address), hand=hand, hand_rank="", is_winner=False
        )
        self.players.append(player)

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
            for i in range(len(self.players)):
                player = self.players[i]
                hands_list.append(f"Player {i} ({player.address}): {player.hand}")

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

        if len(self.players) < 2:
            raise Exception("At least 2 players are required")

        result_json = gl.eq_principle.strict_eq(determine_winner)

        self.has_resolved = True

        # Update board cards if needed (should already be set)
        winner_index = result_json.get("winner_index", -1)
        hand_ranks = result_json.get("hand_ranks", [])
        tie_players = result_json.get("tie_players", [])

        # Update all players with their hand ranks
        for i in range(len(self.players)):
            if i < len(hand_ranks):
                self.players[i].hand_rank = hand_ranks[i]

            # Mark winners
            if winner_index >= 0:
                self.players[i].is_winner = i == winner_index
            else:
                # Tie situation
                self.players[i].is_winner = i in tie_players

        # Build result with player information
        winners = []
        if winner_index >= 0:
            winners.append(
                {
                    "index": winner_index,
                    "address": str(self.players[winner_index].address),
                    "hand": self.players[winner_index].hand,
                    "hand_rank": self.players[winner_index].hand_rank,
                }
            )
        else:
            for idx in tie_players:
                winners.append(
                    {
                        "index": idx,
                        "address": str(self.players[idx].address),
                        "hand": self.players[idx].hand,
                        "hand_rank": self.players[idx].hand_rank,
                    }
                )

        return {
            "winner_index": winner_index,
            "winners": winners,
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
        for i in range(len(self.players)):
            player = self.players[i]
            players_data.append(
                {
                    "index": i,
                    "address": str(player.address),
                    "hand": player.hand,
                    "hand_rank": player.hand_rank,
                    "is_winner": player.is_winner,
                }
            )

        winners = [p for p in players_data if p["is_winner"]]

        return {
            "has_resolved": self.has_resolved,
            "board_cards": self.board_cards,
            "players": players_data,
            "winners": winners,
            "total_players": len(self.players),
        }

    @gl.public.view
    def get_players(self) -> dict[str, typing.Any]:
        """
        Get all players information without resolution data.

        Returns:
            dict: Contains all players and board cards.
        """
        players_data = []
        for i in range(len(self.players)):
            player = self.players[i]
            players_data.append(
                {
                    "index": i,
                    "address": str(player.address),
                    "hand": player.hand,
                    "hand_rank": player.hand_rank,
                    "is_winner": player.is_winner,
                }
            )

        return {
            "players": players_data,
            "board_cards": self.board_cards,
            "total_players": len(self.players),
            "has_resolved": self.has_resolved,
        }
