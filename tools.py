import database
import json

def read_recent_logs(limit: int = 10) -> str:
    """
    Queries the 'kernel_logs' table to return the most recent interactions.
    Used by 'The Watcher' to audit system performance.
    
    Args:
        limit (int): Number of logs to retrieve. Defaults to 10.
        
    Returns:
        str: Formatted string of logs.
    """
    supabase = database.init_supabase()
    if not supabase:
        return "Error: Database connection failed."

    try:
        # Fetch logs, ordered by newest first
        response = supabase.table("kernel_logs") \
            .select("kernel_id, user_input, output, created_at") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
            
        logs = response.data
        if not logs:
            return "No recent logs found."
            
        formatted_output = "Most Recent Kernel Logs:\n"
        for i, log in enumerate(logs):
            formatted_output += f"--- LOG {i+1} ({log['created_at']}) ---\n"
            formatted_output += f"Kernel ID: {log.get('kernel_id', 'Unknown')}\n"
            formatted_output += f"Input: {log.get('user_input', '')[:100]}...\n" # Truncate for brevity
            formatted_output += f"Output: {log.get('output', '')[:100]}...\n"
            formatted_output += "\n"
            
        return formatted_output

    except Exception as e:
        return f"Error reading logs: {e}"

def search_knowledge_base(query: str) -> str:
    """
    Searches the vector memory (RAG) for relevant past information.
    
    Args:
        query (str): The search topic or question.
        
    Returns:
        str: Relevant memory context.
    """
    import agent # Import here to avoid circular dependency if agent imports tools? 
    # Actually agent imports kernel_manager which imports tools. agent -> kernel_manager -> tools. 
    # So tools should not import agent.
    # But we need embedding function. get_embedding is in agent.py.
    # Recommendation: Move get_embedding to database.py or a utils.py to avoid circular.
    # For now, let's duplicate the embedding logic or use a lightweight version here if possible.
    # Or, refactor agent.py later.
    # Let's import from agent inside function (runtime import) to avoid module-level circular.
    from agent import get_embedding 
    
    embedding = get_embedding(query)
    if not embedding:
        return "Error: Could not generate embedding for query."
        
    memories = database.recall_memories("user_current", embedding, limit=3)
    
    if not memories:
        return "No relevant memories found."
        
    return "\n".join([f"- {m['content']}" for m in memories])
