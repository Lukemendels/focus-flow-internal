import os
import googleapiclient.discovery
from google.oauth2 import service_account
from google.cloud.billing.budgets_v1 import BudgetServiceClient

KEY_PATH = "gcp_key.json"

def check_billing_access():
    if not os.path.exists(KEY_PATH):
        print("❌ gcp_key.json not found.")
        return

    try:
        creds = service_account.Credentials.from_service_account_file(KEY_PATH)
        
        # 1. Check Cloud Billing API (Listing Accounts) - Basic Check
        print("🔎 Checking 'Cloud Billing API'...")
        cloudbilling = googleapiclient.discovery.build('cloudbilling', 'v1', credentials=creds)
        try:
            accounts = cloudbilling.billingAccounts().list().execute()
            if 'billingAccounts' in accounts:
                print(f"   ✅ Success! Found {len(accounts['billingAccounts'])} billing accounts.")
                for acc in accounts['billingAccounts']:
                    print(f"      - {acc['displayName']} ({acc['name']})")
                    check_budgets_for_account(creds, acc['name'])
            else:
                print("   ⚠️ No Billing Accounts found. (Access OK, but list is empty).")
                print("      Ensure you have 'Billing Account Viewer' on the Account itself.")
        except Exception as e:
            if "PERMISSION_DENIED" in str(e):
                 print("   ❌ PERCENT_DENIED: Service Account cannot list billing accounts.")
                 print("      Action: Go to Billing Account > IAM > Add Member > Role: 'Billing Account Viewer'.")
            else:
                 print(f"   ❌ Error listing accounts: {e}")

    except Exception as e:
        print(f"❌ General Error: {e}")

    print(f"\n🔎 Checking 'Cloud Billing Budget API' for {parent}...")
    try:
        client = BudgetServiceClient(credentials=creds)
        # Parent format: "billingAccounts/{billing_account_id}"
        
        # List budgets
        # Note: client library expects parent string
        budgets = client.list_budgets(parent=parent)
        
        count = 0
        for b in budgets:
            count += 1
            print(f"   ✅ Found Budget: {b.display_name}")
            # Try to read amount
            try:
                # The 'calculated_spend' field is often what we want but it's not always populated in list?
                # Actually it is in the Budget object returned if we are lucky, or we need to GET specific budget.
                # The Budget object definition: https://cloud.google.com/python/docs/reference/billingbudgets/latest/google.cloud.billing.budgets_v1.types.Budget
                # calculated_spend is NOT in the Budget configuration resource. It's separate?
                # Wait, the prompt plan said "Extract calcualted_spend".
                # Double check docs: Budget resource contains "budget_filter", "amount", "threshold_rules".
                # IT DOES NOT CONTAIN ACTUAL SPEND.
                # Actual spend is usually retrieved via the Cloud Billing API 'getBillingAccount stuff' or BigQuery.
                # OR... commonly people use the budget 'alerting' to know status.
                # BUT wait.
                # Let's check if the API returns calculated spend.
                pass
            except:
                pass
        
        if count == 0:
            print("   ⚠️ Access OK, but no budgets found.")
            print("      Action: Create a Budget in GCP Console.")
            
    except Exception as e:
        if "Service is not enabled" in str(e):
            print("   ❌ API NOT ENABLED.")
            print("      Action: Enable 'Cloud Billing Budget API'.")
            print(f"      Link: https://console.cloud.google.com/apis/library/billingbudgets.googleapis.com?project=_")
        elif "Permission denied" in str(e):
            print("   ❌ PERMISSION DENIED.")
            print("      Action: Ensure 'Billing Budget Viewer' role is assigned.")
        else:
            print(f"   ❌ Error listing budgets: {e}")

if __name__ == "__main__":
    check_billing_access()
