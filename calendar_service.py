from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime
import os
import json

# Scopes required
# Scopes required
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Authenticates and returns the Google Calendar Service."""
    creds = None
    if os.path.exists('gcp_key.json'):
        creds = service_account.Credentials.from_service_account_file(
            'gcp_key.json', scopes=SCOPES)
    else:
        print("Error: gcp_key.json not found.")
        return None

    return build('calendar', 'v3', credentials=creds)

def get_todays_events():
    """
    Fetches events for the current day from the primary calendar.
    Returns:
        events (list): List of event dicts {'summary', 'start', 'end', 'duration_hours'}
        total_hours (float): Total duration of today's meetings.
    """
    try:
        service = get_calendar_service()
        if not service:
            return [], 0.0

        # Time range: Start of today (00:00) to End of today (23:59)
        now = datetime.datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'  # 'Z' indicates UTC time
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat() + 'Z'
        
        # Note: 'Z' assumes UTC. Ideally we use local time with offset.
        # But for 'today' logic in simple scripts, let's use the user's local day bounds
        # sent as ISO strings. The API handles timeMin/timeMax well.
        # Better approach for local time:
        local_now = datetime.datetime.now().astimezone()
        time_min = local_now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        time_max = local_now.replace(hour=23, minute=59, second=59).isoformat()

        # Target Calendar ID (Default to primary if not set)
        target_cal_id = os.environ.get('GOOGLE_CALENDAR_ID', 'primary')
        print(f"Querying Calendar ID: {target_cal_id}")

        events_result = service.events().list(
            calendarId=target_cal_id, 
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        items = events_result.get('items', [])
        
        clean_events = []
        total_hours = 0.0
        
        for event in items:
            # Skip all-day events (they have 'date' but not 'dateTime')
            start = event.get('start')
            if 'dateTime' not in start:
                continue
                
            summary = event.get('summary', 'No Title')
            
            # Parse duration
            # ISO format: 2023-10-25T10:00:00-04:00
            start_dt = datetime.datetime.fromisoformat(start['dateTime'])
            end_dt = datetime.datetime.fromisoformat(event['end']['dateTime'])
            
            duration = (end_dt - start_dt).total_seconds() / 3600.0
            total_hours += duration
            
            clean_events.append({
                "summary": summary,
                "start": start_dt.strftime("%I:%M %p"),
                "end": end_dt.strftime("%I:%M %p"),
                "start_iso": start['dateTime'],
                "end_iso": event['end']['dateTime'],
                "duration_hours": round(duration, 2)
            })
            
        return clean_events, round(total_hours, 2)

    except Exception as e:
        print(f"Calendar API Info/Error: {e}")
        # Return empty if fails (e.g. auth error, sharing issue)
        return [], 0.0

if __name__ == "__main__":
    # Test run
    evs, hrs = get_todays_events()
    print(f"Found {len(evs)} events, totaling {hrs} hours.")
    for e in evs:
        print(f"- {e['summary']} ({e['start']} - {e['end']})")
