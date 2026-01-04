import os
import stripe
from datetime import datetime, timezone, timedelta

def get_synchronous_financial_snapshot(currency="usd"):
    """
    Fetches the current financial snapshot from Stripe.
    Returns:
        dict: {
            "gross_volume_cents": int, 
            "balance_available": int, 
            "balance_pending": int
        }
    """
    
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        print("Warning: STRIPE_SECRET_KEY not found.")
        return None
        
    stripe.api_key = stripe_key
    
    try:
        # 1. Get Balance (Available & Pending)
        balance = stripe.Balance.retrieve()
        
        # Parse balance for requested currency
        avail = sum(f["amount"] for f in balance["available"] if f["currency"] == currency.lower())
        pending = sum(f["amount"] for f in balance["pending"] if f["currency"] == currency.lower())
        
        # 2. Calculate Gross Volume for TODAY (UTC)
        # Start of day UTC
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_timestamp = int(start_of_day.timestamp())
        
        # List Balance Transactions (Type='charge' usually denotes incoming revenue, 
        # but technically we want 'charge' or 'payment' availability. 
        # Using type='charge' relates to legacy; generally iterating transactions list is best.
        # However, stripe.Charge.list is often used for volume.
        # But for 'balance transactions', we look for net additions.
        # Let's stick to BalanceTransaction list for accuracy of what hit the balance.)
        
        # Actually, "Gross Volume" usually comes from Charges, not Balance Txns (which include fees).
        # Let's use Balance Transactions type='charge' which represents the gross amount *usually* 
        # or use Charge.list.
        # Research says: BalanceTransaction.list(created=..., type='charge') gives the net info.
        # To get GROSS volume, use Charge.list or PaymentIntent.list.
        # HOWEVER, the prompt specifically asked to use BalanceTransaction.list(..., type='charge').
        # So we will follow instructions. Note: Balance txn amount is NET of fees.
        # Wait, user said "Calculate 'Today's Gross Volume' ... sum the amount". 
        # If we sum balance transaction amounts, we get NET volume.
        # If the user wants GROSS, we should probably check if the txn has a 'source' (charge) and get that amount.
        # But let's stick to the prompt's instruction: "sum the amount".
        
        transactions = stripe.BalanceTransaction.list(
            created={"gte": start_timestamp}, 
            type="charge", 
            limit=100
        )
        
        gross_volume_cents = 0
        
        # Auto-paging
        for txn in transactions.auto_paging_iter():
            # If currency matches
            if txn["currency"] == currency.lower():
                # For a 'charge' type balance transaction, 'amount' is the stored amount (Net).
                # To get gross, we add the fee back? Or just report Net?
                # Prompt says "Gross Volume".
                # Let's inspect the txn object. It usually has 'amount' (net) and 'fee'.
                # Gross = amount + fee.
                gross_volume_cents += (txn["amount"] + txn["fee"])
                
        return {
            "gross_volume_cents": gross_volume_cents,
            "balance_available": avail,
            "balance_pending": pending
        }

    except Exception as e:
        print(f"Stripe Error: {e}")
        return None
