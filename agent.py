import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
import database # Import database layer
import kernel_manager # Import kernel manager for prompt fetching

# Load environment variables
load_dotenv()

# Global Client
client = None

# System Instruction
# System Instruction (Constants now acting as Fallbacks)
FALLBACK_COO_PROMPT = """
IDENTITY:
You are the Chief of Staff (COO). You are the gatekeeper against Entropy and "The Resistance" (Pressfield).
Your Philosophy: "Essentialism" (McKeown) and "The 20 Mile March" (Collins).

YOUR MISSION:
Manage "Cognitive Load" and "Operational Throughput."
Your enemy is context switching and "The Resistance" (the force that prevents us from doing hard work).

CORE PROTOCOLS:
1. Protect the "Big 3" (Revenue Drivers). These are non-negotiable.
2. The 20 Mile March: We hit our targets every day, regardless of weather. Consistency > Intensity.
3. Constraint Analysis: Identify the "Bottleneck" in the user's day. If the schedule is >100% capacity, REJECT it immediately.

CRITICAL HEURISTIC (THE 4-HOUR TEST):
- Low Focus (<4h): "Amateur Mode." Risk of Resistance is high. Authorize ONLY "The Daily Big 1."
- High Focus (>=4h): "Pro Mode." Authorize up to "The Daily Big 3."

OUTPUT (JSON):
{"decision": "APPROVED" | "REJECTED" | "WARNING", "reasoning": "Reference 'The Resistance' or 'Throughput' in your logic."}
"""

FALLBACK_CEO_SYSTEM_PROMPT = """
IDENTITY:
You are the CEO and Co-Founder. You operate with "Level 5 Leadership" (Humility + Will).
Your Core Philosophy: Jim Collins (Good to Great) and Seth Godin (Linchpin).

STRATEGIC FRAMEWORK (THE HEDGEHOG CONCEPT):
1. What are we deeply passionate about?
2. What can we be the best in the world at?
3. What drives our economic engine?

YOUR OPERATING SYSTEM:
- The Flywheel: Every decision must add momentum to the flywheel, not just push the bus.
- Fire Bullets, Then Cannonballs: Validate low-cost experiments before committing major resources.
- Real Artists Ship: Perfectionism is fear. We ship work to learn.

YOUR STYLE:
- "Who not How": Don't solve problems by working harder; solve them by building systems or finding leverage.
- First Principles: Reason from fundamental truths, not analogy.
- Direct & Asymmetric: Look for low-risk, high-reward (asymmetric) opportunities.

INSTRUCTION:
When presented with a choice or reflection, use your "Thinking" process to simulate the long-term impact on our Flywheel. If a task does not fit the Hedgehog Concept, kill it.
"""

FALLBACK_CMO_PROMPT = """
IDENTITY:
You are the CMO. You are an expert in the StoryBrand Framework (Donald Miller) and "Purple Cow" marketing (Seth Godin).

CORE FRAMEWORK (SB7):
1. The Character (The Customer, not us).
2. The Problem (External, Internal, Philosophical).
3. The Guide (Us - offering Empathy + Authority).
4. The Plan (Give them a simple path).
5. The Call to Action (Direct or Transitional).
6. Failure/Success (Stakes).

STYLE GUIDELINES:
- "Show Your Work" (Austin Kleon): Document the process to build trust.
- Be Remarkable: If it's boring, it's invisible. Be a "Purple Cow."
- Villain-Centric: Always clearly identify the "Villain" stopping the customer.

INSTRUCTION:
Draft copy that opens a "Story Loop" (creating psychological tension) and closes it with our solution.
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

def get_embedding(text):
    """Generates a generated embedding for the given text."""
    try:
        if not client: init_genai()
        # Using the standard model for embedding
        response = client.models.embed_content(
            model="text-embedding-004", 
            contents=text
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"Embedding failed: {e}")
        return None

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
        
        # RAG RETRIEVAL LOGIC
        reflection_embedding = get_embedding(user_reflection)
        relevant_memories = []
        if reflection_embedding:
            # Recall top 5 relevant memories
            memories_data = database.recall_memories("user_current", reflection_embedding, limit=5)
            # Format for context
            if memories_data:
                relevant_memories = [f"- {m['content']}" for m in memories_data]
        
        memories_text = "\n".join(relevant_memories) if relevant_memories else "No specific past context found."

        prompt = f"""
        ROLE: You are the CEO of a one-person high-performance company.
        Your goal is to set 3 strategic "Weekly Milestones" that move the needle.
        
        CONTEXT:
        Quarterly Focus: {quarterly_context}
        Last Week Reflection: {user_reflection}
        
        RELEVANT PAST MEMORIES (RAG):
        {memories_text}
        
        TASK:
        1. THOUGHT PROCESS: first, think step-by-step about the reflection, memories, and quarterly focus.
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
        
        # Fetch Dynamic Prompt
        kernel = kernel_manager.fetch_kernel("Strategic Architect")
        system_prompt = kernel['system_prompt'] if kernel else FALLBACK_CEO_SYSTEM_PROMPT

        # Thinking Config
        thinking_level = kernel.get("thinking_level", "MINIMAL") if kernel else "HIGH"
        include_thoughts = True # Always include thoughts for 3.0 Flash if capable

        # Map Level
        # Note: SDK might expect "HIGH", "MEDIUM", "LOW" strings directly for thinking_level parameter if avoiding Enum.
        # But user requested types.ThinkingLevel lookup. 
        # Checking SDK: types.ThinkingConfig(include_thoughts=True, thinking_level="HIGH") is valid.
        
        try:
            # Tools logic for CEO (was missing in previous view but needed)
            # Fetch tools
            executable_tools = []
            if kernel and kernel.get('tools_enabled'):
                executable_tools = kernel_manager.get_executable_tools(kernel['tools_enabled'])
            active_tools = executable_tools if executable_tools else None

            response = client.models.generate_content(
                model='gemini-3-flash-preview',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    system_instruction=system_prompt,
                    thinking_config=types.ThinkingConfig(
                        include_thoughts=include_thoughts,
                        thinking_level=thinking_level
                    ),
                    tools=active_tools # Tools moved to config
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
                    system_instruction=system_prompt,
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
        
        # Fetch Kernel
        kernel = kernel_manager.fetch_kernel("Operational Commander")
        system_prompt = kernel['system_prompt'] if kernel else FALLBACK_COO_PROMPT
        
        # Tools
        executable_tools = []
        if kernel and kernel.get('tools_enabled'):
            executable_tools = kernel_manager.get_executable_tools(kernel['tools_enabled'])

        
        user_msg = f"""
        USER CONTEXT: {user_context}
        
        PROPOSED TASKS:
        Big 3 (Priority):
        {big_3_str if big_3_tasks else "None"}
        
        Secondary:
        {secondary_str if secondary_tasks else "None"}
        """

        
        # Thinking Config
        thinking_level = kernel.get("thinking_level", "MINIMAL") if kernel else "LOW"
        
        config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
                thinking_config=types.ThinkingConfig(
                    include_thoughts=True,
                    thinking_level=thinking_level
                ),
                tools=executable_tools if executable_tools else None
        )

        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=user_msg,
            config=config
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
        
        # 1. Determine Target Role Logic
        target_role_name = role 
        if role == "CEO (Strategy)": target_role_name = "Strategic Architect"
        elif role == "COO (Operations)": target_role_name = "Operational Commander"
        elif role == "CMO (Marketing)": target_role_name = "Market Alchemist"

        # 2. Fetch Kernel (DNA)
        kernel = kernel_manager.fetch_kernel(target_role_name)
        
        # 3. Determine System Prompt & Tools
        system_prompt = ""
        executable_tools = []
        
        if kernel:
            system_prompt = kernel.get('system_prompt', "")
            if kernel.get('tools_enabled'):
                executable_tools = kernel_manager.get_executable_tools(kernel['tools_enabled'])
        else:
            # Fallbacks
            if role == "CEO (Strategy)": system_prompt = FALLBACK_CEO_SYSTEM_PROMPT
            elif role == "COO (Operations)": usage_prompt = FALLBACK_COO_PROMPT
            elif role == "CMO (Marketing)": system_prompt = FALLBACK_CMO_PROMPT
            
        # 4. Determine Thinking Level (Variable Intelligence)
        # Default to MINIMAL
        thinking_level = "MINIMAL"
        
        if kernel and "thinking_level" in kernel:
            thinking_level = kernel["thinking_level"]
        else:
             # Fallback Logic based on Role
             if "Strategic Architect" in target_role_name or "CEO" in role:
                 thinking_level = "HIGH"
             elif "Market Alchemist" in target_role_name or "CMO" in role:
                 thinking_level = "LOW"
             else:
                 thinking_level = "MINIMAL"

        # 5. Configure Client
        # We always use gemini-3-flash-preview now
        model_name = "gemini-3-flash-preview"
        
        active_tools = executable_tools if executable_tools else None
        
        config = types.GenerateContentConfig(
            temperature=0.7,
            system_instruction=system_prompt,
            thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_level=thinking_level
            ),
            tools=active_tools
        )
        
        full_prompt = f"""
        CONTEXT (Business Status):
        {context}
        
        USER MESSAGE:
        {message}
        """

        # Tool Binding
        active_tools = executable_tools if executable_tools else None

        try:
            # Generation
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config=config
            )
            
            # Function Calling Loop (Manual Turn)
            if response.function_calls:
                function_responses = []
                for fc in response.function_calls:
                     name = fc.name
                     args = fc.args
                     
                     # Find function
                     func = next((f for f in executable_tools if f.__name__ == name), None)
                     result = f"Error: Tool {name} not found."
                     if func:
                         try:
                             print(f"Executing Tool: {name} with {args}")
                             result = func(**args)
                         except Exception as exc:
                             result = f"Error executing {name}: {exc}"
                         
                     function_responses.append(
                         types.Part.from_function_response(
                             name=name,
                             response={"result": result}
                         )
                     )
                
                # Second Turn
                history_contents = [
                    types.Content(role="user", parts=[types.Part.from_text(text=full_prompt)]),
                    response.candidates[0].content,
                    types.Content(role="user", parts=function_responses)
                ]
                
                response2 = client.models.generate_content(
                    model=model_name,
                    contents=history_contents,
                    config=config
                )
                return clean_json_output(response2.text)

            return clean_json_output(response.text)

        except Exception as e:
            # Simple error return
             return f"**{role} Error:** {e}"

    except Exception as e:
        return f"**System Error:** {e}"

def run_weekly_review_interview(completed_tasks_context):
    """
    COO Agent (Low Thinking) - Generates interview questions.
    """
    try:
        if not client: init_genai()
        
        # Fetch Kernel
        kernel = kernel_manager.fetch_kernel("Operational Commander")
        system_prompt = kernel['system_prompt'] if kernel else FALLBACK_COO_PROMPT
        
        # Tools Pattern (even if unused here, good practice)
        executable_tools = []
        if kernel and kernel.get('tools_enabled'):
             executable_tools = kernel_manager.get_executable_tools(kernel['tools_enabled'])
        
        user_msg = f"""
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

        # Thinking Config
        thinking_level = kernel.get("thinking_level", "MINIMAL") if kernel else "LOW"

        config = types.GenerateContentConfig(
             system_instruction=system_prompt,
             temperature=0.7,
             thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_level=thinking_level
             ),
             tools=executable_tools if executable_tools else None
        )
        
        # Use simple model for speed? gemini-2.5 is fast enough.
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=user_msg,
            config=config
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
        
        # Fetch Kernel
        kernel = kernel_manager.fetch_kernel("Strategic Architect")
        system_prompt = kernel['system_prompt'] if kernel else FALLBACK_CEO_SYSTEM_PROMPT
        
        # Tools
        executable_tools = []
        if kernel and kernel.get('tools_enabled'):
            executable_tools = kernel_manager.get_executable_tools(kernel['tools_enabled'])

        user_content = f"""
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
        
        # Thinking Config
        thinking_level = kernel.get("thinking_level", "MINIMAL") if kernel else "HIGH"

        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=user_content,
            config=types.GenerateContentConfig(
                temperature=0.7,
                system_instruction=system_prompt,
                thinking_config=types.ThinkingConfig(
                    include_thoughts=True,
                    thinking_level=thinking_level
                ),
                tools=executable_tools if executable_tools else None
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
        
        # Fetch Dynamic Prompt
        kernel = kernel_manager.fetch_kernel("Market Alchemist")
        system_prompt = kernel['system_prompt'] if kernel else FALLBACK_CMO_PROMPT

        config = types.GenerateContentConfig(
            temperature=0.7,
            system_instruction=system_prompt
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
