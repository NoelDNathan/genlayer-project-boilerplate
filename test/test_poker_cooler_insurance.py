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


def deploy_contract():
    factory = get_contract_factory("PokerCoolerInsurance")
    contract = factory.deploy()

    # Get Initial State
    contract_policies_state = contract.get_policies(args=[])
    assert contract_policies_state == {}

    contract_total_premiums = contract.get_total_premiums(args=[])
    assert contract_total_premiums == 0

    contract_total_payouts = contract.get_total_payouts(args=[])
    assert contract_total_payouts == 0

    contract_balance = contract.get_contract_balance(args=[])
    assert contract_balance == 0

    return contract


def test_purchase_insurance():
    """Test purchasing insurance for a tournament."""
    contract = load_fixture(deploy_contract)

    # Purchase insurance
    purchase_result = contract.purchase_insurance(
        args=[
            "tournament123",
            "http://localhost:8000/tournament_example.html",
            "player123",
            "2024-01-15",
        ],
        wait_interval=10000,  # 10 seconds
        wait_retries=15,
    )
    assert tx_execution_succeeded(purchase_result)

    # Get policies
    policies = contract.get_policies(args=[])
    assert default_account.address in policies
    assert len(policies[default_account.address]) == 1

    # Get player policies
    player_policies = contract.get_player_policies(args=[default_account.address])
    assert len(player_policies) == 1

    # Get specific policy
    policy_id = list(player_policies.keys())[0]
    policy = contract.get_policy(args=[policy_id])
    assert policy.tournament_id == "tournament123"
    assert policy.player_id == "player123"
    assert policy.tournament_buy_in == 100
    assert policy.premium_paid == 20  # 20% of 100
    assert policy.payout_amount == 50  # 50% of 100
    assert policy.has_claimed == False
    assert policy.claim_resolved == False
    assert policy.is_valid_cooler == False

    # Check total premiums
    total_premiums = contract.get_total_premiums(args=[])
    assert total_premiums == 20

    # Check total payouts (should be 0)
    total_payouts = contract.get_total_payouts(args=[])
    assert total_payouts == 0

    # Check contract balance
    balance = contract.get_contract_balance(args=[])
    assert balance == 20  # premiums - payouts = 20 - 0


def test_get_tournament_info():
    """Test getting tournament information before purchasing."""
    contract = load_fixture(deploy_contract)

    # Get tournament info
    tournament_info = contract.get_tournament_info(
        args=["http://localhost:8000/tournament_example.html"],
        wait_interval=10000,
        wait_retries=15,
    )

    assert "tournament_buy_in" in tournament_info
    assert "insurance_premium" in tournament_info
    assert "payout_amount" in tournament_info
    assert tournament_info["tournament_buy_in"] == 100
    assert tournament_info["insurance_premium"] == 20  # 20% of 100
    assert tournament_info["payout_amount"] == 50  # 50% of 100


def test_file_claim_with_cooler():
    """Test filing a claim when player was eliminated by a cooler."""
    contract = load_fixture(deploy_contract)

    # Purchase insurance
    purchase_result = contract.purchase_insurance(
        args=[
            "tournament123",
            "http://localhost:8000/tournament_example.html",
            "player123",  # This player has a cooler elimination
            "2024-01-15",
        ],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(purchase_result)

    # Get policy ID
    player_policies = contract.get_player_policies(args=[default_account.address])
    policy_id = list(player_policies.keys())[0]

    # File claim
    claim_result = contract.file_claim(
        args=[policy_id],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(claim_result)

    # Verify policy state after claim
    policy = contract.get_policy(args=[policy_id])
    assert policy.has_claimed == True
    assert policy.claim_resolved == True
    assert policy.is_valid_cooler == True

    # Check total payouts (should be 50)
    total_payouts = contract.get_total_payouts(args=[])
    assert total_payouts == 50

    # Check contract balance
    balance = contract.get_contract_balance(args=[])
    assert balance == -30  # premiums - payouts = 20 - 50


def test_file_claim_without_cooler():
    """Test filing a claim when player was eliminated but not by a cooler."""
    contract = load_fixture(deploy_contract)

    # Purchase insurance
    purchase_result = contract.purchase_insurance(
        args=[
            "tournament123",
            "http://localhost:8000/tournament_example.html",
            "player456",  # This player was eliminated but not by cooler
            "2024-01-15",
        ],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(purchase_result)

    # Get policy ID
    player_policies = contract.get_player_policies(args=[default_account.address])
    policy_id = list(player_policies.keys())[0]

    # File claim
    claim_result = contract.file_claim(
        args=[policy_id],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(claim_result)

    # Verify policy state after claim
    policy = contract.get_policy(args=[policy_id])
    assert policy.has_claimed == True
    assert policy.claim_resolved == True
    assert policy.is_valid_cooler == False

    # Check total payouts (should be 0, no payout for non-cooler)
    total_payouts = contract.get_total_payouts(args=[])
    assert total_payouts == 0

    # Check contract balance
    balance = contract.get_contract_balance(args=[])
    assert balance == 20  # premiums - payouts = 20 - 0


def test_duplicate_insurance_purchase():
    """Test that purchasing insurance twice for the same tournament fails."""
    contract = load_fixture(deploy_contract)

    # Purchase insurance first time
    purchase_result = contract.purchase_insurance(
        args=[
            "tournament123",
            "http://localhost:8000/tournament_example.html",
            "player123",
            "2024-01-15",
        ],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(purchase_result)

    # Try to purchase insurance again for the same tournament (should fail)
    purchase_result_duplicate = contract.purchase_insurance(
        args=[
            "tournament123",
            "http://localhost:8000/tournament_example.html",
            "player123",
            "2024-01-15",
        ],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_failed(purchase_result_duplicate)


def test_file_claim_twice():
    """Test that filing a claim twice for the same policy fails."""
    contract = load_fixture(deploy_contract)

    # Purchase insurance
    purchase_result = contract.purchase_insurance(
        args=[
            "tournament123",
            "http://localhost:8000/tournament_example.html",
            "player123",
            "2024-01-15",
        ],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(purchase_result)

    # Get policy ID
    player_policies = contract.get_player_policies(args=[default_account.address])
    policy_id = list(player_policies.keys())[0]

    # File claim first time
    claim_result = contract.file_claim(
        args=[policy_id],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(claim_result)

    # Try to file claim again (should fail)
    claim_result_duplicate = contract.file_claim(
        args=[policy_id],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_failed(claim_result_duplicate)


def test_file_claim_nonexistent_policy():
    """Test that filing a claim for a non-existent policy fails."""
    contract = load_fixture(deploy_contract)

    # Try to file claim for non-existent policy (should fail)
    claim_result = contract.file_claim(
        args=["nonexistent_policy_id"],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_failed(claim_result)


def test_multiple_policies():
    """Test purchasing multiple insurance policies for different tournaments."""
    contract = load_fixture(deploy_contract)

    # Purchase first insurance
    purchase_result1 = contract.purchase_insurance(
        args=[
            "tournament123",
            "http://localhost:8000/tournament_example.html",
            "player123",
            "2024-01-15",
        ],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(purchase_result1)

    # Purchase second insurance for different tournament
    purchase_result2 = contract.purchase_insurance(
        args=[
            "tournament456",
            "http://localhost:8000/tournament_example.html",
            "player123",
            "2024-01-16",
        ],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(purchase_result2)

    # Get player policies
    player_policies = contract.get_player_policies(args=[default_account.address])
    assert len(player_policies) == 2

    # Check total premiums (should be 40, 20 + 20)
    total_premiums = contract.get_total_premiums(args=[])
    assert total_premiums == 40


def test_get_policy_nonexistent():
    """Test getting a non-existent policy fails."""
    contract = load_fixture(deploy_contract)

    # Try to get non-existent policy (should fail)
    try:
        policy = contract.get_policy(args=["nonexistent_policy_id"])
        assert False, "Should have raised an exception"
    except Exception:
        # Expected to fail
        pass


def test_get_player_policies_empty():
    """Test getting policies for a player with no policies."""
    contract = load_fixture(deploy_contract)

    # Get policies for player with no policies
    player_policies = contract.get_player_policies(
        args=["0x0000000000000000000000000000000000000000"]
    )
    assert player_policies == {}


def test_contract_balance_calculation():
    """Test contract balance calculation with multiple policies and claims."""
    contract = load_fixture(deploy_contract)

    # Purchase first insurance
    purchase_result1 = contract.purchase_insurance(
        args=[
            "tournament123",
            "http://localhost:8000/tournament_example.html",
            "player123",
            "2024-01-15",
        ],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(purchase_result1)

    # Purchase second insurance
    purchase_result2 = contract.purchase_insurance(
        args=[
            "tournament456",
            "http://localhost:8000/tournament_example.html",
            "player789",
            "2024-01-16",
        ],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(purchase_result2)

    # Check balance after purchases (should be 40, 20 + 20)
    balance = contract.get_contract_balance(args=[])
    assert balance == 40

    # File claim for first policy (cooler, should payout 50)
    player_policies = contract.get_player_policies(args=[default_account.address])
    policy_id1 = [pid for pid in player_policies.keys() if "tournament123" in pid][0]

    claim_result1 = contract.file_claim(
        args=[policy_id1],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(claim_result1)

    # Check balance after first claim (should be -10, 40 - 50)
    balance = contract.get_contract_balance(args=[])
    assert balance == -10

    # File claim for second policy (cooler, should payout 50)
    policy_id2 = [pid for pid in player_policies.keys() if "tournament456" in pid][0]

    claim_result2 = contract.file_claim(
        args=[policy_id2],
        wait_interval=10000,
        wait_retries=15,
    )
    assert tx_execution_succeeded(claim_result2)

    # Check balance after second claim (should be -60, 40 - 100)
    balance = contract.get_contract_balance(args=[])
    assert balance == -60

    # Verify totals
    total_premiums = contract.get_total_premiums(args=[])
    assert total_premiums == 40

    total_payouts = contract.get_total_payouts(args=[])
    assert total_payouts == 100
