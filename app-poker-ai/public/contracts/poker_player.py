# v0.1.0
# { "Depends": "py-genlayer:latest" }

import json
import typing
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class GameState:
    game_id: str
    player_address: str
    player_hand: str
    board_cards: str
    player_position: u256
    num_players: u256
    pot_size: u256
    small_blind: u256
    big_blind: u256
    player_stack: u256
    current_bet: u256
    game_stage: str  # preflop, flop, turn, river, finished
    last_action: str
    game_active: bool


class PokerPlayer(gl.Contract):
    """
    AI-powered poker advisor contract that provides action recommendations
    at each betting round (preflop, flop, turn, river).
    """

    games: TreeMap[str, GameState]  # Map of game_id -> GameState
    game_counter: u256  # Counter for generating unique game IDs

    def __init__(self):
        self.game_counter = u256(0)

    def _generate_game_id(self) -> str:
        """Generate a unique game ID."""
        counter = int(self.game_counter)
        self.game_counter = u256(counter + 1)
        return f"game_{counter}"

    def _validate_action(
        self, action: str, amount: int, current_bet: int, player_stack: int
    ) -> None:
        """
        Validate that the recommended action is legal.

        Args:
            action: The action to validate (fold, check, call, raise, all-in)
            amount: The amount for raise actions
            current_bet: Current bet to call
            player_stack: Player's current stack
        """
        action_lower = action.lower()

        if action_lower == "fold":
            # Fold is always valid
            return
        elif action_lower == "check":
            # Check is only valid if current_bet == 0
            if current_bet != 0:
                raise Exception(
                    f"Cannot check when current bet is {current_bet}. Must call or fold."
                )
        elif action_lower == "call":
            # Call is valid if player_stack >= current_bet
            if player_stack < current_bet:
                raise Exception(
                    f"Insufficient stack ({player_stack}) to call bet ({current_bet})"
                )
        elif action_lower == "raise":
            # Raise is valid if amount > current_bet and player_stack >= amount
            if amount <= current_bet:
                raise Exception(
                    f"Raise amount ({amount}) must be greater than current bet ({current_bet})"
                )
            if player_stack < amount:
                raise Exception(
                    f"Insufficient stack ({player_stack}) to raise to {amount}"
                )
        elif action_lower == "all-in":
            # All-in is valid if player_stack > 0
            if player_stack <= 0:
                raise Exception("Cannot go all-in with zero stack")
        else:
            raise Exception(
                f"Invalid action: {action}. Must be fold, check, call, raise, or all-in"
            )

    def _get_ai_recommendation(self, game_state: GameState) -> dict:
        """
        Query AI for action recommendation based on current game state.

        Args:
            game_state: Current game state

        Returns:
            Dictionary with action and amount
        """
        # Extract all values from game_state BEFORE entering nondet context
        # This is required because storage cannot be read in nondet mode
        player_hand = game_state.player_hand
        board_cards = game_state.board_cards
        game_stage = game_state.game_stage
        player_position = int(game_state.player_position)
        num_players = int(game_state.num_players)
        pot_size = int(game_state.pot_size)
        small_blind = int(game_state.small_blind)
        big_blind = int(game_state.big_blind)
        player_stack = int(game_state.player_stack)
        current_bet = int(game_state.current_bet)

        # Format board cards display
        board_display = board_cards if board_cards else "None (Pre-flop)"

        # Determine position name
        position_names = [
            "Under the Gun",
            "Under the Gun +1",
            "Middle Position",
            "Middle Position +1",
            "Cutoff",
            "Button",
            "Small Blind",
            "Big Blind",
        ]
        position_name = (
            position_names[player_position]
            if player_position < len(position_names)
            else f"Position {player_position}"
        )

        def leader_fn():
            task = f"""
You are an expert Texas Hold'em poker advisor. Analyze the current game situation and recommend the best action.

GAME INFORMATION:
- Player's Hole Cards: {player_hand}
- Community Cards: {board_display}
- Game Stage: {game_stage.upper()}
- Player Position: {position_name} (Position {player_position})
- Number of Players: {num_players}
- Pot Size: {pot_size}
- Small Blind: {small_blind}
- Big Blind: {big_blind}
- Player Stack: {player_stack}
- Current Bet to Call: {current_bet}

CARD NOTATION:
- Suit symbols: ♠ (spades), ♥ (hearts), ♦ (diamonds), ♣ (clubs)
- Ranks: A (Ace), K (King), Q (Queen), J (Jack), 10, 9, 8, 7, 6, 5, 4, 3, 2
- Example: "♠A♥K" means Ace of spades and King of hearts

AVAILABLE ACTIONS:
- fold: Give up the hand (always valid)
- check: Pass when no bet to call (only valid if current_bet == 0)
- call: Match the current bet (valid if player_stack >= current_bet)
- raise: Increase the bet (valid if amount > current_bet and player_stack >= amount)
- all-in: Bet entire stack (valid if player_stack > 0)

STRATEGY CONSIDERATIONS:
- Consider hand strength, position, pot odds, stack depth, and opponent behavior
- Be aggressive with strong hands, cautious with weak hands
- Consider implied odds and fold equity
- Adjust strategy based on position (tight in early position, loose in late position)

Respond in JSON format:
{{
    "action": "fold|check|call|raise|all-in",
    "amount": 0  // For raise: the total amount to bet (including call). For other actions: 0
}}

IMPORTANT:
- Your response must be ONLY valid JSON, nothing else.
- For raise actions, amount must be greater than current_bet.
- For all-in, set action to "all-in" and amount to 0 (or player_stack if you want to specify).
- Be strategic and consider all factors.
            """
            result = gl.nondet.exec_prompt(task, response_format="json")
            return json.dumps(result, sort_keys=True)

        def validator_fn(leader_result: gl.vm.Result) -> bool:
            """
            Validator function that allows reasonable variations in raise amounts.
            Actions must match exactly, but raise amounts can vary within tolerance.
            """
            # Check if leader result is an error
            if not isinstance(leader_result, gl.vm.Return):
                return False

            try:
                # Parse leader's result
                leader_json = json.loads(leader_result.calldata)
                leader_action = leader_json.get("action", "").lower()
                leader_amount = leader_json.get("amount", 0)

                # Get validator's own result
                validator_result_str = leader_fn()
                validator_json = json.loads(validator_result_str)
                validator_action = validator_json.get("action", "").lower()
                validator_amount = validator_json.get("amount", 0)

                # Actions must match exactly
                if leader_action != validator_action:
                    return False

                # For categorical actions (fold, check, call, all-in), amounts should match
                if leader_action in ["fold", "check", "call", "all-in"]:
                    return leader_amount == validator_amount

                # For raise actions, allow reasonable tolerance
                # Accept if amounts are within 20% of each other or within 2 big blinds
                if leader_action == "raise":
                    amount_diff = abs(leader_amount - validator_amount)
                    if amount_diff == 0:
                        return True  # Exact match

                    # Calculate percentage difference
                    max_amount = max(leader_amount, validator_amount, 1)
                    percent_diff = (amount_diff / max_amount) * 100
                    tolerance_bb = 2 * big_blind

                    # Accept if within 20% or within 2 big blinds
                    return percent_diff <= 20 or amount_diff <= tolerance_bb

                return False

            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                return False

        # Use run_nondet with custom validator for flexible validation
        result_json_str = gl.vm.run_nondet(leader_fn, validator_fn)
        result_json = json.loads(result_json_str)

        action = result_json.get("action", "").lower()
        amount = result_json.get("amount", 0)

        # Handle all-in: if action is all-in, amount should be player_stack
        if action == "all-in":
            amount = player_stack

        return {"action": action, "amount": amount}

    @gl.public.write
    def create_game(
        self,
        player_address: str,
        player_hand: str,
        position: int,
        num_players: int,
        pot_size: int,
        small_blind: int,
        big_blind: int,
        player_stack: int,
        current_bet: int,
    ) -> typing.Any:
        """
        Initialize a new game with preflop information.

        Args:
            player_address: Address of the player
            player_hand: Player's hole cards (2 cards, e.g., "♠A♥K")
            position: Player's position at the table (0-9)
            num_players: Number of active players
            pot_size: Current pot size
            small_blind: Small blind amount
            big_blind: Big blind amount
            player_stack: Player's current stack
            current_bet: Current bet to call

        Returns:
            Dictionary with game_id and initial state
        """
        # Validate inputs
        if position < 0 or position > 9:
            raise Exception("Position must be between 0 and 9")
        if num_players < 2:
            raise Exception("Number of players must be at least 2")
        if pot_size < 0:
            raise Exception("Pot size cannot be negative")
        if small_blind <= 0 or big_blind <= 0:
            raise Exception("Blinds must be positive")
        if player_stack <= 0:
            raise Exception("Player stack must be positive")
        if current_bet < 0:
            raise Exception("Current bet cannot be negative")

        # Generate game ID
        game_id = self._generate_game_id()

        # Create game state
        game_state = GameState(
            game_id=game_id,
            player_address=player_address,
            player_hand=player_hand,
            board_cards="",
            player_position=u256(position),
            num_players=u256(num_players),
            pot_size=u256(pot_size),
            small_blind=u256(small_blind),
            big_blind=u256(big_blind),
            player_stack=u256(player_stack),
            current_bet=u256(current_bet),
            game_stage="preflop",
            last_action="",
            game_active=True,
        )

        # Store game
        self.games[game_id] = game_state

        return {
            "game_id": game_id,
            "player_address": player_address,
            "game_stage": "preflop",
            "game_active": True,
        }

    @gl.public.write
    def get_action(self, game_id: str) -> typing.Any:
        """
        Query AI for action recommendation at current stage.

        Args:
            game_id: The game ID to get action for

        Returns:
            Dictionary with recommended action and amount
        """
        # Get game state
        if game_id not in self.games:
            raise Exception(f"Game {game_id} not found")

        game_state = self.games[game_id]

        if not game_state.game_active:
            raise Exception(f"Game {game_id} is not active")

        if game_state.game_stage == "finished":
            raise Exception(f"Game {game_id} is finished")

        # Get AI recommendation
        recommendation = self._get_ai_recommendation(game_state)

        action = recommendation["action"]
        amount = recommendation["amount"]

        # Validate action
        self._validate_action(
            action, amount, int(game_state.current_bet), int(game_state.player_stack)
        )

        # Calculate amount to deduct from stack
        amount_to_deduct = 0
        action_lower = action.lower()

        if action_lower == "call":
            # For call, deduct the current bet amount
            amount_to_deduct = int(game_state.current_bet)
        elif action_lower == "raise":
            # For raise, deduct the total raise amount
            amount_to_deduct = amount
        elif action_lower == "all-in":
            # For all-in, deduct entire stack
            amount_to_deduct = int(game_state.player_stack)
        # For fold and check, no deduction (amount_to_deduct remains 0)

        # Update player stack by deducting the bet amount
        if amount_to_deduct > 0:
            current_stack = int(game_state.player_stack)
            new_stack = current_stack - amount_to_deduct
            if new_stack < 0:
                raise Exception(
                    f"Cannot deduct {amount_to_deduct} from stack {current_stack}. Stack would be negative."
                )
            game_state.player_stack = u256(new_stack)

        # Update game state with last action
        game_state.last_action = f"{action}:{amount}"

        # If action is fold, mark game as finished
        if action.lower() == "fold":
            game_state.game_active = False
            game_state.game_stage = "finished"

        return {
            "game_id": game_id,
            "action": action,
            "amount": amount,
            "game_stage": game_state.game_stage,
            "game_active": game_state.game_active,
            "player_stack": int(game_state.player_stack),  # Return updated stack
            "amount_deducted": amount_to_deduct,  # Return how much was deducted
        }

    @gl.public.write
    def update_stage(
        self,
        game_id: str,
        board_cards: str,
        pot_size: int,
        current_bet: int,
        player_stack: typing.Optional[int] = None,
    ) -> typing.Any:
        """
        Update game stage (flop, turn, river).

        Args:
            game_id: The game ID to update
            board_cards: Community cards (3 for flop, 4 for turn, 5 for river)
            pot_size: Updated pot size
            current_bet: Updated current bet to call
            player_stack: Optional updated player stack (if not provided, keeps current stack)

        Returns:
            Dictionary with updated game state
        """
        # Get game state
        if game_id not in self.games:
            raise Exception(f"Game {game_id} not found")

        game_state = self.games[game_id]

        if not game_state.game_active:
            raise Exception(f"Game {game_id} is not active")

        if game_state.game_stage == "finished":
            raise Exception(f"Game {game_id} is finished")

        # Validate board cards count
        def count_cards(cards_str: str) -> int:
            if not cards_str:
                return 0
            suit_symbols = ["♠", "♥", "♦", "♣"]
            count = 0
            for symbol in suit_symbols:
                count += cards_str.count(symbol)
            return count

        card_count = count_cards(board_cards)

        # Determine expected stage based on card count
        if card_count == 0:
            expected_stage = "preflop"
        elif card_count == 3:
            expected_stage = "flop"
        elif card_count == 4:
            expected_stage = "turn"
        elif card_count == 5:
            expected_stage = "river"
        else:
            raise Exception(
                f"Invalid board cards count: {card_count}. Must be 0, 3, 4, or 5 cards."
            )

        # Validate stage progression
        stage_order = ["preflop", "flop", "turn", "river", "finished"]
        current_stage_idx = stage_order.index(game_state.game_stage)
        expected_stage_idx = stage_order.index(expected_stage)

        if expected_stage_idx <= current_stage_idx:
            raise Exception(
                f"Cannot go back to {expected_stage}. Current stage is {game_state.game_stage}"
            )

        # Update game state
        game_state.board_cards = board_cards
        game_state.pot_size = u256(pot_size)
        game_state.current_bet = u256(current_bet)
        game_state.game_stage = expected_stage
        game_state.last_action = ""  # Reset last action for new stage

        # Update player stack if provided
        if player_stack is not None:
            if player_stack < 0:
                raise Exception("Player stack cannot be negative")
            game_state.player_stack = u256(player_stack)

        return {
            "game_id": game_id,
            "board_cards": board_cards,
            "pot_size": pot_size,
            "current_bet": current_bet,
            "game_stage": expected_stage,
            "game_active": game_state.game_active,
            "player_stack": int(game_state.player_stack),  # Return current stack
        }

    @gl.public.view
    def get_game_state(self, game_id: str) -> typing.Any:
        """
        Get current game state.

        Args:
            game_id: The game ID to query

        Returns:
            Dictionary with all game information
        """
        if game_id not in self.games:
            raise Exception(f"Game {game_id} not found")

        game_state = self.games[game_id]

        return {
            "game_id": game_state.game_id,
            "player_address": game_state.player_address,
            "player_hand": game_state.player_hand,
            "board_cards": game_state.board_cards,
            "player_position": int(game_state.player_position),
            "num_players": int(game_state.num_players),
            "pot_size": int(game_state.pot_size),
            "small_blind": int(game_state.small_blind),
            "big_blind": int(game_state.big_blind),
            "player_stack": int(game_state.player_stack),
            "current_bet": int(game_state.current_bet),
            "game_stage": game_state.game_stage,
            "last_action": game_state.last_action,
            "game_active": game_state.game_active,
        }

