import streamlit as st
import database

# Cache the kernel data to avoid hitting the DB on every run
# ttl=600 means clear cache every 10 minutes to allow for updates
@st.cache_data(ttl=600)
def fetch_kernel(role_name):
    """
    Fetches the full Kernel DNA (Prompt, Logic Gates, Axioms) from Supabase.
    Returns a dictionary or None if not found.
    """
    supabase = database.init_supabase()
    if not supabase:
        return None

    try:
        response = supabase.table("kernels") \
            .select("*") \
            .eq("role_name", role_name) \
            .single() \
            .execute()
        
        return response.data
    except Exception as e:
        print(f"Error fetching kernel '{role_name}': {e}")
        return None

@st.cache_data(ttl=600)
def list_active_kernels():
    """
    Returns a list of active role_names for the UI Dropdown.
    """
    supabase = database.init_supabase()
    if not supabase:
        return []

    try:
        response = supabase.table("kernels") \
            .select("role_name") \
            .eq("is_active", True) \
            .execute()
            
        return [row['role_name'] for row in response.data]
    except Exception as e:
        print(f"Error listing kernels: {e}")
        return []

def log_interaction(kernel_id, user_input, output, logic_trace=None):
    """
    Logs the interaction to the 'kernel_logs' table (The Watcher).
    This is NOT cached as it is a write operation.
    """
    supabase = database.init_supabase()
    if not supabase:
        return None

    try:
        data = {
            "kernel_id": kernel_id,
            "user_input": user_input,
            "output": output,
            "logic_trace": logic_trace
        }
        res = supabase.table("kernel_logs").insert(data).execute()
        return res.data
    except Exception as e:
        print(f"Error logging interaction: {e}")
        return None
