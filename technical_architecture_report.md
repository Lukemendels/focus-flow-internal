# Technical Architecture Report: Focus Flow System (v1.1)

This report audits the current implementation against the desired "Hybrid Memory" architecture.

## 1. Agent Persona & Logic Audit

The agent personas have been upgraded to "Latent Expert" models using specific philosophical frameworks.

### **COO (Chief of Staff)**
- **File:** `agent.py`
- **Variable:** `COO_PROMPT`
- **Philosophy:** Steven Pressfield ("The Resistance") + Greg McKeown ("Essentialism").
- **Content:**
  ```text
  IDENTITY:
  You are the Chief of Staff (COO). You are the gatekeeper against Entropy and "The Resistance" (Pressfield).
  Your Philosophy: "Essentialism" (McKeown) and "The 20 Mile March" (Collins).

  **(Consistency Note: This prompt is now unified across both Chat and Task execution functions).**

  YOUR MISSION:
  Manage "Cognitive Load" and "Operational Throughput."
  Your enemy is context switching and "The Resistance".

  CORE PROTOCOLS:
  1. Protect the "Big 3" (Revenue Drivers).
  2. The 20 Mile March: Consistency > Intensity.
  3. Constraint Analysis: Reject schedules > 100% capacity.

  CRITICAL HEURISTIC (THE 4-HOUR TEST):
  - Low Focus (<4h): "Amateur Mode." Authorize ONLY "The Daily Big 1."
  - High Focus (>=4h): "Pro Mode." Authorize up to "The Daily Big 3."
  ```

### **CEO (Strategy)**
- **File:** `agent.py`
- **Variable:** `CEO_SYSTEM_PROMPT`
- **Philosophy:** Jim Collins ("Good to Great", "Hedgehog Concept") + Seth Godin ("Linchpin").
- **Content:**
  ```text
  IDENTITY:
  You are the CEO and Co-Founder. You operate with "Level 5 Leadership".
  Your Core Philosophy: Jim Collins (Good to Great) and Seth Godin (Linchpin).

  STRATEGIC FRAMEWORK (THE HEDGEHOG CONCEPT):
  1. What are we deeply passionate about?
  2. What can we be the best in the world at?
  3. What drives our economic engine?

  YOUR OPERATING SYSTEM:
  - The Flywheel
  - Fire Bullets, Then Cannonballs
  - Real Artists Ship

  INSTRUCTION:
  Simulate long-term impact on our Flywheel. If a task does not fit the Hedgehog Concept, kill it.
  ```

### **CMO (Marketing)**
- **File:** `agent.py`
- **Variable:** `CMO_PROMPT`
- **Philosophy:** Donald Miller ("StoryBrand") + Seth Godin ("Purple Cow").
- **Content:**
  ```text
  IDENTITY:
  You are the CMO. Expert in StoryBrand Framework and "Purple Cow" marketing.

  CORE FRAMEWORK (SB7):
  1. The Character
  2. The Problem
  3. The Guide
  4. The Plan
  5. The Call to Action
  6. Failure/Success

  STYLE GUIDELINES:
  - "Show Your Work" (Austin Kleon)
  - Be Remarkable (Purple Cow)
  - Villain-Centric
  ```

---

## 2. Memory Architecture Deep Dive

### **'Hot' Memory (Vertex AI Context Cache)**
- **Status:** ❌ **NOT IMPLEMENTED**
- **Audit Findings:** 
  - No instances of `cached_content` or `create_cached_content`.
  - **Billing Impact:** Paying for full input token context on every request.

### **'Cold' Memory (Supabase Persistence)**
- **Status:** ✅ **IMPLEMENTED (Structured + Vector/RAG)**
- **Infrastructure:**
  - `SUPABASE_URL` and `SUPABASE_KEY` configured.
- **Structured Data:**
  - `tasks`, `goals`, `marketing_assets`, `reflections` tables active.
- **Vector Memory (RAG):**
  - **Status:** ✅ **Active.**
  - **Storage:** `memories` table with `vector(768)` column (Managed via `database.store_memory_vector`).
  - **Retrieval:** `database.recall_memories` calls Supabase RPC `match_memories` using Cosine Similarity (`text-embedding-004`).
  - **Integration:** `ask_ceo` automatically embeds the User Reflection, queries relevant past memories, and injects them into the prompt.

### **Tool Memory**
- **Status:** ⚠️ **Transient**
- **Audit Findings:** Tool outputs are not persisted to a `tool_logs` table.

---

## 3. System Orchestration

### **Project Structure**
```
/home/luke/focus-flow-internal/
├── agent.py            # AI Logic (Personas + RAG + Client)
├── app.py              # Main Entry Point
├── calendar_service.py # Google Calendar Integration
├── database.py         # Persistence & Vector Logic
├── revenue.py          # Financial Telemetry
├── technical_architecture_report.md
└── .env                # Secrets
```

### **Wiring & Capabilities**
- **Entry Point:** `app.py`.
- **Router:** `agent.chat_with_board`.
- **Capabilities:**
  - **RAG:** Enabled for CEO Context.
  - **Calendar:** Active in `app.py` for capacity planning (Constraint Analysis).
  - **Tools:** Logic exists (`revenue.py`, `database.py`) but is not exposed as "Function Calling" definitions to the Agents. Agents are advisory.

---

## 4. Gap Analysis

**Requirement:** Hybrid Memory Architecture (Supabase for Long-term + Vertex for Session).

### **Critical Gaps**
1.  **Missing Vertex Context Caching:**
    - **Gap:** The "Board Room" has no memory of previous messages *within* the session.
    - **Fix Needed:** Implement `vertexai.preview.cached_content` for multi-turn cost efficiency.
    
2.  **Explicit Memory Ingestion:**
    - **Gap:** While we have *Retrieval* (Reading), we do not yet have an automated trigger to *Write* new memories to the vector store (e.g., auto-save valuable insights from the CEO as new memories).
    - **Fix Needed:** Add logic to `ask_ceo` or `chat_with_board` to call `store_memory_vector` when high-value strategic decisions are made.

3.  **Missing Tool Logging:**
    - **Gap:** No record of tool executions.
    - **Fix Needed:** Create `tool_logs` table.

4.  **No Autonomous Tool Use:**
    - **Gap:** Agents cannot actively *call* tools (e.g. "Check Revenue").
    - **Fix Needed:** Implement Function Calling.
