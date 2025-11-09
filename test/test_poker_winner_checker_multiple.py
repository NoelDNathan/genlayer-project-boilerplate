from gltest import get_contract_factory, default_account
from gltest.helpers import load_fixture
import gltest.assertions
import gltest.glchain.contract
from test.assertions_fix import (
    tx_execution_succeeded,
    tx_execution_failed as fixed_tx_execution_failed,
)

# Patch the assertions to handle leader_receipt as list (can be list or dict)
gltest.assertions.tx_execution_succeeded = tx_execution_succeeded
gltest.assertions.tx_execution_failed = fixed_tx_execution_failed
# Also patch in the contract module since it imports the function directly
gltest.glchain.contract.tx_execution_failed = fixed_tx_execution_failed

# Create alias for easier use in tests
tx_execution_failed = fixed_tx_execution_failed


def deploy_contract():
    """Deploy the PokerWinnerCheckerMultiple contract and verify initial state."""
    factory = get_contract_factory("PokerWinnerCheckerMultiple")
    contract = factory.deploy()

    # Get initial state
    initial_state = contract.get_state(args=[])
    assert initial_state["player_hands"] == []
    assert initial_state["board_cards"] == ""
    assert initial_state["winner_index"] == 0
    assert initial_state["tie_players"] == []
    assert initial_state["is_tie"] == False

    return contract


def test_calculate_winner_three_of_a_kind_vs_pair():
    """Test calculating winner with three of a kind beating a pair."""
    contract = load_fixture(deploy_contract)

    # Player 0: Three Kings (K♦K♥ with board K♠K♦Q♥J♣2♠)
    # Player 1: Pair of Aces (A♠A♦ with same board)
    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2"

    result = contract.calculate_winner_and_store(
        args=[players, board_cards],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Verify state
    state = contract.get_state(args=[])
    assert state["player_hands"] == players
    assert state["board_cards"] == board_cards
    assert state["winner_index"] == 0  # Player 0 should win with three Kings
    assert state["is_tie"] == False
    assert state["tie_players"] == []


def test_calculate_winner_multiple_players():
    """Test calculating winner with multiple players."""
    contract = load_fixture(deploy_contract)

    # Player 0: Three Kings
    # Player 1: Three Queens
    # Player 2: Three Deuces
    # Player 3: Pair of Aces
    players = ["♦K♥K", "♠Q♦Q", "♠2♦2", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2"

    result = contract.calculate_winner_and_store(
        args=[players, board_cards],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Verify state - Player 0 should win with three Kings
    state = contract.get_state(args=[])
    assert state["player_hands"] == players
    assert state["board_cards"] == board_cards
    assert state["winner_index"] == 0
    assert state["is_tie"] == False


def test_calculate_winner_tie():
    """Test calculating winner when there's a tie."""
    contract = load_fixture(deploy_contract)

    # Two players with identical hands (same ranks, different suits)
    # Both have King-high flush
    players = ["♠K♥K", "♦K♣K"]
    board_cards = "♠K♠Q♠J♠10♠9"

    result = contract.calculate_winner_and_store(
        args=[players, board_cards],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Verify state - should be a tie
    state = contract.get_state(args=[])
    assert state["is_tie"] == True
    assert state["winner_index"] == 999999  # Special value for tie
    assert len(state["tie_players"]) == 2
    assert 0 in state["tie_players"]
    assert 1 in state["tie_players"]


def test_multiple_executions():
    """Test that the function can be executed multiple times with different inputs."""
    contract = load_fixture(deploy_contract)

    # First execution
    players1 = ["♦K♥K", "♠A♦A"]
    board_cards1 = "♠K♥Q♦K♣J♠2"

    result1 = contract.calculate_winner_and_store(
        args=[players1, board_cards1],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result1)

    state1 = contract.get_state(args=[])
    assert state1["player_hands"] == players1
    assert state1["board_cards"] == board_cards1

    # Second execution with different inputs
    players2 = ["♠Q♦Q", "♠2♦2"]
    board_cards2 = "♠Q♥Q♦Q♣J♠2"

    result2 = contract.calculate_winner_and_store(
        args=[players2, board_cards2],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result2)

    # Verify state was updated
    state2 = contract.get_state(args=[])
    assert state2["player_hands"] == players2
    assert state2["board_cards"] == board_cards2
    # Player 0 should win with four Queens
    assert state2["winner_index"] == 0


def test_insufficient_players():
    """Test that calling with less than 2 players fails."""
    contract = load_fixture(deploy_contract)

    # Try with only one player
    players = ["♦K♥K"]
    board_cards = "♠K♥Q♦K♣J♠2"

    result = contract.calculate_winner_and_store(
        args=[players, board_cards],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_failed(result)


def test_board_cards_less_than_five():
    """Test that calling with less than 5 board cards (and not empty) fails."""
    contract = load_fixture(deploy_contract)

    # Try with only 3 cards (flop scenario, but we require 5 or empty)
    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦K"  # Only 3 cards

    result = contract.calculate_winner_and_store(
        args=[players, board_cards],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_failed(result)


def test_board_cards_more_than_five():
    """Test that calling with more than 5 board cards fails."""
    contract = load_fixture(deploy_contract)

    # Try with 6 cards (invalid)
    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2♠3"  # 7 cards

    result = contract.calculate_winner_and_store(
        args=[players, board_cards],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_failed(result)


def test_board_cards_exactly_five():
    """Test that calling with exactly 5 board cards succeeds."""
    contract = load_fixture(deploy_contract)

    # Valid case with exactly 5 cards
    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2"  # Exactly 5 cards

    result = contract.calculate_winner_and_store(
        args=[players, board_cards],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Verify state
    state = contract.get_state(args=[])
    assert state["board_cards"] == board_cards


def test_flush_vs_straight():
    """Test flush beating a straight."""
    contract = load_fixture(deploy_contract)

    # Player 0: Flush (all spades)
    # Player 1: Straight
    players = ["♥A♥K", "♠Q♠J"]
    board_cards = "♠2♠3♠10♠7♥8"

    result = contract.calculate_winner_and_store(
        args=[players, board_cards],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Verify state - Player 1 should win with straight
    state = contract.get_state(args=[])
    assert state["winner_index"] == 1
    assert state["is_tie"] == False


def test_full_house_vs_two_pair():
    """Test full house beating two pair."""
    contract = load_fixture(deploy_contract)

    # Player 0: Full house (three Kings, two Aces)
    # Player 1: Two pair (Kings and Queens)
    players = ["♠K♦2", "♠4♦3"]
    board_cards = "♠K♥K♦K♠A♦A"

    result = contract.calculate_winner_and_store(
        args=[players, board_cards],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Verify state - Player 0 should win with full house
    state = contract.get_state(args=[])
    assert state["winner_index"] == 0
    assert state["is_tie"] == False


def test_get_state_after_calculation():
    """Test that get_state returns correct information after calculation."""
    contract = load_fixture(deploy_contract)

    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2"

    # Calculate winner
    result = contract.calculate_winner_and_store(
        args=[players, board_cards],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Get state and verify all fields
    state = contract.get_state(args=[])
    assert isinstance(state, dict)
    assert "player_hands" in state
    assert "board_cards" in state
    assert "winner_index" in state
    assert "tie_players" in state
    assert "is_tie" in state

    assert state["player_hands"] == players
    assert state["board_cards"] == board_cards
    assert isinstance(state["winner_index"], int)
    assert isinstance(state["tie_players"], list)
    assert isinstance(state["is_tie"], bool)
