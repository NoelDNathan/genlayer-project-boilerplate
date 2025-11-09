# v0.1.0
# { "Depends": "py-genlayer:latest" }

import json
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class InsurancePolicy:
    id: str
    player_address: Address
    tournament_id: str
    tournament_url: str
    player_id: str
    tournament_buy_in: u256
    premium_paid: u256
    has_claimed: bool
    claim_resolved: bool
    is_valid_cooler: bool
    payout_amount: u256
    registration_date: str


class PokerCoolerInsurance(gl.Contract):
    policies: TreeMap[Address, TreeMap[str, InsurancePolicy]]
    total_premiums: u256
    total_payouts: u256

    def __init__(self):
        self.total_premiums = 0
        self.total_payouts = 0

    def _policy_to_dict(self, policy: InsurancePolicy) -> dict:
        """Convert InsurancePolicy dataclass to dictionary with u256 values as int."""
        return {
            "id": policy.id,
            "player_address": policy.player_address.as_hex,
            "tournament_id": policy.tournament_id,
            "tournament_url": policy.tournament_url,
            "player_id": policy.player_id,
            "tournament_buy_in": int(policy.tournament_buy_in),
            "premium_paid": int(policy.premium_paid),
            "has_claimed": policy.has_claimed,
            "claim_resolved": policy.claim_resolved,
            "is_valid_cooler": policy.is_valid_cooler,
            "payout_amount": int(policy.payout_amount),
            "registration_date": policy.registration_date,
        }

    def _get_tournament_buy_in(self, tournament_url: str) -> int:
        def extract_buy_in() -> str:
            web_data = gl.nondet.web.render(tournament_url, mode="text")

            task = f"""
Extract the tournament buy-in cost from the following tournament page.

Web content:
{web_data}

Respond in JSON:
{{
    "buy_in": str, // the tournament buy-in cost as a number (e.g., "100", "500", "1000")
}}
It is mandatory that you respond only using the JSON format above,
nothing else. Don't include any other words or characters,
your output must be only JSON without any formatting prefix or suffix.
This result should be perfectly parsable by a JSON parser without errors.
            """
            result = gl.nondet.exec_prompt(task, response_format="json")
            return json.dumps(result, sort_keys=True)

        result_json = json.loads(gl.eq_principle.strict_eq(extract_buy_in))
        buy_in_str = result_json.get("buy_in", "0")
        try:
            buy_in_clean = "".join(filter(str.isdigit, buy_in_str))
            return u256(int(buy_in_clean) if buy_in_clean else 0)
        except (ValueError, TypeError):
            raise Exception("Could not extract valid tournament buy-in from URL")

    def _verify_cooler(
        self,
        tournament_url: str,
        player_id: str,
    ) -> dict:
        def verify_tournament_cooler() -> str:
            web_data = gl.nondet.web.render(tournament_url, mode="text")

            task = f"""
Verify if the player was eliminated from the tournament due to a poker cooler.

Player ID: {player_id}

Card notation uses suit symbols: ♠ (spades), ♥ (hearts), ♦ (diamonds), ♣ (clubs)
Examples: ♠A♠A (pocket Aces of spades), ♥K♥K (pocket Kings of hearts), ♠A♠K (Ace-King suited)

A "cooler" elimination is defined as a situation where:
1. The player was eliminated from the tournament
2. The elimination hand was a cooler: the player had a very strong hand (e.g., ♠A♠A, ♥K♥K, top pair with top kicker)
3. The opponent had an even stronger hand (e.g., ♠A♠A vs ♥K♥K, flush vs straight)
4. The player lost the hand and was eliminated despite having a strong hand

Web content:
{web_data}

Respond in JSON:
{{
    "is_cooler": bool, // true if the player was eliminated by a cooler
    "was_eliminated": bool, // true if the player was eliminated from the tournament
    "player_hand": str, // the actual hand the player had when eliminated (use card symbols: ♠A♠A, ♥K♥Q, etc.)
    "opponent_hand": str, // the actual hand the opponent had (use card symbols: ♠A♠A, ♥K♥Q, etc.)
    "hand_rank_player": str, // e.g., "Pocket Aces", "Flush", "Straight"
    "hand_rank_opponent": str, // e.g., "Pocket Aces", "Flush", "Straight"
    "tournament_finished": bool // true if the tournament has been completed
}}
It is mandatory that you respond only using the JSON format above,
nothing else. Don't include any other words or characters,
your output must be only JSON without any formatting prefix or suffix.
This result should be perfectly parsable by a JSON parser without errors.
            """
            result = gl.nondet.exec_prompt(task, response_format="json")
            return json.dumps(result, sort_keys=True)

        result_json = json.loads(gl.eq_principle.strict_eq(verify_tournament_cooler))
        return result_json

    @gl.public.write
    def purchase_insurance(
        self,
        tournament_id: str,
        tournament_url: str,
        player_id: str,
        registration_date: str,
    ) -> None:
        sender_address = gl.message.sender_address
        policy_id = f"{tournament_id}_{sender_address.as_hex}".lower()

        if (
            sender_address in self.policies
            and policy_id in self.policies[sender_address]
        ):
            raise Exception("Insurance policy already exists for this tournament")

        # Extract tournament buy-in from URL
        tournament_buy_in = self._get_tournament_buy_in(tournament_url)

        if tournament_buy_in <= 0:
            raise Exception("Could not extract valid tournament buy-in from URL")

        # Calculate premium as 20% of tournament buy-in
        premium = tournament_buy_in * 20 // 100

        # Calculate payout as 50% of tournament buy-in
        payout_amount = tournament_buy_in // 2

        policy = InsurancePolicy(
            id=policy_id,
            player_address=sender_address,
            tournament_id=tournament_id,
            tournament_url=tournament_url,
            player_id=player_id,
            tournament_buy_in=tournament_buy_in,
            premium_paid=premium,
            has_claimed=False,
            claim_resolved=False,
            is_valid_cooler=False,
            payout_amount=payout_amount,
            registration_date=registration_date,
        )

        self.policies.get_or_insert_default(sender_address)[policy_id] = policy
        self.total_premiums += premium

    @gl.public.write
    def file_claim(self, policy_id: str) -> None:
        sender_address = gl.message.sender_address

        if (
            sender_address not in self.policies
            or policy_id not in self.policies[sender_address]
        ):
            raise Exception("Insurance policy not found")

        policy = self.policies[sender_address][policy_id]

        if policy.has_claimed:
            raise Exception("Claim already filed for this policy")

        # Verify the cooler elimination using GenLayer
        verification_result = self._verify_cooler(
            policy.tournament_url,
            policy.player_id,
        )

        if not verification_result.get("tournament_finished", False):
            raise Exception("Tournament not finished yet")

        if not verification_result.get("was_eliminated", False):
            raise Exception("Player was not eliminated from the tournament")

        policy.has_claimed = True
        policy.is_valid_cooler = verification_result.get("is_cooler", False)

        if policy.is_valid_cooler:
            policy.claim_resolved = True
            self.total_payouts += policy.payout_amount
        else:
            policy.claim_resolved = True
            # No payout if not a valid cooler elimination

    @gl.public.view
    def get_tournament_info(self, tournament_url: str) -> dict:
        """
        Get tournament buy-in and calculated insurance premium before purchasing.
        This allows users to see the costs before registering.
        """
        tournament_buy_in = self._get_tournament_buy_in(tournament_url)
        if tournament_buy_in <= 0:
            raise Exception("Could not extract valid tournament buy-in from URL")

        # Calculate premium as 20% of tournament buy-in
        insurance_premium = tournament_buy_in * 20 // 100

        # Calculate payout as 50% of tournament buy-in
        payout_amount = tournament_buy_in // 2

        return {
            "tournament_buy_in": tournament_buy_in,
            "insurance_premium": insurance_premium,
            "payout_amount": payout_amount,
        }

    @gl.public.view
    def get_policies(self) -> dict:
        result = {}
        for address, policies_map in self.policies.items():
            result[address.as_hex] = {
                k: self._policy_to_dict(v) for k, v in policies_map.items()
            }
        return result

    @gl.public.view
    def get_player_policies(self, player_address: str) -> dict:
        address = Address(player_address)
        if address not in self.policies:
            return {}
        return {k: self._policy_to_dict(v) for k, v in self.policies[address].items()}

    @gl.public.view
    def get_policy(self, policy_id: str) -> dict:
        sender_address = gl.message.sender_address
        if (
            sender_address not in self.policies
            or policy_id not in self.policies[sender_address]
        ):
            raise Exception("Insurance policy not found")
        policy = self.policies[sender_address][policy_id]
        return self._policy_to_dict(policy)

    @gl.public.view
    def get_total_premiums(self) -> int:
        return self.total_premiums

    @gl.public.view
    def get_total_payouts(self) -> int:
        return self.total_payouts

    @gl.public.view
    def get_contract_balance(self) -> int:
        return self.total_premiums - self.total_payouts
