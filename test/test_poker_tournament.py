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
    """Deploy the PokerTournament contract and verify initial state."""
    factory = get_contract_factory("PokerTournament")
    contract = factory.deploy()

    # Get initial state
    initial_state = contract.get_state(args=[])
    assert initial_state["player_balances"] == []
    assert initial_state["player_hands"] == []
    assert initial_state["board_cards"] == ""
    assert initial_state["pot"] == 0
    assert initial_state["hand_winner_index"] == 0
    assert initial_state["tie_players"] == []
    assert initial_state["is_tie"] == False
    assert initial_state["last_pot_distribution"] == []
    assert initial_state["tournament_finished"] == False
    assert initial_state["tournament_winner_index"] == 0

    return contract


def test_set_player_balance():
    """Test setting player balances."""
    contract = load_fixture(deploy_contract)

    # Set balances for all players
    result = contract.set_player_balances(args=[[1000]])
    assert tx_execution_succeeded(result)

    # Verify state using view function
    state = contract.get_state(args=[])
    assert state["player_balances"] == [1000]
    assert state["tournament_finished"] == False


def test_set_player_balance_multiple_players():
    """Test setting balances for multiple players."""
    contract = load_fixture(deploy_contract)

    # Set balances for all players at once
    contract.set_player_balances(args=[[1000, 2000, 1500]])

    # Verify state
    state = contract.get_state(args=[])
    assert state["player_balances"] == [1000, 2000, 1500]
    assert state["tournament_finished"] == False


def test_set_player_balance_negative():
    """Test that setting negative balance fails."""
    contract = load_fixture(deploy_contract)

    result = contract.set_player_balances(args=[[-100]])
    assert tx_execution_failed(result)


def test_calculate_winners_with_bets():
    """Test calculating winners with player bets."""
    contract = load_fixture(deploy_contract)

    # Set initial balances
    contract.set_player_balances(args=[[1000, 1000]])

    # Player 0: Three Kings (K♦K♥ with board K♠K♦Q♥J♣2♠)
    # Player 1: Pair of Aces (A♠A♦ with same board)
    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [100, 100]  # Both players bet 100
    pot_amount = 200  # Sum of bets (calculated automatically)

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Verify state
    state = contract.get_state(args=[])
    assert state["player_hands"] == players
    assert state["board_cards"] == board_cards
    assert state["hand_winner_index"] == 0  # Player 0 should win with three Kings
    assert state["is_tie"] == False
    assert state["pot"] == pot_amount

    # Verify balances: Player 0 lost 100 bet but won 200 pot = +100 net
    # Player 1 lost 100 bet = -100 net
    assert state["player_balances"][0] == 1100  # 1000 - 100 + 200
    assert state["player_balances"][1] == 900  # 1000 - 100


def test_calculate_winners_bets_deducted():
    """Test that bets are properly deducted from balances."""
    contract = load_fixture(deploy_contract)

    # Set initial balances
    contract.set_player_balances(args=[[500, 500]])

    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [150, 50]  # Different bet amounts
    pot_amount = 200  # Sum of bets (calculated automatically)

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    state = contract.get_state(args=[])
    # Player 0 wins, so: 500 - 150 + 200 = 550
    # Player 1 loses, so: 500 - 50 = 450
    assert state["player_balances"][0] == 550
    assert state["player_balances"][1] == 450


def test_calculate_winners_tie():
    """Test calculating winners when there's a tie."""
    contract = load_fixture(deploy_contract)

    # Set initial balances
    contract.set_player_balances(args=[[1000, 1000]])

    # Two players with identical hands (same ranks, different suits)
    players = ["♠K♥K", "♦K♣K"]
    board_cards = "♠K♠Q♠J♠10♠9"
    player_bets = [100, 100]
    pot_amount = 200  # Sum of bets (calculated automatically)

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Verify state - should be a tie
    state = contract.get_state(args=[])
    assert state["is_tie"] == True
    assert state["hand_winner_index"] == 999999  # Special value for tie
    assert len(state["tie_players"]) == 2
    assert 0 in state["tie_players"]
    assert 1 in state["tie_players"]

    # Both players should split the pot: 1000 - 100 + 100 = 1000 each
    assert state["player_balances"][0] == 1000
    assert state["player_balances"][1] == 1000


def test_calculate_winners_tie_uneven_pot():
    """Test tie with uneven pot distribution."""
    contract = load_fixture(deploy_contract)

    # Set initial balances
    contract.set_player_balances(args=[[1000, 1000]])

    players = ["♠K♥K", "♦K♣K"]
    board_cards = "♠K♠Q♠J♠10♠9"
    player_bets = [100, 101]  # Different bets to create uneven pot
    pot_amount = 201  # Sum of bets (calculated automatically)

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    state = contract.get_state(args=[])
    # Pot split: 201 / 2 = 100 remainder 1, so first player gets 101, second gets 100
    # Player 0: 1000 - 100 + 101 = 1001
    # Player 1: 1000 - 101 + 100 = 999
    assert state["player_balances"][0] == 1001
    assert state["player_balances"][1] == 999


def test_calculate_winners_insufficient_balance():
    """Test that calculate_winners fails if player has insufficient balance."""
    contract = load_fixture(deploy_contract)

    # Set initial balances
    contract.set_player_balances(args=[[50, 1000]])  # Player 0 only has 50 balance

    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [100, 100]  # Player 0 tries to bet 100 but only has 50

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_failed(result)


def test_calculate_winners_bets_sum_mismatch():
    """Test removed - pot_amount is now calculated automatically from player_bets."""
    # This test is no longer relevant since pot_amount is calculated automatically
    pass


def test_calculate_winners_bets_length_mismatch():
    """Test that calculate_winners fails if player_bets length doesn't match players length."""
    contract = load_fixture(deploy_contract)

    # Set initial balances
    contract.set_player_balances(args=[[1000, 1000]])

    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [100]  # Only one bet for two players

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_failed(result)


def test_calculate_winners_negative_bet():
    """Test that calculate_winners fails if any bet is negative."""
    contract = load_fixture(deploy_contract)

    # Set initial balances
    contract.set_player_balances(args=[[1000, 1000]])

    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [-50, 100]  # Negative bet

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_failed(result)


def test_tournament_finished_single_winner():
    """Test that tournament finishes when only one player has balance."""
    contract = load_fixture(deploy_contract)

    # Set initial balances
    contract.set_player_balances(args=[[1000, 100]])

    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [50, 100]  # Player 1 bets all their money
    pot_amount = 150  # Sum of bets (calculated automatically)

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Player 0 wins, so:
    # Player 0: 1000 - 50 + 150 = 1100
    # Player 1: 100 - 100 = 0 (eliminated)

    state = contract.get_state(args=[])
    assert state["player_balances"][0] == 1100
    assert state["player_balances"][1] == 0
    assert state["tournament_finished"] == True
    assert state["tournament_winner_index"] == 0


def test_tournament_finished_via_set_balance():
    """Test that tournament finishes when setting balance leaves only one player."""
    contract = load_fixture(deploy_contract)

    # Set initial balances for 3 players
    contract.set_player_balances(args=[[1000, 500, 200]])

    # Eliminate players 1 and 2 by setting their balance to 0
    contract.set_player_balances(args=[[1000, 0, 0]])

    # Verify tournament is finished
    state = contract.get_state(args=[])
    assert state["tournament_finished"] == True
    assert state["tournament_winner_index"] == 0
    assert state["player_balances"] == [1000, 0, 0]


def test_tournament_not_finished_multiple_players():
    """Test that tournament doesn't finish when multiple players have balance."""
    contract = load_fixture(deploy_contract)

    # Set initial balances
    contract.set_player_balances(args=[[1000, 500, 200]])

    state = contract.get_state(args=[])
    assert state["tournament_finished"] == False
    assert state["player_balances"] == [1000, 500, 200]


def test_get_state_after_calculation():
    """Test that get_state returns correct information after calculation."""
    contract = load_fixture(deploy_contract)

    # Set initial balances
    contract.set_player_balances(args=[[1000, 1000]])

    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [100, 100]
    pot_amount = 200  # Sum of bets (calculated automatically)

    # Calculate winner
    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Get state and verify all fields
    state = contract.get_state(args=[])
    assert isinstance(state, dict)
    assert "player_balances" in state
    assert "player_hands" in state
    assert "board_cards" in state
    assert "pot" in state
    assert "hand_winner_index" in state
    assert "tie_players" in state
    assert "is_tie" in state
    assert "last_pot_distribution" in state
    assert "tournament_finished" in state
    assert "tournament_winner_index" in state

    assert state["player_hands"] == players
    assert state["board_cards"] == board_cards
    assert state["pot"] == pot_amount
    assert isinstance(state["hand_winner_index"], int)
    assert isinstance(state["tie_players"], list)
    assert isinstance(state["is_tie"], bool)
    assert isinstance(state["last_pot_distribution"], list)
    assert isinstance(state["tournament_finished"], bool)
    assert isinstance(state["tournament_winner_index"], int)


def test_get_last_winner():
    """Test that get_last_winner returns correct information."""
    contract = load_fixture(deploy_contract)

    # Set initial balances
    contract.set_player_balances(args=[[1000, 1000]])

    players = ["♦K♥K", "♠A♦A"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [100, 100]

    # Calculate winner
    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Get last winner info
    last_winner = contract.get_last_winner(args=[])
    assert isinstance(last_winner, dict)
    assert "player_hands" in last_winner
    assert "board_cards" in last_winner
    assert "hand_winner_index" in last_winner
    assert "tie_players" in last_winner
    assert "is_tie" in last_winner
    assert "tournament_finished" in last_winner
    assert "tournament_winner_index" in last_winner

    assert last_winner["player_hands"] == players
    assert last_winner["board_cards"] == board_cards
    assert last_winner["hand_winner_index"] == 0
    assert last_winner["is_tie"] == False


def test_multiple_hands_tournament():
    """Test multiple hands in a tournament scenario."""
    contract = load_fixture(deploy_contract)

    # Set initial balances
    contract.set_player_balances(args=[[1000, 1000]])

    # First hand: Player 0 wins
    players1 = ["♦K♥K", "♠A♦A"]
    board_cards1 = "♠K♥Q♦K♣J♠2"
    player_bets1 = [100, 100]
    pot_amount1 = 200  # Sum of bets (calculated automatically)

    result1 = contract.calculate_winners(
        args=[players1, board_cards1, player_bets1],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result1)

    state1 = contract.get_state(args=[])
    assert state1["player_balances"][0] == 1100  # 1000 - 100 + 200
    assert state1["player_balances"][1] == 900  # 1000 - 100
    assert state1["tournament_finished"] == False

    # Second hand: Player 1 wins
    players2 = ["♠2♦2", "♠Q♦Q"]
    board_cards2 = "♠Q♥Q♦Q♣J♠2"
    player_bets2 = [50, 50]
    pot_amount2 = 100  # Sum of bets (calculated automatically)

    result2 = contract.calculate_winners(
        args=[players2, board_cards2, player_bets2],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result2)

    state2 = contract.get_state(args=[])
    assert state2["player_balances"][0] == 1050  # 1100 - 50
    assert state2["player_balances"][1] == 950  # 900 - 50 + 100
    assert state2["tournament_finished"] == False


def test_tournament_ends_after_multiple_hands():
    """Test that tournament ends after multiple hands when one player is eliminated."""
    contract = load_fixture(deploy_contract)

    # Set initial balances
    contract.set_player_balances(args=[[1000, 200]])

    # First hand: Player 0 wins, Player 1 loses
    players1 = ["♦K♥K", "♠A♦A"]
    board_cards1 = "♠K♥Q♦K♣J♠2"
    player_bets1 = [100, 100]
    pot_amount1 = 200  # Sum of bets (calculated automatically)

    result1 = contract.calculate_winners(
        args=[players1, board_cards1, player_bets1],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result1)

    state1 = contract.get_state(args=[])
    assert state1["player_balances"][0] == 1100
    assert state1["player_balances"][1] == 100
    assert state1["tournament_finished"] == False

    # Second hand: Player 1 bets all remaining money and loses
    players2 = ["♠Q♦Q", "♠2♦2"]
    board_cards2 = "♠Q♥Q♦Q♣J♠2"
    player_bets2 = [50, 100]  # Player 1 goes all-in
    pot_amount2 = 150  # Sum of bets (calculated automatically)

    result2 = contract.calculate_winners(
        args=[players2, board_cards2, player_bets2],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result2)

    state2 = contract.get_state(args=[])
    assert state2["player_balances"][0] == 1200  # 1100 - 50 + 150
    assert state2["player_balances"][1] == 0  # 100 - 100
    assert state2["tournament_finished"] == True
    assert state2["tournament_winner_index"] == 0


def test_last_pot_distribution():
    """Test that last_pot_distribution tracks pot distribution correctly."""
    contract = load_fixture(deploy_contract)

    # Set initial balances
    contract.set_player_balances(args=[[1000, 1000, 1000]])

    players = ["♦K♥K", "♠A♦A", "♠2♦2"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [100, 100, 100]
    pot_amount = 300  # Sum of bets (calculated automatically)

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    state = contract.get_state(args=[])
    # Player 0 wins, so should receive 300
    assert state["last_pot_distribution"][0] == 300
    assert state["last_pot_distribution"][1] == 0
    assert state["last_pot_distribution"][2] == 0


def test_insufficient_players():
    """Test that calling calculate_winners with less than 2 players fails."""
    contract = load_fixture(deploy_contract)

    players = ["♦K♥K"]
    board_cards = "♠K♥Q♦K♣J♠2"
    player_bets = [100]

    result = contract.calculate_winners(
        args=[players, board_cards, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_failed(result)


def test_board_cards_validation():
    """Test board cards validation (must be empty or exactly 5 cards)."""
    contract = load_fixture(deploy_contract)

    # Set initial balances
    contract.set_player_balances(args=[[1000, 1000]])

    players = ["♦K♥K", "♠A♦A"]
    player_bets = [100, 100]

    # Test with 3 cards (should fail)
    board_cards_3 = "♠K♥Q♦K"
    result = contract.calculate_winners(
        args=[players, board_cards_3, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_failed(result)

    # Test with 5 cards (should succeed)
    board_cards_5 = "♠K♥Q♦K♣J♠2"
    result = contract.calculate_winners(
        args=[players, board_cards_5, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)

    # Test with empty board (should succeed)
    board_cards_empty = ""
    result = contract.calculate_winners(
        args=[players, board_cards_empty, player_bets],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(result)
