"""
Test data and expected states for PokerCoolerInsurance contract tests.
"""

poker_cooler_insurance_contract_schema = {
    "id": 1,
    "jsonrpc": "2.0",
    "result": {
        "ctor": {"kwparams": {}, "params": []},
        "methods": {
            "purchase_insurance": {
                "kwparams": {},
                "params": [
                    ["tournament_id", "string"],
                    ["tournament_url", "string"],
                    ["player_id", "string"],
                    ["registration_date", "string"],
                ],
                "readonly": False,
                "ret": "null",
            },
            "file_claim": {
                "kwparams": {},
                "params": [["policy_id", "string"]],
                "readonly": False,
                "ret": "null",
            },
            "get_tournament_info": {
                "kwparams": {},
                "params": [["tournament_url", "string"]],
                "readonly": True,
                "ret": "dict",
            },
            "get_policies": {
                "kwparams": {},
                "params": [],
                "readonly": True,
                "ret": "dict",
            },
            "get_player_policies": {
                "kwparams": {},
                "params": [["player_address", "string"]],
                "readonly": True,
                "ret": "dict",
            },
            "get_policy": {
                "kwparams": {},
                "params": [["policy_id", "string"]],
                "readonly": True,
                "ret": "InsurancePolicy",
            },
            "get_total_premiums": {
                "kwparams": {},
                "params": [],
                "readonly": True,
                "ret": "int",
            },
            "get_total_payouts": {
                "kwparams": {},
                "params": [],
                "readonly": True,
                "ret": "int",
            },
            "get_contract_balance": {
                "kwparams": {},
                "params": [],
                "readonly": True,
                "ret": "int",
            },
        },
    },
}

# Expected policy state after purchase (before claim)
test_policy_purchased = {
    "id": "tournament123_0x1234567890123456789012345678901234567890",
    "player_address": "0x1234567890123456789012345678901234567890",
    "tournament_id": "tournament123",
    "tournament_url": "http://localhost:8000/tournament_example.html",
    "player_id": "player123",
    "tournament_buy_in": 100,
    "premium_paid": 20,  # 20% of 100
    "has_claimed": False,
    "claim_resolved": False,
    "is_valid_cooler": False,
    "payout_amount": 50,  # 50% of 100
    "registration_date": "2024-01-15",
}

# Expected policy state after successful cooler claim
test_policy_claimed_cooler = {
    "id": "tournament123_0x1234567890123456789012345678901234567890",
    "player_address": "0x1234567890123456789012345678901234567890",
    "tournament_id": "tournament123",
    "tournament_url": "http://localhost:8000/tournament_example.html",
    "player_id": "player123",
    "tournament_buy_in": 100,
    "premium_paid": 20,
    "has_claimed": True,
    "claim_resolved": True,
    "is_valid_cooler": True,
    "payout_amount": 50,
    "registration_date": "2024-01-15",
}

# Expected policy state after claim without cooler
test_policy_claimed_no_cooler = {
    "id": "tournament123_0x1234567890123456789012345678901234567890",
    "player_address": "0x1234567890123456789012345678901234567890",
    "tournament_id": "tournament123",
    "tournament_url": "http://localhost:8000/tournament_example.html",
    "player_id": "player456",
    "tournament_buy_in": 100,
    "premium_paid": 20,
    "has_claimed": True,
    "claim_resolved": True,
    "is_valid_cooler": False,
    "payout_amount": 50,
    "registration_date": "2024-01-15",
}

# Expected tournament info response
test_tournament_info = {
    "tournament_buy_in": 100,
    "insurance_premium": 20,  # 20% of 100
    "payout_amount": 50,  # 50% of 100
}

