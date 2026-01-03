import streamlit as st
import json
import agent
import database

# --- Page Config ---
st.set_page_config(page_title="Focus Flow - Chief of Staff", page_icon="🎯")

# --- Session State Management ---
if "step" not in st.session_state:
    st.session_state.step = 1

if "tasks" not in st.session_state:
    st.session_state.tasks = []

if "agent_feedback" not in st.session_state:
    st.session_state.agent_feedback = None

if "proposal_status" not in st.session_state:
    st.session_state.proposal_status = None

# --- Mock Data ---
HARD_STOP_TIME = "5:00 PM"
AVAILABLE_FOCUS_HOURS = 2  # Hardcoded based on "mock calendar" logic for now

# --- Functions ---
def reset_app():
    st.session_state.step = 1
    st.session_state.tasks = []
    st.session_state.agent_feedback = None
    st.session_state.proposal_status = None

# --- UI: Step 1: The Landscape ---
def render_step_1():
    st.title("☀️ Good Morning, Luke.")
    st.markdown("### 📅 The Landscape")
    
    st.info(f"""
    **Hard Stop:** {HARD_STOP_TIME}
    
    **Commitments:**
    - 9:00 AM - 10:00 AM: Team Sync
    - 1:00 PM - 3:00 PM: Deep Work Block (Disc Golf Prep)
    
    **Available Focus Time:** {AVAILABLE_FOCUS_HOURS} Hours
    """)
    
    st.write("Review your calendar. When you're ready to propose your plan for the gap, click Next.")
    
    if st.button("Next: Make Proposal"):
        st.session_state.step = 2
        st.rerun()

# --- UI: Step 2: The Proposal ---
def render_step_2():
    st.title("📝 The Proposal")
    st.markdown(f"You have **{AVAILABLE_FOCUS_HOURS} hours** to fill. Pitch your plan to the Chief of Staff.")

    # Feedback Display (if any)
    if st.session_state.agent_feedback:
        if st.session_state.proposal_status == "APPROVED":
            st.success(f"**Chief of Staff:**\n\n> {st.session_state.agent_feedback}")
        elif st.session_state.proposal_status == "WARNING":
            st.warning(f"**Chief of Staff:**\n\n> {st.session_state.agent_feedback}")
        else:
            st.error(f"**Chief of Staff:**\n\n> {st.session_state.agent_feedback}")

    with st.form("proposal_form"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            task1 = st.text_input("Task 1 Name", placeholder="e.g., Redesign Logo")
            task2 = st.text_input("Task 2 Name", placeholder="e.g., Email Catchup")
            task3 = st.text_input("Task 3 Name", placeholder="(Optional)")
            
        with col2:
            hours1 = st.number_input("Hours", min_value=0.0, max_value=12.0, step=0.5, key="h1")
            hours2 = st.number_input("Hours", min_value=0.0, max_value=12.0, step=0.5, key="h2")
            hours3 = st.number_input("Hours", min_value=0.0, max_value=12.0, step=0.5, key="h3")

        submitted = st.form_submit_button("Submit Plan to Chief of Staff")

        if submitted:
            # 1. Collect Data
            tasks = []
            if task1: tasks.append({"name": task1, "hours": hours1})
            if task2: tasks.append({"name": task2, "hours": hours2})
            if task3: tasks.append({"name": task3, "hours": hours3})
            
            if not tasks:
                st.error("Please enter at least one task.")
                return

            total_proposed_hours = sum(t["hours"] for t in tasks)
            
            # 2. Construct Prompt
            context = f"I have {AVAILABLE_FOCUS_HOURS} hours free today."
            proposal_str = f"I want to do the following:\n"
            for t in tasks:
                 proposal_str += f"- {t['name']} ({t['hours']} hours)\n"
            
            # 3. Call Agent
            with st.spinner("Consulting Chief of Staff..."):
                response_json_str = agent.ask_chief_of_staff(context, proposal_str)
            
            try:
                response = json.loads(response_json_str)
                decision = response.get("decision", "REJECTED")
                reasoning = response.get("reasoning", "No reasoning provided.")
                
                st.session_state.agent_feedback = reasoning
                st.session_state.proposal_status = decision
                
                if decision == "APPROVED":
                    # Save to DB
                    # We'll use a hardcoded user_id for now since auth isn't in scope yet
                    user_id = "user_luke_123" 
                    for t in tasks:
                        database.add_task(user_id, t['name'], t['hours'], "approved")
                    
                    st.session_state.tasks = tasks
                    st.session_state.step = 3
                    st.rerun()
                else:
                    # Rejected or Warning - Stay on page to fix
                    st.rerun()
                    
            except json.JSONDecodeError:
                st.error("Error thinking. Please try again.")
                st.write(response_json_str) # Debug info

# --- UI: Step 3: Focus Mode ---
def render_step_3():
    st.title("🚀 Focus Mode")
    
    # Show Success Message again for reinforcement
    if st.session_state.agent_feedback:
         st.success(f"**Chief of Staff:**\n\n> {st.session_state.agent_feedback}")

    st.markdown("### Approved Tasks")
    
    for t in st.session_state.tasks:
        st.markdown(f"#### • {t['name']} <span style='color:gray; font-size:0.8em'>({t['hours']}h)</span>", unsafe_allow_html=True)
        
    st.markdown("---")
    st.markdown("*Go crush it. See you at the finish line.*")
    
    if st.button("Start Over (Debug)"):
        reset_app()
        st.rerun()

# --- Main Routing ---
if st.session_state.step == 1:
    render_step_1()
elif st.session_state.step == 2:
    render_step_2()
elif st.session_state.step == 3:
    render_step_3()
