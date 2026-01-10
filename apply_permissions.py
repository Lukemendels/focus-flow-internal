import database
import sys

def apply_permissions():
    supabase = database.init_supabase()
    if not supabase:
        print("Failed to initialize Supabase client.")
        return

    updates = [
        {
            "role_name": "Strategic Architect",
            "tools_enabled": ["web_search", "calculate_metrics"]
        },
        {
            "role_name": "Market Alchemist",
            "tools_enabled": ["web_search"]
        },
        {
            "role_name": "Operational Commander",
            "tools_enabled": ["block_calendar_time", "update_calendar_event", "delete_calendar_event", "calculate_metrics"]
        }
    ]

    print("Applying permission updates...")
    for update in updates:
        try:
            print(f"Updating {update['role_name']}...")
            data = {"tools_enabled": update["tools_enabled"]}
            res = supabase.table("kernels").update(data).eq("role_name", update["role_name"]).execute()
            print(f"Success: {res.data}")
        except Exception as e:
            print(f"Error updating {update['role_name']}: {e}")

if __name__ == "__main__":
    apply_permissions()
