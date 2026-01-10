import database
import json
import os
import datetime
import calendar_service
from googleapiclient.discovery import build
from asteval import Interpreter

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
    # Import here to avoid circular dependency
    from agent import get_embedding 
    
    embedding = get_embedding(query)
    if not embedding:
        return "Error: Could not generate embedding for query."
        
    memories = database.recall_memories("user_current", embedding, limit=3)
    
    if not memories:
        return "No relevant memories found."
        
    return "\n".join([f"- {m['content']}" for m in memories])

def web_search(query: str) -> str:
    """
    Performs a Google Search and returns the top 3 results with snippets.
    Uses Google Custom Search JSON API.
    """
    # specific key for search if provided, otherwise generic google api key
    api_key = os.environ.get("Google Search_API_KEY") or os.environ.get("GOOGLE_SEARCH_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    cx = os.environ.get("GOOGLE_CSE_ID")
    
    if not api_key or not cx:
        return "Error: GOOGLE_API_KEY or GOOGLE_CSE_ID not set in environment."

    try:
        service = build("customsearch", "v1", developerKey=api_key)
        res = service.cse().list(q=query, cx=cx, num=3).execute()
        
        items = res.get("items", [])
        if not items:
            return "No results found."
            
        output = []
        for item in items:
            title = item.get("title", 'No Title')
            snippet = item.get("snippet", 'No Snippet')
            link = item.get("link", 'No Link')
            output.append(f"Title: {title}\nSnippet: {snippet}\nLink: {link}")
            
        return "\n\n".join(output)
    except Exception as e:
        return f"Error performing search: {e}"

def block_calendar_time(start_iso: str, duration_hours: float, title: str) -> str:
    """
    Creates a 'Busy' event on the Google Calendar.
    """
    service = calendar_service.get_calendar_service()
    if not service:
        return "Error: Could not connect to Calendar."
        
    try:
        start_dt = datetime.datetime.fromisoformat(start_iso)
        end_dt = start_dt + datetime.timedelta(hours=duration_hours)
        
        event = {
            'summary': title,
            'start': {'dateTime': start_iso}, 
            'end': {'dateTime': end_dt.isoformat()},
        }
        
        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Event created: {event.get('htmlLink')}"
    except Exception as e:
        return f"Error blocking time: {e}"

def update_calendar_event(event_id: str, new_start_iso: str = None, new_title: str = None) -> str:
    """
    Updates an existing calendar event (move or rename).
    """
    service = calendar_service.get_calendar_service()
    if not service: return "Error: Calendar service unavailable."
    
    try:
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        if new_title:
            event['summary'] = new_title
        if new_start_iso:
            start_old = datetime.datetime.fromisoformat(event['start']['dateTime'])
            end_old = datetime.datetime.fromisoformat(event['end']['dateTime'])
            duration = end_old - start_old
            
            new_start_dt = datetime.datetime.fromisoformat(new_start_iso)
            new_end_dt = new_start_dt + duration
            
            event['start']['dateTime'] = new_start_iso
            event['end']['dateTime'] = new_end_dt.isoformat()
            
        updated_event = service.events().patch(calendarId='primary', eventId=event_id, body=event).execute()
        return f"Event updated: {updated_event.get('htmlLink')}"
    except Exception as e:
        return f"Error updating event: {e}"

def delete_calendar_event(event_id: str) -> str:
    """
    Deletes a calendar event.
    """
    service = calendar_service.get_calendar_service()
    if not service: return "Error: Calendar service unavailable."
    
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return "Event deleted successfully."
    except Exception as e:
        return f"Error deleting event: {e}"

def calculate_metrics(expression: str) -> str:
    """
    Evaluates a mathematical expression safely using asteval.
    """
    aeval = Interpreter()
    try:
        result = aeval(expression)
        return str(result)
    except Exception as e:
        return f"Error calculating metrics: {e}"
