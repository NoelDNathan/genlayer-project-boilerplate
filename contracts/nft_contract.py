# v0.1.0
# { "Depends": "py-genlayer:latest" }

import json
import typing
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class NFTMetadata:
    """Metadata structure for an NFT token."""

    name: str
    description: str
    block_number: u256
    attributes: str  # JSON string for additional attributes
    creator: Address
    mint_date: str

    # Poker-specific metadata attributes
    lucky: u256  # How lucky the winner was (0-10, 10 = royal flush level)
    skill: u256  # Player skill level (0-10, based on hand reading, strategic decisions)
    value_extraction: u256  # How well the player extracted value from strong hand (0-10, slow play/trapping)
    hand_strength: u256  # Objective hand strength (0-10)
    bluff_success: bool  # Whether the player won with a successful bluff
    pot_size: u256  # Size of the pot won
    opponents_count: u256  # Number of opponents in the hand


class NFTContract(gl.Contract):
    """
    A simple NFT (Non-Fungible Token) contract implementation for GenLayer.

    Features:
    - Mint new NFTs with metadata
    - Transfer NFTs between addresses
    - Query token ownership and metadata
    - Track total supply and balances per address
    """

    # Mapping from token ID to owner address
    token_owners: TreeMap[u256, Address]

    # Mapping from token ID to metadata
    token_metadata: TreeMap[u256, NFTMetadata]

    # Mapping from address to number of tokens owned (for quick balance queries)
    balances: TreeMap[Address, u256]

    # Total number of tokens minted (also serves as next token ID)
    total_supply: u256

    # Contract owner (can be used for access control)
    owner: Address

    def __init__(self):
        """Initialize the NFT contract."""
        self.total_supply = u256(0)
        self.owner = gl.message.sender_address

    @gl.public.write
    def mint(
        self,
        to_address: str,
        name: str,
        description: str,
        block_number: int,
        lucky: int,
        skill: int,
        value_extraction: int,
        hand_strength: int = 0,
        bluff_success: bool = False,
        pot_size: int = 0,
        opponents_count: int = 0,
        attributes: str = "{}",
    ) -> dict:
        """
        Mint a new NFT token.

        Args:
            to_address: Address that will receive the NFT
            name: Name of the NFT
            description: Description of the NFT
            block_number: Block number associated with this NFT
            lucky: Luck score (0-10, 10 = royal flush level)
            skill: Skill score (0-10, based on hand reading and strategy)
            value_extraction: Value extraction score (0-10, slow play/trapping success)
            hand_strength: Objective hand strength (0-10, optional)
            bluff_success: Whether won with a successful bluff (optional)
            pot_size: Size of the pot won (optional)
            opponents_count: Number of opponents in the hand (optional)
            attributes: JSON string for additional attributes (optional)

        Returns:
            Dictionary with token_id and owner information
        """
        if not name or not description:
            raise Exception("Name and description are required")

        if block_number < 0:
            raise Exception("Block number must be non-negative")

        # Validate scores are in range 0-10
        if lucky < 0 or lucky > 10:
            raise Exception("Lucky score must be between 0 and 10")

        if skill < 0 or skill > 10:
            raise Exception("Skill score must be between 0 and 10")

        if value_extraction < 0 or value_extraction > 10:
            raise Exception("Value extraction score must be between 0 and 10")

        if hand_strength < 0 or hand_strength > 10:
            raise Exception("Hand strength must be between 0 and 10")

        if pot_size < 0:
            raise Exception("Pot size must be non-negative")

        if opponents_count < 0:
            raise Exception("Opponents count must be non-negative")

        recipient = Address(to_address)
        token_id = self.total_supply

        # Create metadata
        metadata = NFTMetadata(
            name=name,
            description=description,
            block_number=u256(block_number),
            attributes=attributes,
            creator=gl.message.sender_address,
            mint_date=str(gl.block.timestamp),
            lucky=u256(lucky),
            skill=u256(skill),
            value_extraction=u256(value_extraction),
            hand_strength=u256(hand_strength),
            bluff_success=bluff_success,
            pot_size=u256(pot_size),
            opponents_count=u256(opponents_count),
        )

        # Assign ownership
        self.token_owners[token_id] = recipient
        self.token_metadata[token_id] = metadata

        # Update balances
        current_balance = self.balances.get(recipient, u256(0))
        self.balances[recipient] = current_balance + u256(1)

        # Increment total supply
        self.total_supply = self.total_supply + u256(1)

        return {
            "token_id": int(token_id),
            "owner": recipient.as_hex,
            "name": name,
        }

    @gl.public.write
    def transfer(self, to_address: str, token_id: int) -> None:
        """
        Transfer an NFT from the sender to another address.

        Args:
            to_address: Address that will receive the NFT
            token_id: ID of the token to transfer
        """
        token_id_u256 = u256(token_id)
        sender = gl.message.sender_address
        recipient = Address(to_address)

        # Check if token exists
        if token_id_u256 not in self.token_owners:
            raise Exception(f"Token {token_id} does not exist")

        # Check if sender owns the token
        current_owner = self.token_owners[token_id_u256]
        if current_owner != sender:
            raise Exception(f"Sender does not own token {token_id}")

        # Transfer ownership
        self.token_owners[token_id_u256] = recipient

        # Update balances
        sender_balance = self.balances.get(sender, u256(0))
        if sender_balance > 0:
            self.balances[sender] = sender_balance - u256(1)

        recipient_balance = self.balances.get(recipient, u256(0))
        self.balances[recipient] = recipient_balance + u256(1)

    @gl.public.view
    def owner_of(self, token_id: int) -> str:
        """
        Get the owner address of a specific token.

        Args:
            token_id: ID of the token

        Returns:
            Owner address as hex string
        """
        token_id_u256 = u256(token_id)
        if token_id_u256 not in self.token_owners:
            raise Exception(f"Token {token_id} does not exist")
        return self.token_owners[token_id_u256].as_hex

    @gl.public.view
    def get_metadata(self, token_id: int) -> dict:
        """
        Get the metadata of a specific token.

        Args:
            token_id: ID of the token

        Returns:
            Dictionary with token metadata
        """
        token_id_u256 = u256(token_id)
        if token_id_u256 not in self.token_metadata:
            raise Exception(f"Token {token_id} does not exist")

        metadata = self.token_metadata[token_id_u256]
        return {
            "token_id": token_id,
            "name": metadata.name,
            "description": metadata.description,
            "block_number": int(metadata.block_number),
            "attributes": metadata.attributes,
            "creator": metadata.creator.as_hex,
            "mint_date": metadata.mint_date,
            "owner": self.token_owners[token_id_u256].as_hex,
            "lucky": int(metadata.lucky),
            "skill": int(metadata.skill),
            "value_extraction": int(metadata.value_extraction),
            "hand_strength": int(metadata.hand_strength),
            "bluff_success": metadata.bluff_success,
            "pot_size": int(metadata.pot_size),
            "opponents_count": int(metadata.opponents_count),
        }

    @gl.public.view
    def balance_of(self, address: str) -> int:
        """
        Get the number of NFTs owned by an address.

        Args:
            address: Address to query

        Returns:
            Number of tokens owned
        """
        addr = Address(address)
        return int(self.balances.get(addr, u256(0)))

    @gl.public.view
    def total_supply_count(self) -> int:
        """
        Get the total number of NFTs minted.

        Returns:
            Total supply count
        """
        return int(self.total_supply)

    @gl.public.view
    def tokens_of_owner(self, address: str) -> list[int]:
        """
        Get all token IDs owned by an address.

        Args:
            address: Address to query

        Returns:
            List of token IDs owned by the address
        """
        owner = Address(address)
        token_ids = []

        for token_id, token_owner in self.token_owners.items():
            if token_owner == owner:
                token_ids.append(int(token_id))

        return token_ids

    @gl.public.view
    def get_all_tokens(self) -> dict:
        """
        Get information about all minted tokens.

        Returns:
            Dictionary mapping token IDs to their metadata
        """
        result = {}
        for token_id in range(int(self.total_supply)):
            token_id_u256 = u256(token_id)
            if token_id_u256 in self.token_metadata:
                metadata = self.token_metadata[token_id_u256]
                result[str(token_id)] = {
                    "token_id": token_id,
                    "name": metadata.name,
                    "description": metadata.description,
                    "block_number": int(metadata.block_number),
                    "owner": self.token_owners[token_id_u256].as_hex,
                    "creator": metadata.creator.as_hex,
                    "lucky": int(metadata.lucky),
                    "skill": int(metadata.skill),
                    "value_extraction": int(metadata.value_extraction),
                    "hand_strength": int(metadata.hand_strength),
                    "bluff_success": metadata.bluff_success,
                    "pot_size": int(metadata.pot_size),
                    "opponents_count": int(metadata.opponents_count),
                }
        return result
