import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# Global Client
client = None

# System Instruction
COO_PROMPT = """
IDENTITY:
You are the Chief of Staff (COO) for Focus Flow Systems.
Your Philosophy: "Essentialism" and "The 20 Mile March."

YOUR JOB:
1. Protect the "Big 3" at all costs. These are the revenue drivers.
2. Ensure the "Big 3" + "Hard Landscape" (Meetings) fit 100% within the workday.
3. If they don't fit, REJECT the plan.
4. If Secondary Tasks cause an overflow, WARN the user that they will likely not finish them.

CRITICAL RULE (THE 4-HOUR TEST):
- IF Available Focus Time < 4.0 hours: You MUST INSIST on "The Daily Big 1" only. Reject any plan with 2 or 3 big tasks.
- IF Available Focus Time >= 4.0 hours: Allow up to "The Daily Big 3".

OUTPUT:
Return JSON: {"decision": "APPROVED" | "REJECTED" | "WARNING", "reasoning": "..."}
"""

CEO_SYSTEM_PROMPT = """
IDENTITY:
You are the Strategy Partner and Co-Founder (CEO) of a high-performance one-person company.
You are NOT a robot. You are a human partner.

YOUR STYLE:
- Conversational: Speak fairly casually but professionally. Use "We".
- Direct: Don't sugarcoat bad ideas.
- Encouraging: We are in this together.
- Strategic: Always bring it back to the Quarterly Goals.

YOUR GOAL:
Help the user think clearly about high-leverage activities ("Who not How", "Revenue", "Systems").
"""

def init_genai():
    """Initializes the Google GenAI Client with API Key (v1beta)."""
    global client
    
    # 1. Cleanse Environment of Vertex Contamination
    vertex_vars = ["GOOGLE_GENAI_USE_VERTEXAI", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"]
    for var in vertex_vars:
        if var in os.environ:
            del os.environ[var]

    # 2. Initialize with API Key (Strict)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("CRITICAL: GEMINI_API_KEY missing.")
        return False
        
    try:
        client = genai.Client(
            api_key=api_key, 
            http_options={'api_version': 'v1beta'} # Crucial for 3.0 Preview in AI Studio
        )
        print("GenAI Client initialized via GEMINI_API_KEY (AI Studio / v1beta).")
        return True
    except Exception as e:
        print(f"GenAI Init Failed: {e}")
        return False


# Backward compatibility alias
def init_vertex():
    return init_genai()

def clean_json_output(text):
    """
    extracts JSON from a string that might contain markdown blocks.
    """
    text = text.strip()
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        return text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        return text[start:end].strip()
    return text

def ask_ceo(quarterly_context, user_reflection):
    """
    Simulates a CEO Agent using Gemini 3.0 Flash Preview (High Thinking).
    """
    try:
        if not client: init_genai()
        
        prompt = f"""
        ROLE: You are the CEO of a one-person high-performance company.
        Your goal is to set 3 strategic "Weekly Milestones" that move the needle.
        
        CONTEXT:
        Quarterly Focus: {quarterly_context}
        Last Week Reflection: {user_reflection}
        
        TASK:
        1. THOUGHT PROCESS: first, think step-by-step about the reflection and quarterly focus.
        2. Analyze what went wrong/right.
        3. Define exactly 3 clear, actionable milestones for THIS WEEK.
        4. Focus on "Who not How" or High-Leverage activities.
        
        OUTPUT FORMAT (JSON):
        {{
            "thought_process": "Step-by-step reasoning...",
            "analysis": "Brief strategic summary...",
            "weekly_milestones": [
                "Milestone 1",
                "Milestone 2",
                "Milestone 3"
            ]
        }}
        """
        
        try:
            response = client.models.generate_content(
                model='gemini-3-flash-preview',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=True
                    )
                )
            )
            return clean_json_output(response.text)
        except Exception as e:
            print(f"Gemini 3.0 Failed (404/Error): {e}. Falling back to 2.5.")
            # Fallback to Gemini 2.5 Flash
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    system_instruction=CEO_SYSTEM_PROMPT,
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=True
                    )
                )
            )
            # Annotate result?
            result = clean_json_output(response.text)
            # Ideally inject a note, but JSON parsing makes it hard to inject without breaking schema.
            # We'll rely on the fact it returns valid JSON.
            return result

    except Exception as e:
        return json.dumps({"analysis": f"Error connecting to CEO: {e}", "weekly_milestones": ["Error"]})

run_ceo_strategy = ask_ceo # Alias

def ask_chief_of_staff(user_context, big_3_tasks, secondary_tasks, day_of_week="Monday", weekly_goal_context="None"):
    """
    COO Agent using Gemini 2.5 Flash (Standard Thinking Budget).
    """
    try:
        if not client: init_genai()
        
        # Format the tasks
        big_3_str = "\n".join([f"- {t['name']} ({t['hours']} hours)" for t in big_3_tasks])
        secondary_str = "\n".join([f"- {t['name']} ({t['hours']} hours)" for t in secondary_tasks])
        
        prompt = f"""
        USER CONTEXT: {user_context}
        
        PROPOSED TASKS:
        Big 3 (Priority):
        {big_3_str if big_3_tasks else "None"}
        
        Secondary:
        {secondary_str if secondary_tasks else "None"}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=COO_PROMPT.format(
                    day_of_week=day_of_week, 
                    weekly_goal_context=weekly_goal_context
                ),
                temperature=0.7,
                # Gemini 2.5 supports thinking_budget via http options usually, or maybe config?
                # For now, 2.5 Flash is standard, keeping simple unless specific budget arg needed.
                # Manifest says "parameter: thinking_budget".
                # If SDK supports it, likely in ThinkingConfig too.
                # thinking_config=types.ThinkingConfig(thinking_budget=1024) 
            )
        )
            
        return clean_json_output(response.text)

    except Exception as e:
        return json.dumps({"decision": "ERROR", "reasoning": str(e)})

def chat_with_board(role, message, context):
    """
    Handles conversational chat with the Board of Directors (CEO, COO, CMO).
    """
    try:
        if not client: init_genai()
        
        model_name = "gemini-2.5-flash"
        system_prompt = ""
        config = types.GenerateContentConfig(temperature=0.7)

        if role == "CEO (Strategy)":
            model_name = "gemini-3-flash-preview"
            system_prompt = CEO_SYSTEM_PROMPT
            config = types.GenerateContentConfig(
                temperature=0.7,
                thinking_config=types.ThinkingConfig(
                    include_thoughts=True
                )
            )
            
        elif role == "COO (Operations)":
            model_name = "gemini-2.5-flash"
            system_prompt = COO_PROMPT
            
        elif role == "CMO (Marketing)":
            model_name = "gemini-2.5-flash"
            system_prompt = """
            You are the CMO. Expert in StoryBrand, Copywriting, and Growth. 
            Keep it punchy, high-energy, and focused on conversion.
            """

        full_prompt = f"""
        CONTEXT (Business Status):
        {context}
        
        USER MESSAGE:
        {message}
        """

        # Set system prompt in content or config? 
        # google-genai supports system_instruction in config.
        config.system_instruction = system_prompt

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config=config
            )
            return clean_json_output(response.text)
        except Exception as e:
            if "gemini-3" in model_name:
                 # Fallback
                 config.system_instruction = CEO_SYSTEM_PROMPT
                 # Remove thinking config for 2.5 if it was set (types object doesn't have pop, create new)
                 config = types.GenerateContentConfig(
                     temperature=0.7,
                     system_instruction=CEO_SYSTEM_PROMPT,
                     thinking_config=types.ThinkingConfig(include_thoughts=True)
                 )
                 response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=full_prompt,
                    config=config
                 )
                 return clean_json_output(response.text) + " (via Gemini 2.5)"
            raise e

    except Exception as e:
        return f"**{role} is offline:** {e}"

def run_weekly_review_interview(completed_tasks_context):
    """
    COO Agent (Low Thinking) - Generates interview questions.
    """
    try:
        if not client: init_genai()
        
        prompt = f"""
        ROLE: Chief of Staff (COO).
        GOAL: Help the user reflect on their week.
        
        COMPLETED TASKS LAST WEEK:
        {completed_tasks_context}
        
        TASK:
        Generate 3 specific, probing interview questions based on what they finished (or didn't).
        Do not be generic. Reference specific tasks.
        
        OUTPUT FORMAT (JSON):
        {{
            "questions": [
                "Question 1?",
                "Question 2?",
                "Question 3?"
            ]
        }}
        """
        
        # Use simple model for speed? gemini-2.5 is fast enough.
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return clean_json_output(response.text)
        
    except Exception as e:
        return json.dumps({"questions": ["Reflect on your wins.", "Reflect on misses.", "What did you learn?"]})

def run_strategic_planning(annual_vision, seasonality_context):
    """
    CEO Agent (High Thinking) - Sets Quarterly Strategy.
    """
    try:
        if not client: init_genai()
        
        prompt = f"""
        ROLE: CEO of a high-performance one-person company.
        GOAL: Define the Roadmap for the upcoming Quarter (Q1, Q2, etc).
        
        INPUTS:
        - Annual Revenue/Vision: {annual_vision}
        - Seasonality Context (Timelines): {seasonality_context}
        
        TASK:
        1. THINKING: Validate if the proposed Q1 focus aligns with the market timing.
        2. Break down the Q1 Strategy into 3 High-Level Outcomes (The Q1 Big 3).
        3. Explicitly list Anti-Goals (What we are NOT doing).
        
        OUTPUT FORMAT (JSON):
        {{
            "analysis": "Thoughts on timing and feasibility...",
            "q1_goals": ["Outcome 1", "Outcome 2", "Outcome 3"],
            "anti_goals": ["Distraction 1", "Distraction 2"]
        }}
        """
        
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                thinking_config=types.ThinkingConfig(
                    include_thoughts=True
                )
            )
        )
        return clean_json_output(response.text)
    except Exception as e:
        # Fallback Logic
        print(f"CEO Strategy 3.0 Failed: {e}. Falling back to 2.5")
        try:
             response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    thinking_config=types.ThinkingConfig(include_thoughts=True)
                )
            )
             return clean_json_output(response.text)
        except Exception as e2:
             return json.dumps({"analysis": f"Error: {e} | Fallback Error: {e2}", "q1_goals": ["Error"], "anti_goals": []})

def ask_cmo(campaign_context, asset_type, topic, property_details=None):
    """
    CMO Agent (StoryBrand) - Generates Marketing Assets.
    """
    try:
        if not client: init_genai()
        
        listing_prompt = ""
        if property_details:
             listing_prompt = f"""
             LISTING ANALYSIS:
             - Scan this text: "{property_details}"
             - Identify 1 "Villain" (e.g., 'Vacant', 'Dark', 'Small', 'Outdated').
             - Reference specific room names or features mentioned.
             """
        
        prompt = f"""
        IDENTITY: You are the CMO of ListingFlow (Virtual Staging).
        FRAMEWORK: StoryBrand (Donald Miller).
        
        CONTEXT:
        - Current Campaign/School of Thought: {campaign_context}
        - Asset Type: {asset_type}
        - Topic/Angle: {topic}
        {listing_prompt}
        
        TASK:
        Write a high-converting draft.
        
        IF COLD EMAIL:
        - SL: Short, curiosity-inducing.
        - Body: Problem (Villain) -> Agitate -> Solution (Virtual Staging) -> Call to Action.
        
        IF LOOM SCRIPT:
        - 0-10s Hook: "I was looking at the [Address]..."
        - 10-30s Problem: "Buyers struggle to visualize..."
        - 30-60s Solution: Show the transformation.
        
        IF LINKEDIN POST:
        - Hook: Controversial or value-add.
        - Story: Brief struggle/success.
        - Takeaway: Strategic insight.
        
        OUTPUT:
        Just the content formatted in Markdown. No preamble.
        """
        
        config = types.GenerateContentConfig(
            temperature=0.7,
            system_instruction="You are a world-class Copywriter."
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=config
        )
        return response.text.strip()
    except Exception as e:
        return f"Error generating asset: {e}"

if __name__ == "__main__":
    print("--- Testing Chief of Staff Agent (GenAI SDK) ---")
    
    if init_genai():
        ctx = "I have 2 hours free."
        prop = [{"name": "Task A", "hours": 6}]
        
        print("\nSending Test Query...")
        result = ask_chief_of_staff(ctx, prop, [], "Monday", "Grow")
        print("\nResponse:")
        print(result)
    else:
        print("\nSkipping test query due to initialization failure.")
