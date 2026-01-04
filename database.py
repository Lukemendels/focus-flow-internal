import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def init_supabase():
    """Initializes the Supabase client using environment variables."""
    # Try Service Key first (Bypasses RLS - Best for Backend/Streamlit)
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    # Fallback to standard keys
    url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
    anon_key = os.environ.get("SUPABASE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")

    key = service_key if service_key else anon_key

    if not url or not key:
        print("Error: SUPABASE_URL or valid KEY not found.")
        return None

    try:
        supabase: Client = create_client(url, key)
        return supabase
    except Exception as e:
        print(f"Failed to initialize Supabase: {e}")
        return None

def get_todays_tasks(user_id):
    """
    Queries the 'tasks' table for a specific user.
    Currently returns all tasks, can be filtered by date later.
    """
    supabase = init_supabase()
    if not supabase:
        return []

    try:
        # Assuming 'tasks' table exists and has 'user_id' column
        response = supabase.table("tasks").select("*").eq("user_id", user_id).execute()
        return response.data
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        return []

def add_task(user_id, task_name, hours, status="pending", is_big_3=False):
    """
    Inserts a new row into the 'tasks' table.
    """
    supabase = init_supabase()
    if not supabase:
        return None

    try:
        data = {
            "user_id": user_id,
            "task_name": task_name,
            "hours": hours,
            "status": status,
            "is_big_3": is_big_3,
            "completed": False # Default to incomplete
        }
        response = supabase.table("tasks").insert(data).execute()
        return response.data
    except Exception as e:
        print(f"Error adding task: {e}")
        return None

def get_yesterdays_incomplete(user_id):
    """
    Returns tasks that are incorrectly incomplete from previous days.
    """
    supabase = init_supabase()
    if not supabase:
        return []

    try:
        # 'date' column defaults to current_date. We want tasks where date < Today.
        # Supabase filtering uses 'lt' for Less Than.
        # Note: We rely on Supabase/Postgres current_date logic or python date.
        # For simplicity, let's use Python to get today's date string.
        from datetime import date
        today_str = date.today().isoformat()
        
        response = supabase.table("tasks").select("*") \
            .eq("user_id", user_id) \
            .eq("completed", False) \
            .lt("date", today_str) \
            .execute()
            
        return response.data
    except Exception as e:
        print(f"Error fetching incomplete tasks: {e}")
        return []

def mark_task_complete(task_id):
    """
    Updates the completed status of a task to True.
    """
    supabase = init_supabase()
    if not supabase:
        return None

    try:
        return response.data
    except Exception as e:
        print(f"Error marking task complete: {e}")
        return None

        return res.data
    except Exception as e:
        print(f"Error saving reflection: {e}")
        return None

def add_goal(user_id, description, start_date, end_date, period="weekly", context=None):
    """
    Adds a new strategic goal for a specific period (weekly/quarterly).
    """
    supabase = init_supabase()
    if not supabase: return None
    
    # Simple default status
    status = "active"
    
    try:
        data = {
            "user_id": user_id,
            "description": description,
            "start_date": start_date,
            "end_date": end_date,
            "period": period,
            "status": status,
            "context": context
        }
        res = supabase.table("goals").insert(data).execute()
        return res.data
    except Exception as e:
        print(f"Error adding goal: {e}")
        return None

def save_quarterly_goal(user_id, description, start_date, end_date, context):
    """
    Wrapper for answering the War Room planning.
    """
    return add_goal(user_id, description, start_date, end_date, period="quarterly", context=context)

def get_active_quarterly_goal(user_id):
    """
    Fetches the active QUARTERLY goal.
    """
    supabase = init_supabase()
    if not supabase: return None
    
    try:
        from datetime import date
        today_str = date.today().isoformat()
        
        # Logic: period='quarterly', active today
        res = supabase.table("goals").select("*") \
            .eq("user_id", user_id) \
            .eq("period", "quarterly") \
            .lte("start_date", today_str) \
            .gte("end_date", today_str) \
            .limit(1) \
            .execute()
            
        if res.data:
            return res.data[0]
        return None
    except Exception as e:
        print(f"Error fetching active quarterly goal: {e}")
        return None

def get_active_weekly_goal(user_id):
    """
    Fetches the goal that is active for today.
    """
    supabase = init_supabase()
    if not supabase: return None
    
    try:
        from datetime import date
        today_str = date.today().isoformat()
        
        # Logic: start_date <= today <= end_date
        # Supabase filter: lte(start_date, today) AND gte(end_date, today)
        res = supabase.table("goals").select("*") \
            .eq("user_id", user_id) \
            .lte("start_date", today_str) \
            .gte("end_date", today_str) \
            .limit(1) \
            .execute()
            
        if res.data:
            return res.data[0]
        return None
    except Exception as e:
        print(f"Error fetching active goal: {e}")
        return None

def save_marketing_asset(user_id, asset_type, topic, listing, content):
    """
    Saves a generated marketing asset.
    """
    supabase = init_supabase()
    if not supabase: return None
    
    try:
        data = {
            "user_id": user_id,
            "asset_type": asset_type,
            "topic": topic,
            "listing_details": listing,
            "content": content
        }
        res = supabase.table("marketing_assets").insert(data).execute()
        return res.data
    except Exception as e:
        print(f"Error saving marketing asset: {e}")
        return None

def get_marketing_assets(user_id):
    """
    Fetches the 20 most recent marketing assets.
    """
    supabase = init_supabase()
    if not supabase: return []
    
    try:
        res = supabase.table("marketing_assets").select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(20) \
            .execute()
        return res.data
    except Exception as e:
        print(f"Error fetching marketing assets: {e}")
        return []

def get_completed_tasks_last_week(user_id):
    """
    Fetches tasks completed in the last 7 days.
    """
    supabase = init_supabase()
    if not supabase: return []
    
    try:
        from datetime import date, timedelta
        today = date.today()
        seven_days_ago = (today - timedelta(days=7)).isoformat()
        
        # Logic: completed = true AND date > 7 days ago
        res = supabase.table("tasks").select("*") \
            .eq("user_id", user_id) \
            .eq("completed", True) \
            .gte("date", seven_days_ago) \
            .execute()
        return res.data
    except Exception as e:
        print(f"Error fetching completed tasks: {e}")
        return []

def save_reflection(user_id, week_start_date, wins, misses, lessons):
    """
    Saves the user's weekly reflection.
    """
    supabase = init_supabase()
    if not supabase: return None
    
    try:
        data = {
            "user_id": user_id,
            "week_start_date": week_start_date,
            "wins": wins,
            "misses": misses,
            "lessons_learned": lessons
        }
        res = supabase.table("reflections").insert(data).execute()
        return res.data
    except Exception as e:
        print(f"Error saving reflection: {e}")
        return None

def save_weekly_goal(user_id, description, start_date, end_date):
    """
    Wrapper to save a goal with period='weekly' and status='active'.
    """
    supabase = init_supabase()
    if not supabase: return None
    
    try:
        data = {
            "user_id": user_id,
            "description": description,
            "start_date": start_date,
            "end_date": end_date,
            "period": "weekly",
            "status": "active"
        }
        # Note: This might duplicate if we just insert. 
        # In a real app we might update existing active goals to 'archived'.
        # For this MVP, we just insert.
        res = supabase.table("goals").insert(data).execute()
        return res.data
    except Exception as e:
        print(f"Error adding weekly goal: {e}")
        return None

if __name__ == "__main__":
    print("--- Testing Supabase Connection ---")
    
    # Simple connection test
    client = init_supabase()
    if client:
        print("Supabase client initialized.")
        # user_id = "test_user"
        # print("Incomplete from yesterday:", get_yesterdays_incomplete(user_id))
    else:
        print("Supabase initialization failed (expected if keys are missing).")
