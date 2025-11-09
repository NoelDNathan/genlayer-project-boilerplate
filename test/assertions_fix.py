"""
Fix for tx_execution_succeeded to handle leader_receipt as both list and dict.
"""

from typing import Any


def tx_execution_succeeded(result: Any) -> bool:
    """
    Check if transaction execution succeeded, handling both list and dict formats for leader_receipt.
    """
    if "consensus_data" not in result:
        return False

    consensus_data = result["consensus_data"]
    if "leader_receipt" not in consensus_data:
        return False

    leader_receipt = consensus_data["leader_receipt"]

    # Handle case where leader_receipt is a list
    if isinstance(leader_receipt, list):
        if len(leader_receipt) == 0:
            return False
        # Get the first element (leader's receipt)
        leader_receipt = leader_receipt[0]

    # Handle case where leader_receipt is a dict
    if not isinstance(leader_receipt, dict):
        return False

    if "execution_result" not in leader_receipt:
        return False

    execution_result = leader_receipt["execution_result"]
    return execution_result == "SUCCESS"


def tx_execution_failed(result: Any) -> bool:
    """
    Check if transaction execution failed.
    """
    return not tx_execution_succeeded(result)
