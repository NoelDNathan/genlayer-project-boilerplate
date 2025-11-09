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
    """Deploy the NFTContract and verify initial state."""
    factory = get_contract_factory("NFTContract")
    contract = factory.deploy()

    # Verify initial state
    assert contract.total_supply_count(args=[]) == 0
    assert contract.balance_of(args=[default_account().address]) == 0

    return contract


def test_mint_nft():
    """Test minting a new NFT."""
    contract = load_fixture(deploy_contract)
    account = default_account()

    # Mint an NFT
    result = contract.mint(
        args=[
            account.address,
            "My First NFT",
            "This is a test NFT",
            12345,  # block_number
            '{"rarity": "common"}',
        ]
    )
    assert tx_execution_succeeded(result)

    # Verify token was minted
    assert contract.total_supply_count(args=[]) == 1
    assert contract.balance_of(args=[account.address]) == 1

    # Verify ownership
    owner = contract.owner_of(args=[0])
    assert owner == account.address

    # Verify metadata
    metadata = contract.get_metadata(args=[0])
    assert metadata["name"] == "My First NFT"
    assert metadata["description"] == "This is a test NFT"
    assert metadata["block_number"] == 12345
    assert metadata["owner"] == account.address

    # Verify tokens_of_owner
    tokens = contract.tokens_of_owner(args=[account.address])
    assert len(tokens) == 1
    assert tokens[0] == 0


def test_transfer_nft():
    """Test transferring an NFT between addresses."""
    contract = load_fixture(deploy_contract)
    account1 = default_account()
    account2 = default_account(1)  # Get a different account

    # Mint an NFT to account1
    result = contract.mint(
        args=[
            account1.address,
            "Transferable NFT",
            "This NFT will be transferred",
            54321,  # block_number
        ]
    )
    assert tx_execution_succeeded(result)

    # Verify initial ownership
    assert contract.owner_of(args=[0]) == account1.address
    assert contract.balance_of(args=[account1.address]) == 1
    assert contract.balance_of(args=[account2.address]) == 0

    # Transfer NFT from account1 to account2
    # Note: In real usage, you'd need to call this from account1's context
    result = contract.transfer(args=[account2.address, 0])
    assert tx_execution_succeeded(result)

    # Verify transfer
    assert contract.owner_of(args=[0]) == account2.address
    assert contract.balance_of(args=[account1.address]) == 0
    assert contract.balance_of(args=[account2.address]) == 1


def test_multiple_nfts():
    """Test minting multiple NFTs."""
    contract = load_fixture(deploy_contract)
    account = default_account()

    # Mint 3 NFTs
    for i in range(3):
        result = contract.mint(
            args=[
                account.address,
                f"NFT #{i}",
                f"Description for NFT {i}",
                10000 + i,  # block_number
            ]
        )
        assert tx_execution_succeeded(result)

    # Verify total supply
    assert contract.total_supply_count(args=[]) == 3
    assert contract.balance_of(args=[account.address]) == 3

    # Verify all tokens belong to the account
    tokens = contract.tokens_of_owner(args=[account.address])
    assert len(tokens) == 3
    assert set(tokens) == {0, 1, 2}

    # Verify metadata for each token
    for i in range(3):
        metadata = contract.get_metadata(args=[i])
        assert metadata["name"] == f"NFT #{i}"
        assert metadata["owner"] == account.address


def test_get_all_tokens():
    """Test retrieving all tokens."""
    contract = load_fixture(deploy_contract)
    account = default_account()

    # Mint a few NFTs
    contract.mint(
        args=[
            account.address,
            "NFT 1",
            "First NFT",
            20000,  # block_number
        ]
    )
    contract.mint(
        args=[
            account.address,
            "NFT 2",
            "Second NFT",
            20001,  # block_number
        ]
    )

    # Get all tokens
    all_tokens = contract.get_all_tokens(args=[])
    assert len(all_tokens) == 2
    assert "0" in all_tokens
    assert "1" in all_tokens
    assert all_tokens["0"]["name"] == "NFT 1"
    assert all_tokens["1"]["name"] == "NFT 2"


def test_mint_validation():
    """Test that minting validates required fields."""
    contract = load_fixture(deploy_contract)
    account = default_account()

    # Try to mint with empty name (should fail)
    result = contract.mint(
        args=[
            account.address,
            "",  # Empty name
            "Description",
            12345,  # block_number
        ]
    )
    assert tx_execution_failed(result)

    # Try to mint with empty description (should fail)
    result = contract.mint(
        args=[
            account.address,
            "Name",
            "",  # Empty description
            12345,  # block_number
        ]
    )
    assert tx_execution_failed(result)

    # Try to mint with negative block_number (should fail)
    result = contract.mint(
        args=[
            account.address,
            "Name",
            "Description",
            -1,  # Negative block_number
        ]
    )
    assert tx_execution_failed(result)


def test_transfer_validation():
    """Test that transfer validates ownership."""
    contract = load_fixture(deploy_contract)
    account1 = default_account()
    account2 = default_account(1)

    # Mint an NFT to account1
    contract.mint(
        args=[
            account1.address,
            "Test NFT",
            "Description",
            99999,  # block_number
        ]
    )

    # Try to transfer non-existent token (should fail)
    result = contract.transfer(args=[account2.address, 999])
    assert tx_execution_failed(result)

    # Note: Testing transfer from wrong owner would require calling from a different account context
    # which depends on how gltest handles account switching
