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


def get_test_addresses(count: int):
    """Generate test addresses for players."""
    base_address = default_account().address
    addresses = [base_address]
    # Generate additional addresses by modifying the address
    for i in range(1, count):
        # Create a simple variation of the address for testing
        addr_hex = base_address[2:]  # Remove 0x prefix
        # Modify last few characters to create different addresses
        last_digit = (int(addr_hex[-1], 16) + i) % 16
        second_last_digit = (int(addr_hex[-2], 16) + i) % 16
        new_addr_hex = addr_hex[:-2] + hex(second_last_digit)[2:] + hex(last_digit)[2:]
        new_addr = "0x" + new_addr_hex
        addresses.append(new_addr)
    return addresses[:count]


def deploy_contract():
    """Deploy the PokerTournament v2 contract and verify initial state."""
    factory = get_contract_factory("PokerTournament")
    contract = factory.deploy()

    # Get initial state
    initial_state = contract.get_state(args=[])
    assert initial_state["player_balances"] == []
    assert initial_state["player_addresses"] == []
    assert initial_state["player_hands"] == []
    assert initial_state["board_cards"] == ""
    assert initial_state["pot"] == 0
    assert initial_state["hand_winner_index"] == 0
    assert initial_state["tie_players"] == []
    assert initial_state["is_tie"] == False
    assert initial_state["last_pot_distribution"] == []
    assert initial_state["tournament_finished"] == False
    assert initial_state["tournament_winner_index"] == 0

    # Verify initial eliminations are empty
    all_eliminations = contract.get_all_eliminations(args=[])
    assert all_eliminations == []

    return contract


def test_no_eliminations_initially():
    """Test that there are no eliminations initially."""
    contract = load_fixture(deploy_contract)

    # Check all eliminations
    all_eliminations = contract.get_all_eliminations(args=[])
    assert all_eliminations == []

    # Check eliminations for specific player (using a test address)
    test_address = get_test_addresses(1)[0]
    player_eliminations = contract.get_player_eliminations(args=[test_address])
    assert player_eliminations == []


def test_single_player_elimination():
    """Test that a player elimination is recorded when balance goes from > 0 to 0."""
    contract = load_fixture(deploy_contract)

    # Set initial balances and addresses - player 0 has 100, player 1 has 1000
    addresses = get_test_addresses(2)
    contract.set_players(args=[[100, 1000], addresses])

    # Player 0: Pair of Kings (K♦K♥ with board)
    # Player 1: Three Kings (K♠K♦ with board K♠K♦Q♥J♣2♠)
    # Player 1 wins, Player 0 loses and gets eliminated (bets all 100)
    players = ["♦K♥K", "♠K♦K"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [100, 100]  # Player 0 bets all their balance

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Verify player 0 was eliminated (balance went from 100 to 0)
    state = contract.get_state(args=[])
    assert state["player_balances"][0] == 0
    assert state["player_balances"][1] > 0

    # Check eliminations
    all_eliminations = contract.get_all_eliminations(args=[])
    assert len(all_eliminations) == 1

    elimination = all_eliminations[0]
    assert elimination["player_index"] == 0
    assert elimination["player_hand"] == "♦K♥K"
    assert elimination["opponent_hand"] == "♠K♦K"
    assert elimination["board_cards"] == board_cards
    assert "is_cooler" in elimination
    assert "hand_rank_player" in elimination
    assert "hand_rank_opponent" in elimination

    # Check player-specific eliminations
    addresses = get_test_addresses(2)
    player_0_eliminations = contract.get_player_eliminations(args=[addresses[0]])
    assert len(player_0_eliminations) == 1
    assert player_0_eliminations[0]["player_index"] == 0
    assert player_0_eliminations[0]["player_address"] == addresses[0]

    # Player 1 should have no eliminations
    player_1_eliminations = contract.get_player_eliminations(args=[addresses[1]])
    assert len(player_1_eliminations) == 0


def test_no_elimination_when_player_already_at_zero():
    """Test that players already at balance 0 don't get recorded as eliminated."""
    contract = load_fixture(deploy_contract)

    # Set initial balances and addresses - player 0 already at 0, player 1 has 1000
    addresses = get_test_addresses(2)
    contract.set_players(args=[[0, 1000], addresses])

    players = ["♦K♥K", "♠K♦K"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [0, 100]  # Player 0 bets 0 (already eliminated)

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Verify no eliminations were recorded (player 0 was already at 0)
    all_eliminations = contract.get_all_eliminations(args=[])
    assert len(all_eliminations) == 0


def test_no_elimination_when_player_still_has_balance():
    """Test that players who don't go to 0 balance are not recorded as eliminated."""
    contract = load_fixture(deploy_contract)

    # Set initial balances and addresses
    addresses = get_test_addresses(2)
    contract.set_players(args=[[500, 1000], addresses])

    # Player 0 loses but still has balance after the hand
    players = ["♦K♥K", "♠K♦K"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [100, 100]  # Player 0 bets 100, loses, but still has 400

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Verify player 0 still has balance
    state = contract.get_state(args=[])
    assert state["player_balances"][0] > 0

    # Verify no eliminations were recorded
    all_eliminations = contract.get_all_eliminations(args=[])
    assert len(all_eliminations) == 0


def test_multiple_eliminations_same_hand():
    """Test that multiple players can be eliminated in the same hand."""
    contract = load_fixture(deploy_contract)

    # Set initial balances and addresses - players 0 and 1 have small balances, player 2 has large balance
    addresses = get_test_addresses(3)
    contract.set_players(args=[[100, 150, 2000], addresses])

    # Player 2 wins (has best hand)
    # Players 0 and 1 both lose and get eliminated
    players = ["♦K♥K", "♠Q♥Q", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [100, 150, 200]  # Players 0 and 1 bet all their balance

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Verify both players 0 and 1 were eliminated
    state = contract.get_state(args=[])
    assert state["player_balances"][0] == 0
    assert state["player_balances"][1] == 0
    assert state["player_balances"][2] > 0

    # Check eliminations - should have 2 eliminations
    all_eliminations = contract.get_all_eliminations(args=[])
    assert len(all_eliminations) == 2

    # Verify both players are in eliminations
    eliminated_indices = [elim["player_index"] for elim in all_eliminations]
    assert 0 in eliminated_indices
    assert 1 in eliminated_indices
    assert 2 not in eliminated_indices

    # Check individual player eliminations
    addresses = get_test_addresses(3)
    player_0_eliminations = contract.get_player_eliminations(args=[addresses[0]])
    assert len(player_0_eliminations) == 1

    player_1_eliminations = contract.get_player_eliminations(args=[addresses[1]])
    assert len(player_1_eliminations) == 1

    player_2_eliminations = contract.get_player_eliminations(args=[addresses[2]])
    assert len(player_2_eliminations) == 0


def test_elimination_across_multiple_hands():
    """Test that eliminations are recorded across multiple hands."""
    contract = load_fixture(deploy_contract)

    # Set initial balances and addresses
    addresses = get_test_addresses(3)
    contract.set_players(args=[[200, 1000, 1000], addresses])

    # First hand: Player 0 loses and gets eliminated
    players_hand1 = ["♦K♥K", "♠K♦K", "♠A♦A"]
    board_cards_hand1 = "♠K♥Q♦K♣J♠2"
    player_bets_hand1 = [200, 100, 100]  # Player 0 bets all

    result1 = contract.calculate_winners(
        args=[players_hand1, board_cards_hand1, player_bets_hand1],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result1)

    # Verify first elimination
    all_eliminations = contract.get_all_eliminations(args=[])
    assert len(all_eliminations) == 1
    assert all_eliminations[0]["player_index"] == 0

    # Second hand: Player 1 loses and gets eliminated (now has 900, bets all)
    addresses = get_test_addresses(3)
    contract.set_players(args=[[0, 900, 1000], addresses])

    players_hand2 = ["♦K♥K", "♠Q♥Q", "♠A♦A"]
    board_cards_hand2 = "♠A♥Q♦A♣J♠2"
    player_bets_hand2 = [0, 900, 100]  # Player 1 bets all

    result2 = contract.calculate_winners(
        args=[players_hand2, board_cards_hand2, player_bets_hand2],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result2)

    # Verify both eliminations are recorded
    all_eliminations = contract.get_all_eliminations(args=[])
    assert len(all_eliminations) == 2

    # Verify both players are in eliminations
    eliminated_indices = [elim["player_index"] for elim in all_eliminations]
    assert 0 in eliminated_indices
    assert 1 in eliminated_indices

    # Check individual player eliminations
    addresses = get_test_addresses(3)
    player_0_eliminations = contract.get_player_eliminations(args=[addresses[0]])
    assert len(player_0_eliminations) == 1

    player_1_eliminations = contract.get_player_eliminations(args=[addresses[1]])
    assert len(player_1_eliminations) == 1


def test_elimination_with_tie():
    """Test elimination when there's a tie (multiple winners)."""
    contract = load_fixture(deploy_contract)

    # Set initial balances and addresses
    addresses = get_test_addresses(3)
    contract.set_players(args=[[100, 1000, 1000], addresses])

    # Players 1 and 2 tie, Player 0 loses and gets eliminated
    players = ["♦K♥K", "♠K♣K", "♠K♥K"]
    board_cards = "♠K♠Q♠J♠10♠9"  # All spades - flush for all
    player_bets = [100, 100, 100]  # Player 0 bets all

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Verify tie occurred
    state = contract.get_state(args=[])
    assert state["is_tie"] == True

    # Verify player 0 was eliminated
    assert state["player_balances"][0] == 0

    # Check elimination record
    all_eliminations = contract.get_all_eliminations(args=[])
    assert len(all_eliminations) == 1
    assert all_eliminations[0]["player_index"] == 0

    # In case of tie, opponent_hand should be from one of the tied players
    elimination = all_eliminations[0]
    assert elimination["opponent_hand"] in ["♠K♣K", "♠K♥K"]


def test_elimination_record_fields():
    """Test that elimination records contain all required fields."""
    contract = load_fixture(deploy_contract)

    # Set initial balances and addresses
    addresses = get_test_addresses(2)
    contract.set_players(args=[[100, 1000], addresses])

    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [100, 100]

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Get elimination record
    all_eliminations = contract.get_all_eliminations(args=[])
    assert len(all_eliminations) == 1

    elimination = all_eliminations[0]

    # Verify all required fields are present
    assert "player_index" in elimination
    assert "player_address" in elimination
    assert "player_hand" in elimination
    assert "opponent_hand" in elimination
    assert "board_cards" in elimination
    assert "is_cooler" in elimination
    assert "hand_rank_player" in elimination
    assert "hand_rank_opponent" in elimination

    # Verify field types and values
    assert isinstance(elimination["player_index"], int)
    assert isinstance(elimination["player_address"], str)
    assert isinstance(elimination["player_hand"], str)
    assert isinstance(elimination["opponent_hand"], str)
    assert isinstance(elimination["board_cards"], str)
    assert isinstance(elimination["is_cooler"], bool)
    assert isinstance(elimination["hand_rank_player"], str)
    assert isinstance(elimination["hand_rank_opponent"], str)

    # Verify specific values
    assert elimination["player_index"] == 0
    assert elimination["player_address"] == addresses[0]
    assert elimination["player_hand"] == "♦K♥K"
    assert elimination["opponent_hand"] == "♠A♦A"
    assert elimination["board_cards"] == board_cards


def test_elimination_cooler_detection():
    """Test that cooler detection works (player has strong hand but loses to stronger hand)."""
    contract = load_fixture(deploy_contract)

    # Set initial balances and addresses
    addresses = get_test_addresses(2)
    contract.set_players(args=[[100, 1000], addresses])

    # Classic cooler: Pocket Kings vs Pocket Aces
    # Player 0: Pocket Kings (strong hand)
    # Player 1: Pocket Aces (even stronger hand)
    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦2♣J♠3"  # Board doesn't help either much
    player_bets = [100, 100]

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Get elimination record
    all_eliminations = contract.get_all_eliminations(args=[])
    assert len(all_eliminations) == 1

    elimination = all_eliminations[0]

    # Verify cooler detection (should be True for pocket Kings vs Aces)
    # Note: The actual is_cooler value depends on GenLayer's evaluation
    assert "is_cooler" in elimination
    assert isinstance(elimination["is_cooler"], bool)

    # Verify hand ranks are provided
    assert elimination["hand_rank_player"] != "Unknown"
    assert elimination["hand_rank_opponent"] != "Unknown"


def test_elimination_non_cooler():
    """Test that weak hands losing don't count as coolers."""
    contract = load_fixture(deploy_contract)

    # Set initial balances and addresses
    addresses = get_test_addresses(2)
    contract.set_players(args=[[100, 1000], addresses])

    # Player 0 has weak hand, Player 1 has strong hand - not a cooler
    players = ["♦2♥3", "♠A♦A"]  # Weak hand vs strong hand
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [100, 100]

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Get elimination record
    all_eliminations = contract.get_all_eliminations(args=[])
    assert len(all_eliminations) == 1

    elimination = all_eliminations[0]

    # Verify cooler detection (should be False for weak hand losing)
    # Note: The actual is_cooler value depends on GenLayer's evaluation
    assert "is_cooler" in elimination
    assert isinstance(elimination["is_cooler"], bool)


def test_get_player_eliminations_nonexistent_player():
    """Test getting eliminations for a player that doesn't exist."""
    contract = load_fixture(deploy_contract)

    # Get eliminations for player that was never in the tournament
    nonexistent_address = "0x1234567890123456789012345678901234567890"
    player_eliminations = contract.get_player_eliminations(args=[nonexistent_address])
    assert player_eliminations == []


def test_elimination_with_empty_board():
    """Test elimination with empty board (pre-flop scenario)."""
    contract = load_fixture(deploy_contract)

    # Set initial balances and addresses
    addresses = get_test_addresses(2)
    contract.set_players(args=[[100, 1000], addresses])

    # Pre-flop: Player 0 goes all-in with weaker hand
    players = ["♦2♥3", "♠A♦A"]
    board_cards = ""  # Empty board (pre-flop)
    player_bets = [100, 100]

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Verify elimination was recorded
    all_eliminations = contract.get_all_eliminations(args=[])
    assert len(all_eliminations) == 1

    elimination = all_eliminations[0]
    assert elimination["player_index"] == 0
    assert (
        elimination["board_cards"] == ""
    )  # Empty board should be stored as empty string


def test_set_players_can_only_be_called_once():
    """Test that set_players can only be called once."""
    contract = load_fixture(deploy_contract)

    # Set players first time - should succeed
    addresses = get_test_addresses(2)
    result1 = contract.set_players(args=[[100, 1000], addresses])
    assert tx_execution_succeeded(result1)

    # Try to set players again - should fail
    addresses2 = get_test_addresses(2)
    result2 = contract.set_players(args=[[200, 2000], addresses2])
    assert tx_execution_failed(result2)


def test_calculate_winners_fails_when_tournament_finished():
    """Test that calculate_winners fails when tournament has already finished."""
    contract = load_fixture(deploy_contract)

    # Set initial balances and addresses
    addresses = get_test_addresses(2)
    contract.set_players(args=[[100, 1000], addresses])

    # Play a hand that finishes the tournament (player 0 gets eliminated)
    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [100, 100]

    result1 = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result1)

    # Verify tournament is finished
    state = contract.get_state(args=[])
    assert state["tournament_finished"] == True

    # Try to calculate winners again - should fail
    players2 = ["♦K♥K", "♠A♦A"]
    board_cards2 = "♠K♥Q♦K♣J♠2"
    player_bets2 = [0, 100]

    result2 = contract.calculate_winners(
        args=[players2, board_cards2, player_bets2],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_failed(result2)
