# Technical Architecture Report: Focus Flow System (v2.0 - Mendelsohn Kernel Standard)

This report audits the current implementation against the desired "Hybrid Memory" architecture.

## 1. Agent Persona & Logic Audit

The agent personas have been migrated from hardcoded Python variables to a **Dynamic Kernel Registry** stored in Supabase (M mendelsohn Kernel Standard v1.1).

### **Kernel 1: The Chairman (Router)**
- **Role:** Orchestration Layer.
- **Function:** Classifies intent and routes to the correct Expert Kernel.
- **Source:** SQL `kernels` table.

### **Kernel 2: Operational Commander (COO)**
- **Role:** Execution Engine.
- **Philosophy:** "Extreme Ownership" + "Essentialism".
- **Logic Gates:** PARETO_PRINCIPLE, CONSTRAINT_ANALYSIS.

### **Kernel 3: Strategic Architect (CEO)**
- **Role:** Strategy Engine.
- **Philosophy:** "Infinite Game" + "Hedgehog Concept".
- **Logic Gates:** TIME_HORIZON_CHECK, FIRST_WHO.

### **Kernel 4: Market Alchemist (CMO)**
- **Role:** Narrative Engine.
- **Philosophy:** "StoryBrand" + "Purple Cow".
- **Logic Gates:** HERO_INVERSION, REMARKABILITY_CHECK.

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

### **Tool Memory (Kernel Logs)**
- **Status:** ✅ **IMPLEMENTED**
- **Infrastructure:** `kernel_logs` table.
- **Function:** Tracks `user_input`, `logic_trace`, and `output` for every kernel interaction to enable hallucination auditing.

---

## 3. System Orchestration

### **Project Structure**
```
/home/luke/focus-flow-internal/
├── agent.py            # AI Logic (MKS Client)
├── app.py              # Main Entry Point (Frontend)
├── kernel_manager.py   # Dynamic Registry Interface [NEW]
├── calendar_service.py # Google Calendar Integration
├── database.py         # Persistence & Vector Logic
├── revenue.py          # Financial Telemetry
├── technical_architecture_report.md
├── mks_schema.sql      # Database Schema (Source of Truth)
├── seed_*.sql          # Kernel DNA Seeds
└── .env                # Secrets
```

### **Wiring & Capabilities**
- **Entry Point:** `app.py` initializes `kernel_manager` to fetch Active Kernels for Sidebar.
- **Orchestration:** `agent.py` imports `kernel_manager` to fetch `system_prompt` at runtime.
- **Capabilities:**
  - **Dynamic Personality:** Agents can be updated via SQL without redeploying code.
  - **RAG:** Enabled for CEO Context.
  - **Calendar:** Active in `app.py`.
  - **Audit Logging:** All interactions logged to `kernel_logs`.

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

3.  **Missing Vertex Context Caching:**
    - **Gap:** The "Board Room" has no memory of previous messages *within* the session.
    - **Fix Needed:** Implement `vertexai.preview.cached_content` for multi-turn cost efficiency.

4.  **No Autonomous Tool Use:**
    - **Gap:** Agents cannot actively *call* tools (e.g. "Check Revenue").
    - **Fix Needed:** Implement Function Calling.
