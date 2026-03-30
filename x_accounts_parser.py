"""
Easy X Accounts Configuration
Dễ dàng nhập X accounts mà không cần JSON format
"""
import json
import os
from typing import List


def parse_x_accounts_simple(accounts_str: str) -> List[str]:
    """
    Parse X accounts từ nhiều format:
    
    Examples:
    1. "elonmusk sama karpathy"          → ["elonmusk", "sama", "karpathy"]
    2. "@elonmusk @sama @karpathy"       → ["elonmusk", "sama", "karpathy"]
    3. "elonmusk,sama,karpathy"          → ["elonmusk", "sama", "karpathy"]
    4. '["elonmusk", "sama"]'            → ["elonmusk", "sama"]  (JSON)
    5. "elonmusk\nsama\nkarpathy"        → ["elonmusk", "sama", "karpathy"]
    """
    if not accounts_str or not accounts_str.strip():
        return []
    
    # Try JSON format first (backward compatibility)
    try:
        result = json.loads(accounts_str)
        if isinstance(result, list):
            return [acc.lstrip("@").strip() for acc in result if acc]
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Try comma-separated
    if "," in accounts_str:
        accounts = [acc.strip().lstrip("@") for acc in accounts_str.split(",")]
        return [acc for acc in accounts if acc]
    
    # Try newline-separated (multi-line)
    if "\n" in accounts_str:
        accounts = [acc.strip().lstrip("@") for acc in accounts_str.split("\n")]
        return [acc for acc in accounts if acc]
    
    # Try space-separated
    accounts = [acc.strip().lstrip("@") for acc in accounts_str.split()]
    return [acc for acc in accounts if acc]


def get_x_accounts() -> List[str]:
    """
    Get X accounts từ environment variable
    Hỗ trợ nhiều format
    """
    accounts_str = os.getenv("X_ACCOUNTS", "")
    
    if not accounts_str:
        print("⚠️  X_ACCOUNTS not set in .env")
        print("Examples:")
        print('  X_ACCOUNTS="elonmusk sama karpathy"')
        print('  X_ACCOUNTS="@elonmusk, @sama, @karpathy"')
        print('  X_ACCOUNTS="elonmusk\\nsama\\nkarpathy"')
        return []
    
    accounts = parse_x_accounts_simple(accounts_str)
    
    if accounts:
        print(f"✓ Loaded {len(accounts)} accounts: {', '.join(accounts)}")
    else:
        print("⚠️  No valid accounts found in X_ACCOUNTS")
    
    return accounts


def validate_account_name(account: str) -> bool:
    """Check if account name is valid"""
    if not account:
        return False
    # Remove @ if present
    name = account.lstrip("@")
    # Valid Twitter usernames: 1-15 chars, alphanumeric + underscore
    if len(name) > 15 or len(name) < 1:
        return False
    if not all(c.isalnum() or c == "_" for c in name):
        return False
    return True


# Test function
if __name__ == "__main__":
    # Test different formats
    test_cases = [
        'elonmusk sama karpathy',
        '@elonmusk @sama @karpathy',
        'elonmusk,sama,karpathy',
        '["elonmusk", "sama", "karpathy"]',
        'elonmusk\nsama\nkarpathy',
        'elonmusk',
        '@twitter',
    ]
    
    print("Testing X accounts parser:\n")
    for test in test_cases:
        result = parse_x_accounts_simple(test)
        print(f"Input:  {repr(test)}")
        print(f"Output: {result}\n")
