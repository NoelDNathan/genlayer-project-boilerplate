# v0.1.0
# { "Depends": "py-genlayer:latest" }

import json
import typing
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class InsurancePolicy:
    id: str
    player_address: Address
    tournament_address: Address
    tournament_buy_in: u256
    premium_paid: u256
    has_claimed: bool
    claim_resolved: bool
    is_valid_cooler: bool
    payout_amount: u256
    registration_date: str


class PokerCoolerInsurance(gl.Contract):
    """
    Insurance contract for poker coolers.
    Connects to multiple poker tournament contracts to check if eliminations were coolers.
    Each policy is associated with a specific tournament contract address.
    """

    player_policies: TreeMap[
        str, InsurancePolicy
    ]  # Map of policy_id -> InsurancePolicy
    total_premiums: u256  # Total premiums collected
    total_payouts: u256  # Total payouts made
    insurance_premium_rate: u256  # Premium rate (e.g., 100 = 1%, 1000 = 10%)
    payout_rate: u256  # Payout rate (e.g., 5000 = 50% of buy-in)

    def __init__(self):
        """
        Initialize the insurance contract.
        """
        self.total_premiums = u256(0)
        self.total_payouts = u256(0)
        # Default: 5% premium rate (500 = 5%)
        self.insurance_premium_rate = u256(500)
        # Default: 50% of buy-in payout (5000 = 50%)
        self.payout_rate = u256(5000)

    def _check_cooler(
        self,
        player_hand: str,
        opponent_hand: str,
        board_cards: str = "",
    ) -> dict:
        """
        Check if a poker hand situation is a cooler.

        Args:
            player_hand: The player's hand in card notation
            opponent_hand: The opponent's hand in card notation
            board_cards: Optional board cards if applicable

        Returns:
            dict with is_cooler (bool), player_hand_rank (str), opponent_hand_rank (str), and explanation (str)
        """

        def verify_cooler() -> str:
            task = f"""
Determine if this poker hand situation is a "cooler".

Card notation uses suit symbols: ♠ (spades), ♥ (hearts), ♦ (diamonds), ♣ (clubs)
Examples: ♠A♠A (pocket Aces of spades), ♥K♥K (pocket Kings of hearts), ♠A♠K (Ace-King suited)

Player hand: {player_hand}
Opponent hand: {opponent_hand}
Board cards: {board_cards if board_cards else "None"}

A "cooler" is defined as a situation where:
1. The player has a very strong hand (e.g., ♠A♠A, ♥K♥K, top pair with top kicker, flush, straight)
2. The opponent has an even stronger hand (e.g., ♠A♠A vs ♥K♥K, flush vs higher flush, straight vs higher straight)
3. The player loses despite having a strong hand that would normally win

Respond in JSON:
{{
    "is_cooler": bool, // true if this is a cooler situation
    "player_hand_rank": str, // e.g., "Pocket Aces", "Flush", "Straight", "Top Pair"
    "opponent_hand_rank": str, // e.g., "Pocket Aces", "Flush", "Straight", "Top Pair"
    "explanation": str // brief explanation of why it is or isn't a cooler
}}
It is mandatory that you respond only using the JSON format above,
nothing else. Don't include any other words or characters,
your output must be only JSON without any formatting prefix or suffix.
This result should be perfectly parsable by a JSON parser without errors.
            """
            result = gl.nondet.exec_prompt(task, response_format="json")
            return json.dumps(result, sort_keys=True)

        result_json = json.loads(gl.eq_principle.strict_eq(verify_cooler))
        return result_json

    @gl.public.write
    def purchase_insurance(
        self,
        tournament_address: str,
        registration_date: str,
        player_address: str,
    ) -> typing.Any:
        """
        Purchase insurance for a tournament.

        Args:
            tournament_address: Address of the poker tournament contract
            registration_date: Date of registration
            player_address: Address of the player
        Returns:
            dict with policy information
        """
        if not tournament_address:
            raise Exception("tournament_address is required")

        tournament_addr = Address(tournament_address)

        # Convert player_address string to Address object
        player_addr = Address(player_address)

        # Get player address from message sender
        # Disable for testing purposes
        # player_address = gl.message.sender_address

        # Generate policy ID based on tournament address, player address, and registration date
        policy_id = f"{tournament_addr.as_hex}_{player_addr.as_hex}_{registration_date}"

        # Check if policy already exists
        if policy_id in self.player_policies:
            raise Exception(f"Insurance policy {policy_id} already exists")

        # Get tournament info to calculate premium using contract-to-contract interaction
        tournament_info = self._get_tournament_info(tournament_address)
        buy_in = tournament_info.get("tournament_buy_in", 0)

        if buy_in <= 0:
            raise Exception("Invalid tournament buy-in amount")

        # Calculate premium (premium_rate is in basis points, e.g., 500 = 5%)
        premium = (buy_in * int(self.insurance_premium_rate)) // 10000

        # Create insurance policy
        policy = InsurancePolicy(
            id=policy_id,
            player_address=player_addr,  # Use Address object, not string
            tournament_address=tournament_addr,
            tournament_buy_in=u256(buy_in),
            premium_paid=u256(premium),
            has_claimed=False,
            claim_resolved=False,
            is_valid_cooler=False,
            payout_amount=u256(0),
            registration_date=registration_date,
        )

        self.player_policies[policy_id] = policy
        self.total_premiums += u256(premium)

        return {
            "policy_id": policy_id,
            "premium_paid": premium,
            "tournament_buy_in": buy_in,
        }

    def _get_tournament_info(self, tournament_address: str) -> dict:
        """
        Get tournament information from the tournament contract using contract-to-contract interaction.
        This queries the tournament contract to get the buy-in amount from player balances.

        Args:
            tournament_address: Address of the poker tournament contract

        Returns:
            dict with tournament information
        """
        tournament_addr = Address(tournament_address)

        # Query tournament contract to get state and calculate buy-in from player balances
        # We'll use the tournament contract's get_state method to get player balances
        try:
            tournament_contract = gl.get_contract_at(tournament_addr)
            tournament_state = tournament_contract.view().get_state()

            # Calculate buy-in as the sum of all player balances divided by number of players
            # This gives us an estimate of the buy-in amount
            player_balances = tournament_state.get("player_balances", [])

            if len(player_balances) > 0:
                total_balance = sum(player_balances)
                # Estimate buy-in as average balance (assuming all players started with same buy-in)
                buy_in = (
                    total_balance // len(player_balances)
                    if total_balance > 0
                    else 10000
                )
            else:
                # Default buy-in if no players registered yet
                buy_in = 10000
        except Exception:
            # If contract interaction fails, use default buy-in
            buy_in = 10000

        return {
            "tournament_buy_in": buy_in,
        }

    def _process_claim(self, policy: InsurancePolicy, policy_id: str) -> typing.Any:
        """
        Internal method to process a claim for an insurance policy.
        This contains the common logic for processing claims.

        Args:
            policy: The insurance policy to process
            policy_id: ID of the insurance policy

        Returns:
            dict with claim resolution information
        """
        if policy.has_claimed:
            raise Exception(f"Claim already filed for policy {policy_id}")

        if policy.claim_resolved:
            raise Exception(f"Claim already resolved for policy {policy_id}")

        # Get player elimination data from tournament contract using contract-to-contract interaction
        # Each policy has its own tournament_address
        tournament_contract = gl.get_contract_at(policy.tournament_address)
        elimination_data = tournament_contract.view().get_player_elimination(
            policy.player_address.as_hex
        )

        # Check if player was eliminated (get_player_elimination returns empty dict if not found)
        if not elimination_data or len(elimination_data) == 0:
            # Player was not eliminated, claim is invalid
            policy.has_claimed = True
            policy.claim_resolved = True
            policy.is_valid_cooler = False
            policy.payout_amount = u256(0)
            self.player_policies[policy_id] = policy

            return {
                "policy_id": policy_id,
                "claim_resolved": True,
                "is_valid_cooler": False,
                "payout_amount": 0,
                "reason": "Player was not eliminated in the tournament",
            }

        # Extract elimination data
        player_hand = elimination_data.get("player_hand", "")
        opponent_hand = elimination_data.get("opponent_hand", "")
        board_cards = elimination_data.get("board_cards", "")

        if not player_hand or not opponent_hand:
            # Missing hand data, cannot verify cooler
            policy.has_claimed = True
            policy.claim_resolved = True
            policy.is_valid_cooler = False
            policy.payout_amount = u256(0)
            self.player_policies[policy_id] = policy

            return {
                "policy_id": policy_id,
                "claim_resolved": True,
                "is_valid_cooler": False,
                "payout_amount": 0,
                "reason": "Missing hand data in elimination record",
            }

        # Check if it's a cooler
        cooler_result = self._check_cooler(player_hand, opponent_hand, board_cards)
        is_cooler = cooler_result.get("is_cooler", False)

        # Calculate payout if it's a valid cooler
        payout_amount = u256(0)
        if is_cooler:
            # Payout is a percentage of buy-in (payout_rate is in basis points)
            payout_amount = u256(
                (int(policy.tournament_buy_in) * int(self.payout_rate)) // 10000
            )
            self.total_payouts += payout_amount

        # Update policy
        policy.has_claimed = True
        policy.claim_resolved = True
        policy.is_valid_cooler = is_cooler
        policy.payout_amount = payout_amount
        self.player_policies[policy_id] = policy

        return {
            "policy_id": policy_id,
            "claim_resolved": True,
            "is_valid_cooler": is_cooler,
            "payout_amount": int(payout_amount),
            "player_hand_rank": cooler_result.get("player_hand_rank", ""),
            "opponent_hand_rank": cooler_result.get("opponent_hand_rank", ""),
            "explanation": cooler_result.get("explanation", ""),
        }

    @gl.public.write
    def file_claim(self, policy_id: str) -> typing.Any:
        """
        File a claim for an insurance policy.
        This will check the tournament contract to see if the player was eliminated in a cooler.

        Args:
            policy_id: ID of the insurance policy to claim

        Returns:
            dict with claim resolution information
        """
        if policy_id not in self.player_policies:
            raise Exception(f"Insurance policy {policy_id} not found")

        policy = self.player_policies[policy_id]
        return self._process_claim(policy, policy_id)

    @gl.public.write
    def file_claim_by_params(
        self,
        tournament_address: str,
        player_address: str,
        registration_date: str,
    ) -> typing.Any:
        """
        File a claim for an insurance policy using tournament address, player address, and registration date.
        This will check the tournament contract to see if the player was eliminated in a cooler.

        Args:
            tournament_address: Address of the poker tournament contract
            player_address: Address of the player
            registration_date: Date of registration

        Returns:
            dict with claim resolution information
        """
        # Convert addresses to Address objects
        tournament_addr = Address(tournament_address)
        player_addr = Address(player_address)

        # Generate policy ID (same format as in purchase_insurance)
        policy_id = f"{tournament_addr.as_hex}_{player_addr.as_hex}_{registration_date}"

        if policy_id not in self.player_policies:
            raise Exception(f"Insurance policy {policy_id} not found")

        policy = self.player_policies[policy_id]
        return self._process_claim(policy, policy_id)

    @gl.public.view
    def get_policy(self, policy_id: str) -> typing.Any:
        """
        Get an insurance policy by ID.

        Args:
            policy_id: ID of the insurance policy

        Returns:
            dict with policy information
        """
        if policy_id not in self.player_policies:
            raise Exception(f"Insurance policy {policy_id} not found")

        policy = self.player_policies[policy_id]
        return {
            "id": policy.id,
            "player_address": policy.player_address.as_hex,
            "tournament_address": policy.tournament_address.as_hex,
            "tournament_buy_in": int(policy.tournament_buy_in),
            "premium_paid": int(policy.premium_paid),
            "has_claimed": policy.has_claimed,
            "claim_resolved": policy.claim_resolved,
            "is_valid_cooler": policy.is_valid_cooler,
            "payout_amount": int(policy.payout_amount),
            "registration_date": policy.registration_date,
        }

    @gl.public.view
    def get_player_policies(self, player_address: str) -> typing.Any:
        """
        Get all insurance policies for a player.

        Args:
            player_address: Address of the player

        Returns:
            dict mapping policy_id to policy information
        """
        address = Address(player_address)
        policies = {}

        for policy_id, policy in self.player_policies.items():
            if policy.player_address == address:
                policies[policy_id] = {
                    "id": policy.id,
                    "player_address": policy.player_address.as_hex,
                    "tournament_address": policy.tournament_address.as_hex,
                    "tournament_buy_in": int(policy.tournament_buy_in),
                    "premium_paid": int(policy.premium_paid),
                    "has_claimed": policy.has_claimed,
                    "claim_resolved": policy.claim_resolved,
                    "is_valid_cooler": policy.is_valid_cooler,
                    "payout_amount": int(policy.payout_amount),
                    "registration_date": policy.registration_date,
                }

        return policies

    @gl.public.view
    def get_tournament_info(self, tournament_address: str) -> typing.Any:
        """
        Get tournament information including buy-in, premium, and payout amounts.

        Args:
            tournament_address: Address of the poker tournament contract

        Returns:
            dict with tournament information
        """
        tournament_info = self._get_tournament_info(tournament_address)
        buy_in = tournament_info.get("tournament_buy_in", 0)

        # Calculate premium (premium_rate is in basis points)
        premium = (buy_in * int(self.insurance_premium_rate)) // 10000

        # Calculate payout (payout_rate is in basis points)
        payout = (buy_in * int(self.payout_rate)) // 10000

        return {
            "tournament_buy_in": buy_in,
            "insurance_premium": premium,
            "payout_amount": payout,
        }

    @gl.public.view
    def get_total_premiums(self) -> int:
        """
        Get the total premiums collected.

        Returns:
            Total premiums collected
        """
        return int(self.total_premiums)

    @gl.public.view
    def get_total_payouts(self) -> int:
        """
        Get the total payouts made.

        Returns:
            Total payouts made
        """
        return int(self.total_payouts)
