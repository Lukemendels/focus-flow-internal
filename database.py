import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def init_supabase():
    """Initializes the Supabase client using environment variables."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_KEY not found in environment.")
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
        response = supabase.table("tasks").update({"completed": True}).eq("id", task_id).execute()
        return response.data
    except Exception as e:
        print(f"Error marking task complete: {e}")
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
