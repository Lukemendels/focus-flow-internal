import streamlit as st
import json
import agent
import database
import google.generativeai as genai
import revenue
import kernel_manager # Import dynamic kernel registry
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# --- Initialization ---
if "vertex_initialized" not in st.session_state:
    if agent.init_vertex():
        st.session_state.vertex_initialized = True
    else:
        st.error("Failed to initialize Vertex AI. Check gcp_key.json.")

# --- Page Config ---
st.set_page_config(page_title="Focus Flow - Morning Ritual", page_icon="🌅", layout="centered")

# --- Session State Management ---
if "step" not in st.session_state:
    st.session_state.step = 1

if "tasks" not in st.session_state:
    st.session_state.tasks = []

if "rolled_over_tasks" not in st.session_state:
    st.session_state.rolled_over_tasks = []

if "agent_feedback" not in st.session_state:
    st.session_state.agent_feedback = None

if "proposal_status" not in st.session_state:
    st.session_state.proposal_status = None

if "available_hours" not in st.session_state:
    st.session_state.available_hours = 0.0

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [] 

# --- Constants & Mock Data ---
USER_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11" # Mock UUID for Luke
MOCK_MEETINGS_HOURS = 3 # 9-10 team sync, 1-3 deep work block (simulated as hard commitment)

# --- Functions ---
def reset_app():
    st.session_state.step = 1
    st.session_state.tasks = []
    st.session_state.rolled_over_tasks = []
    st.session_state.agent_feedback = None
    st.session_state.proposal_status = None
    st.session_state.available_hours = 0.0
    st.rerun()

def calculate_hours_until_stop(hard_stop_str):
    """
    Parses a time string (e.g., "17:00" or "5:00 PM") and calculates hours from 'now' (mocked as 8:00 AM).
    For simplicity in this mock, we'll assume 'now' is 8:00 AM.
    """
    try:
        # Simple parsing for HH:MM 24hr or 12hr format
        # Let's assume input is 24hr format string for simplicity of the input widget usually
        # But we will use st.time_input which returns a datetime.time object
        
        # Mock Now: 8:00 AM Today
        now_mock = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        
        # Combine today with hard stop time
        stop_time_dt = datetime.combine(datetime.today(), hard_stop_str)
        
        if stop_time_dt < now_mock:
            # Assume it's for tomorrow if time is earlier? Or just return 0
            return 0.0
            
        diff = stop_time_dt - now_mock
        total_hours = diff.total_seconds() / 3600.0
        return max(0.0, total_hours)
    except Exception:
        return 0.0

# --- UI: Step 1: The Review (Context) ---
def render_step_1():
    st.title("🌅 The Review")
    st.markdown("### Yesterday's Unfinished Business")
    
    # Fetch incomplete tasks
    # We trigger this only once or refresh? simple fetch every render is fine for low volume
    incomplete_tasks = database.get_yesterdays_incomplete(USER_ID)
    
    if not incomplete_tasks:
        st.info("No incomplete tasks from yesterday. Clean slate! ✨")
    else:
        st.write("Select tasks to roll over to today:")
        
    # Form for rolling over
    with st.form("rollover_form"):
        # We need to keep track of selections.
        # Checkboxes need unique keys.
        selected_tasks = []
        for t in incomplete_tasks:
            is_checked = st.checkbox(f"{t['task_name']} ({t['hours']}h)", value=True, key=f"ro_{t['id']}")
            if is_checked:
                selected_tasks.append(t)
        
        if st.form_submit_button("Next: Check Capacity"):
            # store rolled over tasks in session
            st.session_state.rolled_over_tasks = selected_tasks
            st.session_state.step = 2
            st.rerun()

import calendar_service

# --- UI: Step 2: The Landscape (Capacity) ---
def render_step_2():
    st.title("📅 The Landscape")
    
    # Fetch Real Calendar Data
    with st.spinner("Syncing with Google Calendar..."):
        events, total_meeting_hours = calendar_service.get_todays_events()
    
    st.info(f"""
    **Context (Real-Time):**
    - Current Time: {datetime.now().strftime("%I:%M %p")}
    - Fixed Commitments: {total_meeting_hours} Hours
    """)
    
    if events:
        with st.expander(f"See {len(events)} Meetings ({total_meeting_hours}h)", expanded=False):
            for e in events:
                st.write(f"• **{e['summary']}** ({e['start']} - {e['end']})")
    else:
        st.caption("No meetings found on 'primary' calendar for today.")
    
    # helper to generate 15-min options
    def get_time_options(start_hour=0, end_hour=24):
        opts = []
        for h in range(start_hour, end_hour):
            # Format to 12h
            h_12 = h if h <= 12 else h - 12
            h_12 = 12 if h_12 == 0 else h_12
            suffix = "AM" if h < 12 else "PM"
            
            opts.append(f"{h_12}:00 {suffix}")
            opts.append(f"{h_12}:15 {suffix}")
            opts.append(f"{h_12}:30 {suffix}")
            opts.append(f"{h_12}:45 {suffix}")
        return opts

    time_options = get_time_options(0, 24) # Allow full day

    # Calculate smart defaults
    now = datetime.now()
    
    # 1. Round up to next 15 min
    delta_min = 15 - (now.minute % 15)
    next_quarter = now + timedelta(minutes=delta_min)
    next_quarter = next_quarter.replace(second=0, microsecond=0)
    
    # Format to match options
    # %I is zero-padded hour (01-12). Our options use 1-12 (no zero padding for single digit if we built it that way?)
    # Let's check get_time_options format: f"{h_12}:00 {suffix}" -> h_12 is int, so "9:00 AM". %I gives "09".
    # We should normalize parsing or formatting.
    # Simple fix: custom format
    def format_12h(dt):
        h = dt.hour
        h_12 = h if h <= 12 else h - 12
        h_12 = 12 if h_12 == 0 else h_12
        suffix = "AM" if h < 12 else "PM"
        return f"{h_12}:{dt.minute:02d} {suffix}"

    default_start_str = format_12h(next_quarter)
    default_end_str = format_12h(next_quarter + timedelta(minutes=30))

    col_start, col_end = st.columns(2)
    
    with col_start:
        def_start_idx = time_options.index(default_start_str) if default_start_str in time_options else 0
        start_time_str = st.selectbox("Start Time", time_options, index=def_start_idx)

    with col_end:
        def_end_idx = time_options.index(default_end_str) if default_end_str in time_options else min(def_start_idx + 2, len(time_options)-1)
        hard_stop_str = st.selectbox("Hard Stop", time_options, index=def_end_idx)

    # --- Calculations ---
    # Intersection Logic: Only subtract meetings that overlap with selected window
    try:
        def parse_to_dt(t_str):
            t = datetime.strptime(t_str, "%I:%M %p").time()
            return datetime.combine(datetime.now().date(), t)

        start_dt = parse_to_dt(start_time_str)
        end_dt = parse_to_dt(hard_stop_str)
        
        # Ensure timezones for comparison if events are offset-aware
        # Easy hack: convert events to simple naive if in same day/zone or make window aware
        # Calendar API returns offsets. Let's make window offset aware (local) if simple.
        # Actually easier: convert event ISO directly to datetime and compare
        
        if end_dt <= start_dt:
            st.warning("⚠️ End time must be after start time.")
            total_window = 0.0
            conflicting_hours = 0.0
        else:
            total_window = (end_dt - start_dt).total_seconds() / 3600.0
            
            # Calculate overlapping meeting time
            conflicting_seconds = 0.0
            
            # Make window start/end offset-naive for comparison (assuming events converted to naive or similar)
            # Events from service are fromisoformat() which keeps offset.
            # Let's rely on naive for simplicity in this local context? 
            # OR better: make start_dt/end_dt aware using local system time?
            # Let's strip offsets from events for today-only logic to avoid timezone headaches in this MVP.
            
            for e in events:
                # Parse event times
                e_start = datetime.fromisoformat(e['start_iso'])
                e_end = datetime.fromisoformat(e['end_iso'])
                
                # Make naive
                e_start_naive = e_start.replace(tzinfo=None)
                e_end_naive = e_end.replace(tzinfo=None)
                
                # Check overlap
                # Max of starts, Min of ends
                overlap_start = max(start_dt, e_start_naive)
                overlap_end = min(end_dt, e_end_naive)
                
                if overlap_start < overlap_end:
                    conflicting_seconds += (overlap_end - overlap_start).total_seconds()
            
            conflicting_hours = conflicting_seconds / 3600.0
            
    except Exception as e:
        st.error(f"Error calculating time: {e}")
        total_window = 0.0
        conflicting_hours = 0.0

    available_focus = max(0.0, total_window - conflicting_hours)
    
    st.info(f"""
    **Analysis:**
    - Window ({start_time_str} - {hard_stop_str}): {total_window:.2f} Hours
    - Conflicting Meetings: -{conflicting_hours:.2f} Hours
    """)
    
    st.metric("Net Available Focus Time", f"{available_focus:.2f} Hours")
    
    if available_focus <= 0.25:
        st.warning("Not enough time for deep work!")
    
    if st.button("Next: Plan The Big 3"):
        st.session_state.available_hours = available_focus
        st.session_state.step = 3
        st.rerun()

# --- UI: Step 3: The Proposal (Planning) ---
def render_step_3():
    st.title("📝 The Proposal")
    st.markdown(f"You have **{st.session_state.available_hours:.1f} hours** of Focus Time.")

    if st.session_state.agent_feedback:
        if st.session_state.proposal_status == "APPROVED":
            st.success(f"**Chief of Staff:**\n\n> {st.session_state.agent_feedback}")
        elif st.session_state.proposal_status == "WARNING":
            st.warning(f"**Chief of Staff:**\n\n> {st.session_state.agent_feedback}")
        else:
            st.error(f"**Chief of Staff:**\n\n> {st.session_state.agent_feedback}")

    with st.form("planning_form"):
        st.markdown("### 🔥 The Big 3 (Must Do)")
        col1, col2 = st.columns([3, 1])
        with col1:
            b1 = st.text_input("Big Task 1", key="b1")
            b2 = st.text_input("Big Task 2", key="b2")
            b3 = st.text_input("Big Task 3", key="b3")
        with col2:
            h1 = st.number_input("Hours", 0.0, 12.0, step=0.5, key="h1")
            h2 = st.number_input("Hours", 0.0, 12.0, step=0.5, key="h2")
            h3 = st.number_input("Hours", 0.0, 12.0, step=0.5, key="h3")

        st.markdown("### 📥 Secondary Tasks (Admin/Rollover)")
        # Pre-fill with rolled over tasks functionality
        # For simplicity, we just list them as text inputs, maybe pre-populating value if possible is tricky dynamically in loop
        # Let's just create a dynamic list of inputs or a fixed set large enough.
        # Or better: Just 2 slots for new ones, plus we auto-add rollover tasks to the list sent to agent?
        # User requested "List rolled-over tasks here + allow adding new ones".
        
        # Initializing rolled over text
        ro_tasks = st.session_state.rolled_over_tasks
        
        # We'll display rolled over items just for visibility? Or allow editing?
        # Requirement: "List rolled-over tasks here"
        if ro_tasks:
            st.caption("Rolled Over Tasks (Will be included in proposal):")
            for t in ro_tasks:
                 st.markdown(f"- **{t['task_name']}** ({t['hours']}h)")
        
        st.caption("Add New Secondary Tasks:")
        col3, col4 = st.columns([3, 1])
        with col3:
            s1 = st.text_input("Secondary 1", key="s1")
            s2 = st.text_input("Secondary 2", key="s2")
        with col4:
            sh1 = st.number_input("Hours", 0.0, 12.0, step=0.5, key="sh1")
            sh2 = st.number_input("Hours", 0.0, 12.0, step=0.5, key="sh2")

        submit = st.form_submit_button("Submit Plan to Chief of Staff")
        
        if submit:
            # Construct Lists
            big_3_list = []
            if b1: big_3_list.append({"name": b1, "hours": h1})
            if b2: big_3_list.append({"name": b2, "hours": h2})
            if b3: big_3_list.append({"name": b3, "hours": h3})
            
            secondary_list = []
            # Add rolled over
            for t in st.session_state.rolled_over_tasks:
                secondary_list.append({"name": t['task_name'], "hours": t['hours']})
            # Add new inputs
            if s1: secondary_list.append({"name": s1, "hours": sh1})
            if s2: secondary_list.append({"name": s2, "hours": sh2})

            if not big_3_list and not secondary_list:
                st.error("Plan cannot be empty.")
                return

            # Agent Call
            context = f"I have {st.session_state.available_hours} hours free today."
            with st.spinner("Consulting Chief of Staff..."):
                resp_str = agent.ask_chief_of_staff(context, big_3_list, secondary_list)
            
            try:
                resp = json.loads(resp_str)
                decision = resp.get("decision", "REJECTED")
                reasoning = resp.get("reasoning", "No reasoning provided.")
                st.session_state.agent_feedback = reasoning
                st.session_state.proposal_status = decision
                
                if decision == "APPROVED":
                    # Save to DB - flatten list for simplicity or tag them
                    user_id = USER_ID
                    
                    # Combine for display/storage
                    all_tasks = big_3_list + secondary_list
                    
                    db_errors = []
                    for t in big_3_list:
                        res = database.add_task(user_id, t['name'], t['hours'], "approved", is_big_3=True)
                        if not res: db_errors.append(t['name'])
                        
                    for t in secondary_list:
                        res = database.add_task(user_id, t['name'], t['hours'], "approved", is_big_3=False)
                        if not res: db_errors.append(t['name'])
                    
                    if db_errors:
                        st.error(f"Failed to save {len(db_errors)} tasks to database. (Schema issue?): {', '.join(db_errors)}")
                        st.write("Tip: Go to Supabase -> Settings -> API -> Reload Schema Cache")
                    else:
                        st.session_state.tasks = all_tasks
                        st.session_state.step = 4
                        st.rerun()
                else:
                    # Rerun to show error
                    st.rerun()

            except Exception as e:
                st.error(f"Agent error: {e}")

# --- UI: Step 4: Focus Mode (Dashboard) ---
def render_step_4():
    st.title("🚀 Focus Mode")
    
    if st.session_state.agent_feedback:
         st.success(f"**Chief of Staff:**\n\n> {st.session_state.agent_feedback}")

    # Fetch tasks from DB for today to ensure sync? 
    # Or just use session state? Using DB is more robust.
    today_tasks = database.get_todays_tasks(USER_ID)
    
    # Filter Big 3 vs Secondary
    b3_tasks = [t for t in today_tasks if t.get('is_big_3')]
    sec_tasks = [t for t in today_tasks if not t.get('is_big_3')]

    st.markdown("## 🔥 THE BIG 3")
    for t in b3_tasks:
        col_chk, col_txt = st.columns([0.1, 0.9])
        with col_chk:
             # Checkbox state needs to be persistent/reactive
             is_done = st.checkbox("Done", value=t['completed'], key=f"done_{t['id']}", 
                                   label_visibility="collapsed")
             if is_done != t['completed']:
                 # Trigger update if changed
                 if is_done:
                     database.mark_task_complete(t['id'])
                     st.toast(f"Crushed it: {t['task_name']}")
                 # We could add uncheck logic but database.py only has mark_complete currently
                 # reloading to reflect state
                 st.rerun()
        with col_txt:
            st.markdown(f"**{t['task_name']}** ({t['hours']}h)")

    st.markdown("---")
    st.markdown("### 📥 Secondary Tasks")
    for t in sec_tasks:
        col_chk, col_txt = st.columns([0.1, 0.9])
        with col_chk:
             is_done = st.checkbox("Done", value=t['completed'], key=f"done_{t['id']}", 
                                   label_visibility="collapsed")
             if is_done != t['completed']:
                 if is_done:
                     database.mark_task_complete(t['id'])
                     st.toast(f"Done: {t['task_name']}")
                 st.rerun()
        with col_txt:
            st.markdown(f"{t['task_name']} ({t['hours']}h)")
            
    if st.button("Start New Day (Debug Reset)"):
        reset_app()

# --- UI: Weekly Strategy View ---
def render_weekly_strategy():
    st.title("🧠 The CEO's Office")
    st.markdown("*> Strategy is about making choices, trade-offs; it's about deliberately choosing to be different.*")
    
    with st.expander("ℹ️ How this works", expanded=False):
        st.write("This is a high-level reasoning session. The CEO Agent analyzes your reflection and quarterly goals to set 3 Strategic Milestones for the week.")

    # Fetch Active Quarterly Goal
    active_q = database.get_active_quarterly_goal(USER_ID)
    if active_q:
        st.info(f"**North Star (Q-Plan):** {active_q['description']}")
        quarterly_focus_val = active_q['description']
    else:
        st.warning("No Active Quarterly Plan Found.")
        quarterly_focus_val = ""

    if quarterly_focus_val:
        quarterly_focus = st.text_area("Quarterly Focus / North Star", value=quarterly_focus_val, height=100, help="What is the ONE thing that matters this quarter?")
    else:
        quarterly_focus = st.text_area("Quarterly Focus / North Star", height=100, help="What is the ONE thing that matters this quarter?")
            
    reflection = st.text_area("Reflection on Last Week", height=150, help="What went well? What blocked you? be honest.")
    
    if st.button("Generate Weekly Plan"):
        if not quarterly_focus or not reflection:
            st.error("Please provide both context and reflection.")
        else:
            with st.spinner("The CEO is thinking... (This uses high-reasoning models)"):
                # Call CEO Agent
                response_json_str = agent.ask_ceo(quarterly_focus, reflection)
                
            try:
                plan = json.loads(response_json_str)
                st.session_state.ceo_plan = plan
            except:
                st.error("CEO Agent returned invalid format. Try again.")
                st.write(response_json_str)

    if "ceo_plan" in st.session_state:
        plan = st.session_state.ceo_plan
        st.subheader("📊 CEO's Analysis")
        st.write(plan.get("analysis", "No analysis provided."))
        
        st.subheader("🎯 Weekly Milestones")
        milestones = plan.get("weekly_milestones", [])
        for i, m in enumerate(milestones):
            st.info(f"**{i+1}.** {m}")
            
        if st.button("Commit to this Plan"):
            # Save to DB
            today = datetime.now().date()
            end_of_week = today + timedelta(days=(6 - today.weekday()))
            
            desc = "\n".join([f"- {m}" for m in milestones])
            res = database.add_goal(USER_ID, desc, today.isoformat(), end_of_week.isoformat())
            
            if res:
                st.success("Weekly Strategy Saved! Go to 'Daily Ritual' to execute.")
                st.balloons()
            else:
                st.error("Failed to save goals.")


# --- UI: Daily Ritual View (The Main Wizard) ---
def render_daily_ritual():
    # 0. Check Context (Weekend vs Weekday)
    today = datetime.now()
    is_weekend = today.weekday() >= 5 # 5=Sat, 6=Sun
    day_name = today.strftime("%A")
    
    # 0.5 Fetch Strategic Context (Q + W)
    active_q = database.get_active_quarterly_goal(USER_ID)
    active_w = database.get_active_weekly_goal(USER_ID)
    
    st.sidebar.markdown("---")
    st.sidebar.header("🔭 Strategy")
    
    if active_q:
        st.sidebar.info(f"**Q-Focus:**\n{active_q['description']}")
    
    if active_w:
        st.sidebar.success(f"**Weekly Goal:**\n{active_w['description']}")
        weekly_context = active_w['description']
    else:
        st.sidebar.warning("No Weekly Goal Found.")
        if st.sidebar.button("Set Strategy"):
             st.info("Switch to 'Weekly Strategy' in the sidebar!")
        weekly_context = "None set."
        
    # Combine contexts for Agent
    q_context_str = active_q['description'] if active_q else "None"
    full_strat_context = f"Quarterly Focus: {q_context_str}. Weekly Goal: {weekly_context}"

    # Progress Bar UI at top
    steps = ["Review", "Landscape", "Proposal", "Focus"]
    current_step_idx = st.session_state.step - 1
    st.progress((current_step_idx + 1) / 4)
    st.caption(f"Step {st.session_state.step} of 4: {steps[current_step_idx]}")

    # Routing based on Step selection
    if st.session_state.step == 1:
        render_step_1()
    elif st.session_state.step == 2:
        render_step_2()
    elif st.session_state.step == 3:
        render_step_3(is_weekend, day_name, full_strat_context)
    elif st.session_state.step == 4:
        render_step_4()


def render_step_3(is_weekend, day_name, weekly_context):
    st.title("📝 The Proposal")
    
    limit_hours = 6.0 if is_weekend else 2.0
    mode_title = "Weekend Warrior Mode ⚔️" if is_weekend else "Weekday Essentialism 🛡️"
    
    st.info(f"""
    **{mode_title} ({day_name})**
    - Focus Limit: **{limit_hours} hours** max.
    - { "Prioritize 'The Daily Big 3'" if is_weekend else "Prioritize 'The Daily Big 1' only." }
    - Available Focus Time: **{st.session_state.get('available_hours', 0.0):.2f} hours**
    """)

    # Display agent feedback if any
    if st.session_state.get('proposal_status'):
        if st.session_state.proposal_status == "APPROVED":
            st.success(f"**Chief of Staff:**\n\n> {st.session_state.agent_feedback}")
        elif st.session_state.proposal_status == "WARNING":
            st.warning(f"**Chief of Staff:**\n\n> {st.session_state.agent_feedback}")
        else:
            st.error(f"**Chief of Staff:**\n\n> {st.session_state.agent_feedback}")

    with st.form("plan_form"):
        st.subheader("The Plan")
        
        big_3 = []
        
        # Dynamic Slots
        num_slots = 3 if is_weekend else 1
        slot_label = "Task" if num_slots == 1 else "Task"

        for i in range(num_slots):
            c1, c2 = st.columns([3, 1])
            with c1:
                name = st.text_input(f"{slot_label} {i+1} (Priority)", key=f"b3_{i}")
            with c2:
                hours = st.number_input(f"Hours", min_value=0.25, max_value=limit_hours, step=0.25, key=f"b3_h_{i}")
            if name:
                big_3.append({"name": name, "hours": hours})
        
        # Secondary Tasks
        st.subheader("Secondary Tasks (Optional)")
        secondary = []
        
        # Pre-fill from rollover
        rollover = st.session_state.get('rolled_over_tasks', [])
        
        # Display 2 slots for secondary + any rollover logic
        # For simplicity, just 2 static slots for now + rollover integration could be complex
        # Let's just list 2 new slots
        for i in range(2):
           c1, c2 = st.columns([3, 1])
           with c1:
               # If we have rollover, maybe pre-fill? 
               def_val = rollover[i]['task_name'] if i < len(rollover) else ""
               name = st.text_input(f"Secondary {i+1}", value=def_val, key=f"sec_{i}")
           with c2:
               hours = st.number_input(f"Hours", min_value=0.25, max_value=2.0, step=0.25, key=f"sec_h_{i}")
           if name:
               secondary.append({"name": name, "hours": hours})

        submitted = st.form_submit_button("Submit Plan to Chief of Staff")
        
        if submitted:
            # 1. Check Constraints
            total_planned = sum(t['hours'] for t in big_3) + sum(t['hours'] for t in secondary)
            available = st.session_state.get('available_hours', 0)
            
            # Allow slight overflow? No, strict.
            # Actually, agent does the strict check. Step 2 did the math.
            # Let's interact with Agent.
            
            with st.spinner(f"Consulting Chief of Staff ({day_name} Rules applied)..."):
                context = f"User has {available} hours focus time. Day is {day_name}. Strategy Context: {weekly_context}"
                
                response = agent.ask_chief_of_staff(
                    user_context=context,
                    big_3_tasks=big_3,
                    secondary_tasks=secondary,
                    day_of_week=day_name,
                    weekly_goal_context=weekly_context
                )
            
            try:
                valid_json = response.replace("```json", "").replace("```", "")
                decision_data = json.loads(valid_json)
                decision = decision_data.get("decision", "ERROR")
                reasoning = decision_data.get("reasoning", "No reasoning provided.")
                
                st.session_state.agent_feedback = reasoning # Store feedback
                st.session_state.proposal_status = decision
                
                if decision == "APPROVED":
                    st.success("✅ Plan APPROVED!")
                    save_tasks_to_db(big_3, secondary)
                elif decision == "WARNING":
                    st.warning(f"⚠️ PROCEED WITH CAUTION: {reasoning}")
                    if st.button("Proceed Anyway"):
                         save_tasks_to_db(big_3, secondary)
                else:
                    st.error(f"❌ PLAN REJECTED: {reasoning}")
                
                # Rerun to display feedback and potentially the "Proceed Anyway" button
                st.rerun()
                    
            except Exception as e:
                st.error(f"Agent Error: {e} | Raw: {response}")

def save_tasks_to_db(big_3_list, secondary_list):
    user_id = USER_ID
    all_tasks = big_3_list + secondary_list
    
    db_errors = []
    for t in big_3_list:
        res = database.add_task(user_id, t['name'], t['hours'], "approved", is_big_3=True)
        if not res: db_errors.append(t['name'])
        
    for t in secondary_list:
        res = database.add_task(user_id, t['name'], t['hours'], "approved", is_big_3=False)
        if not res: db_errors.append(t['name'])
    
    if db_errors:
        st.error(f"Saved some, but failed: {', '.join(db_errors)}")
    else:
        st.session_state.tasks = all_tasks
        st.session_state.step = 4
        st.rerun()

# --- UI: Sunday Review Wizard ---
def render_sunday_review():
    st.title("🕯️ The Sunday Ritual")
    
    # Simple State Machine for Sunday Review
    if "sunday_step" not in st.session_state:
        st.session_state.sunday_step = 1
        
    steps = ["Review Data", "The Interview", "Strategy"]
    current_idx = st.session_state.sunday_step - 1
    st.progress((current_idx + 1) / 3)
    st.caption(f"Phase {st.session_state.sunday_step}: {steps[current_idx]}")

    if st.session_state.sunday_step == 1:
        render_sunday_step_1()
    elif st.session_state.sunday_step == 2:
        render_sunday_step_2()
    elif st.session_state.sunday_step == 3:
        render_sunday_step_3()

def render_sunday_step_1():
    st.header("1. The Rearview Mirror")
    st.write("Let's look at what you actually got done last week.")
    
    tasks = database.get_completed_tasks_last_week(USER_ID)
    
    if tasks:
        st.success(f"You completed **{len(tasks)} tasks** last week! 🏆")
        for t in tasks:
            st.write(f"- ✅ {t['task_name']} ({t['hours']}h)")
            
        # Store context for next step
        task_summary = "\n".join([f"- {t['task_name']}" for t in tasks])
        st.session_state.last_week_context = task_summary
    else:
        st.warning("No completed tasks found for the last 7 days. (Did you log them?)")
        st.session_state.last_week_context = "No tasks completed."
    
    if st.button("Ready for The Interview"):
        st.session_state.sunday_step = 2
        st.rerun()

def render_sunday_step_2():
    st.header("2. The COO Interview")
    st.write("Reflecting on the data above...")
    
    if "interview_questions" not in st.session_state:
        with st.spinner("COO is analyzing your week..."):
            resp_json = agent.run_weekly_review_interview(st.session_state.last_week_context)
            try:
                data = json.loads(resp_json)
                st.session_state.interview_questions = data.get("questions", ["Q1?", "Q2?", "Q3?"])
            except:
                st.session_state.interview_questions = ["What went well?", "What went wrong?", "Key lesson?"]

    with st.form("reflection_form"):
        q = st.session_state.interview_questions
        
        st.markdown(f"**Q1:** {q[0]}")
        a1 = st.text_area("Answer 1", key="a1")
        
        st.markdown(f"**Q2:** {q[1]}")
        a2 = st.text_area("Answer 2", key="a2")
        
        st.markdown(f"**Q3:** {q[2]}")
        a3 = st.text_area("Answer 3", key="a3")
        
        if st.form_submit_button("Submit Reflections"):
            # Synthesize for next step
            full_reflection = f"Q1: {q[0]}\nA1: {a1}\nQ2: {q[1]}\nA2: {a2}\nQ3: {q[2]}\nA3: {a3}"
            st.session_state.reflection_context = full_reflection
            
            # Save to DB
            today = datetime.now().date()
            # Approximation of week start
            week_start = today - timedelta(days=6) 
            database.save_reflection(USER_ID, week_start.isoformat(), a1, a2, a3)
            
            st.session_state.sunday_step = 3
            st.rerun()

# --- UI: Strategy War Room ---
def render_war_room():
    st.title("⚔️ The War Room")
    st.markdown("*> Strategy without tactics is the slowest route to victory. Tactics without strategy is the noise before defeat.*")

    # 1. Existing Context
    active_q = database.get_active_quarterly_goal(USER_ID)
    if active_q:
        st.success(f"**Current Q-Plan Active:** {active_q['description']}")
        with st.expander("See Full Strategic Context"):
            st.write(active_q.get('context', 'No context saved.'))
    else:
        st.info("No Active Quarterly Plan. Let's build one.")

    # --- Revenue Scoreboard ---
    st.markdown("---")
    st.subheader("📊 Financial Signal")
    
    col_rev1, col_rev2 = st.columns(2)
    with col_rev1:
        if st.button("Sync Financials (Stripe)"):
            with st.spinner("Pinging Stripe API..."):
                snapshot = revenue.get_synchronous_financial_snapshot()
                if snapshot:
                    st.session_state.financial_snapshot = snapshot
                else:
                    st.warning("Could not sync with Stripe (Check API Keys).")
    
    if "financial_snapshot" in st.session_state:
        snap = st.session_state.financial_snapshot
        # Format cents to dollars
        gross = snap["gross_volume_cents"] / 100
        avail = snap["balance_available"] / 100
        pending = snap["balance_pending"] / 100
        
        with col_rev1:
            st.metric("Today's Gross Volume (UTC)", f"${gross:,.2f}")
        with col_rev2:
            st.metric("Available Balance", f"${avail:,.2f}", delta=f"Pending: ${pending:,.2f}")
    else:
        with col_rev2:
            st.caption("No data synced yet.")
            
    st.markdown("---")

    # 2. Inputs
    col1, col2 = st.columns(2)
    with col1:
        revenue_target = st.text_input("Annual Revenue Target", value="$200,000")
    with col2:
        current_quarter = "Q" + str((datetime.now().month - 1) // 3 + 1)
        st.write(f"Planning for: **{current_quarter}**")

    seasonality = st.text_area("Strategic Vision & Seasonality Context", height=150, 
        help="Paste your timeline here. E.g., 'ListingFlow in Spring, SermonFlow in Fall'.")

    # 3. Agent Action
    if st.button("Generate Strategic Plan"):
        if not seasonality:
            st.error("Context required.")
        else:
            with st.spinner("CEO is analyzing market timing..."):
                resp = agent.run_strategic_planning(revenue_target, seasonality)
                st.session_state.war_room_plan = resp

    # 4. Display & Commit
    if "war_room_plan" in st.session_state:
        try:
            plan = json.loads(st.session_state.war_room_plan)
            st.subheader("CEO Diagnosis")
            st.write(plan.get("analysis"))
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader(f"✅ {current_quarter} Big 3")
                for g in plan.get("q1_goals", []):
                    st.success(f"- {g}")
            with c2:
                st.subheader(f"⛔ Anti-Goals")
                for g in plan.get("anti_goals", []):
                    st.error(f"- {g}")
            
            if st.button("Commit to Operation"):
                today = datetime.now().date()
                # Approx 90 days
                end_date = today + timedelta(days=90)
                
                desc = "\n".join([f"- {g}" for g in plan.get("q1_goals", [])])
                full_context = f"VISION: {revenue_target}\nCONTEXT: {seasonality}\nANTI-GOALS: {plan.get('anti_goals')}"
                
                database.save_quarterly_goal(USER_ID, desc, today.isoformat(), end_date.isoformat(), full_context)
                st.balloons()
                st.success("Strategic Backbone Installed.")
                
        except Exception as e:
            st.error("Error parsing plan.")
            st.write(st.session_state.war_room_plan)

def render_sunday_step_3():
    st.header("3. The CEO Strategy")
    st.write("Based on your reflections, here is the strategy for next week.")
    
    # FETCH QUARTERLY CONTEXT AUTOMATICALLY
    active_q = database.get_active_quarterly_goal(USER_ID)
    if active_q:
        q_context = active_q['description']
        st.info(f"Aligned with Q-Goal: {q_context}")
    else:
        q_context = st.text_input("No Active Q-Plan. Enter Focus manually:", value="Launch MVP")
    
    if "ceo_strategy" not in st.session_state:
        if st.button("Generate Strategy"):
            with st.spinner("CEO is thinking..."):
                resp = agent.run_ceo_strategy(st.session_state.reflection_context, q_context)
                st.session_state.ceo_strategy_json = resp
                st.rerun()
    
    if "ceo_strategy_json" in st.session_state:
        try:
            data = json.loads(st.session_state.ceo_strategy_json)
            st.subheader("Analysis")
            st.write(data.get("analysis"))
            
            st.subheader("The Weekly Big 3")
            milestones = data.get("weekly_milestones", [])
            for m in milestones:
                st.info(f"🎯 {m}")
                
            if st.button("Commit to this Plan"):
                today = datetime.now().date()
                end_week = today + timedelta(days=6)
                desc = "\n".join([f"- {m}" for m in milestones])
                
                database.save_weekly_goal(USER_ID, desc, today.isoformat(), end_week.isoformat())
                st.balloons()
                st.success("Week Planned! See you mainly in 'Daily Ritual'.")
                
        except Exception as e:
            st.error("Error parsing strategy.")
            st.write(st.session_state.ceo_strategy_json)


# --- UI: Board Room Chat ---
def render_board_room():
    st.title("🗣️ The Board Room")
    st.caption("Chat with your AI Executive Team")

    # Sidebar: Select Agent (Dynamic from DB)
    with st.sidebar:
        st.header("Who is Speaking?")
        
        # Fetch Active Kernels
        active_roles = kernel_manager.list_active_kernels()
        
        # Fallback if DB fetch fails
        if not active_roles:
            active_roles = ["The Chairman", "Strategic Architect", "Operational Commander", "Market Alchemist"]
        
        # Optional: Add Genesis Mode (The Builder)
        # Genesis Mode is special - maybe we add it manually to the list for now?
        # active_roles.append("Genesis Architect") 

        agent_role = st.selectbox(
            "Select Agent:",
            active_roles
        )

        st.info(f"Speaking with: **{agent_role}**")
        
        # Legacy Info Block - removed or made dynamic?
        # For now, simplistic info based on known defaults or just generic
        if "Strategic Architect" in agent_role or "CEO" in agent_role:
             st.caption("Focus: High-level strategy, 'Who not How'.")
        elif "Operational Commander" in agent_role or "COO" in agent_role:
             st.caption("Focus: Execution, Efficiency, 'The 4-Hour Rule'.")
        elif "Market Alchemist" in agent_role or "CMO" in agent_role:
             st.caption("Focus: Growth, StoryBrand, Copywriting.")
        elif "Chairman" in agent_role:
             st.caption("Focus: Routing & Orchestration.")
        
        if st.button("Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

    # Sticky Chat Input
    if prompt := st.chat_input(f"Ask {agent_role}..."):
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # Build Context (Invisible)
        active_q = database.get_active_quarterly_goal(USER_ID)
        q_context = active_q['description'] if active_q else "No Active Quarterly Goal."
        
        # Try to get financial context if available
        fin_context = "Financials: Not Synced."
        if "financial_snapshot" in st.session_state:
            s = st.session_state.financial_snapshot
            fin_context = f"Funds Available: ${(s['balance_available']/100):,.2f}"

        full_context = f"Quarterly Focus: {q_context}. {fin_context}."
        
        # Get Agent Response
        with st.spinner(f"{agent_role} is thinking..."):
            response = agent.chat_with_board(agent_role, prompt, full_context)
        
        # Add assistant message
        st.session_state.chat_history.append({"role": "assistant", "name": agent_role, "content": response})

    # Render History
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            # Different avatars for roles?
            name = msg.get("name", "AI")
            avatar = "👔" if "Strategic" in name or "CEO" in name else "⚙️" if "Operational" in name or "COO" in name else "📢"
            if "Chairman" in name: avatar = "🏛️"
            with st.chat_message("assistant", avatar=avatar):
                st.markdown(f"**{name}:**")
                st.write(msg["content"])


# --- UI: Marketing Lab ---
def render_marketing_lab():
    st.title("🧪 The Marketing Lab")
    st.markdown("*> People don't buy the best products. They buy the products they understand the fastest. - Donald Miller*")
    
    # 1. Fetch Context
    active_q = database.get_active_quarterly_goal(USER_ID)
    if active_q:
        q_context = active_q['description']
        st.info(f"**Campaign Strategy:** {q_context}")
    else:
        st.warning("No Active Quarterly Strategy found. The CMO will fly blind.")
        q_context = "General Real Estate Growth"
        
    # 2. Generator Interface
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Asset Brief")
        asset_type = st.selectbox("Asset Type", ["Cold Email", "Loom Script", "LinkedIn Post"])
        topic = st.text_input("Topic / Angle", placeholder="e.g. Price reduction, Vacant home...")
        
    with col2:
        st.subheader("Listing / Property Context")
        listing_text = st.text_area("Paste Zillow Description (or Property notes)", height=150, 
            placeholder="Beautiful 3bd/2ba in downtown... (Paste details here)")
            
    if st.button(f"Generate {asset_type} Draft"):
        if not topic:
            st.error("Please provide a topic.")
        else:
            with st.spinner("CMO is applying the StoryBrand Framework..."):
                draft = agent.ask_cmo(q_context, asset_type, topic, listing_text)
                st.session_state.current_draft = {
                    "type": asset_type,
                    "topic": topic,
                    "listing": listing_text,
                    "content": draft
                }
    
    # 3. View & Save
    if "current_draft" in st.session_state:
        draft = st.session_state.current_draft
        st.markdown("---")
        st.subheader("📝 Generated Draft")
        
        st.markdown(draft["content"])
        
        if st.button("Save to Asset Library"):
            res = database.save_marketing_asset(
                USER_ID, 
                draft['type'], 
                draft['topic'], 
                draft['listing'], 
                draft['content']
            )
            if res:
                st.success("Asset Saved!")
                # Clear state to restart? Optional.
            else:
                st.error("Failed to save.")

    # 4. Library (Recent)
    st.markdown("---")
    st.subheader("📚 Asset Library (Recent)")
    assets = database.get_marketing_assets(USER_ID)
    if assets:
        for a in assets:
            with st.expander(f"{a['asset_type']}: {a['topic']} ({a['created_at'][:10]})"):
                st.markdown(a['content'])
    else:
        st.caption("No saved assets yet.")


# --- Main App ---
def main():
    st.set_page_config(page_title="Focus Flow: CEO Edition", page_icon="🧘", layout="wide")
    
    # Sidebar Navigation
    # Main Routing
    menu = ["Daily Ritual", "Weekly Strategy", "The War Room", "Sunday Review", "Board Room Chat"]
    choice = st.sidebar.selectbox("Navigation", menu)

    if choice == "Daily Ritual":
        render_daily_ritual()
    elif choice == "Weekly Strategy":
        render_weekly_strategy()
    elif choice == "The War Room":
        render_war_room()
    elif choice == "Sunday Review":
        render_sunday_review()
    elif choice == "Board Room Chat":
        render_board_room()
    else:
        render_daily_ritual()

if __name__ == "__main__":
    main()
