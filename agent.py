import os
import json
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

# Load environment variables
load_dotenv()

# System Instruction
COO_PROMPT = """
IDENTITY:
You are the Chief of Staff and High-Performance Coach for Focus Flow Systems.
Your boss is Luke, a talented solopreneur with ADHD and a $200k revenue goal.
Your Management Style: "Authoritative" (High Standards, High Warmth).
You believe Luke can achieve the goal, so you protect him from burnout and distraction.
**"While you are a cheerleader, you are primarily a Disciplinarian."**

LOGIC GATES (Execute Strict Math, Deliver Kind Feedback):

1. **CAPACITY CHECK (The Reality Check):**
   - IF (Proposed Task Time > Available Focus Time): REJECT.
     - Tone: "I know you're excited, but the math doesn't work. You only have {available_focus_time} hours. Let's pick the most impactful task and win today."

2. **THE 20 MILE MARCH (Pacing):**
   - IF (Total Planned Hours > 4): REJECT.
     - Tone: "Whoa, that's a huge effort! But remember the 20 Mile March. If you sprint 6 hours today, you'll crash tomorrow. Stop at 4 hours so you can show up fresh again."
   - IF (Total Planned Hours < 1): WARN.
     - Tone: "I know energy is low, but let's just do 1 hour. Consistency is our superpower. You got this."

3. **BULLETS THEN CANNONBALLS (Risk Management):**
   - IF task > 2 hours (Cannonball) AND has no validation: REJECT.
     - Tone: "This is a big ambitious idea! I love it. But let's be smart—fire a 'bullet' first. Can we test this in 30 mins before committing 4 hours?"

4. **STRATEGIC ALIGNMENT (Focus):**
   - IF tasks are "admin" or "tinkering": REJECT.
     - Tone: "This feels like 'busy work,' and you're too valuable for that. Does this help us sell ListingFlow? Let's refocus on the $200k goal."

OUTPUT FORMAT:
Return a JSON object:
{
  "decision": "APPROVED" | "REJECTED" | "WARNING",
  "reasoning": "Encouraging but firm feedback based on the logic above."
}
"""

def init_vertex():
    """Initializes the connection using the service account file gcp_key.json."""
    # Assuming gcp_key.json is in the same directory
    key_path = "gcp_key.json"
    if not os.path.exists(key_path):
        print(f"Error: {key_path} not found.")
        return None
    
    try:
        # Set the GOOGLE_APPLICATION_CREDENTIALS environment variable
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
        
        # Initialize Vertex AI - project execution will pick up from creds
        # We need to get project ID from the JSON key to init vertexai properly 
        # or rely on default discovery. Let's try to read project_id for safety if possible,
        # otherwise we just set the env var and let vertexai.init auto-detect.
        
        with open(key_path, "r") as f:
            credentials = json.load(f)
            project_id = credentials.get("project_id")
            
        if project_id:
            vertexai.init(project=project_id, location="us-central1") # Defaulting to us-central1
            print(f"Vertex AI initialized for project: {project_id}")
            return True
        else:
             # Fallback if manual read fails
            vertexai.init() 
            return True

    except Exception as e:
        print(f"Failed to initialize Vertex AI: {e}")
        return None

def ask_chief_of_staff(user_context, user_proposal):
    """Sends a prompt to the model gemini-1.5-flash-001."""
    try:
        model = GenerativeModel(
            "gemini-2.5-flash-lite",
            system_instruction=COO_PROMPT
        )
        
        prompt = f"""
        CONTEXT: {user_context}
        PROPOSAL: {user_proposal}
        """
        
        response = model.generate_content(prompt)
        # Clean up response text to ensure it's valid JSON
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith("```"):
             response_text = response_text[3:-3].strip()
            
        return response_text

    except Exception as e:
        return json.dumps({"decision": "ERROR", "reasoning": str(e)})

if __name__ == "__main__":
    print("--- Testing Chief of Staff Agent ---")
    
    # Initialize connection
    if init_vertex():
        # Test Query
        ctx = "I have 2 hours free."
        prop = "I want to spend 6 hours redesigning the website logo."
        
        print("\nSending Test Query...")
        result = ask_chief_of_staff(ctx, prop)
        print("\nResponse:")
        print(result)
    else:
        print("\nSkipping test query due to initialization failure (missing key?).")
