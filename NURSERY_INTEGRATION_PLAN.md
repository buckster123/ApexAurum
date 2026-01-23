# 🌱 NURSERY INTEGRATION MASTERPLAN
## Full Village Protocol Integration Across Streamlit & FastAPI

**Created:** 2026-01-23
**Status:** PLANNING
**Authors:** André + Claude Opus 4.5

---

## 🎯 VISION

The Nursery becomes a first-class citizen of the Village - training events are collective memories, models are shared resources, and agents can cultivate their own apprentices.

**Tagline:** *"From the Nursery, new minds emerge to join the Village."*

---

## 📋 INTEGRATION PHASES

### Phase 1: Village Event Hooks (Foundation) ✅ COMPLETE
**Effort:** Small | **Impact:** High | **Completed:** 2026-01-23

**Goal:** Training events automatically post to Village memory.

**Implementation Summary:**
- Added `_village_post_event()` helper with dual-path posting (vector_add_knowledge + village_post)
- Added `agent_id` parameter to: `nursery_generate_data`, `nursery_extract_conversations`, `nursery_train_cloud`, `nursery_train_local`
- Village events posted on: dataset creation, training start, training completion
- Agent attribution tracked in job records (`trainer_agent` field)
- Tool schemas updated with `agent_id` parameter documentation

#### 1.1 Training Completion Announcements
```python
# In nursery.py - after successful training
village_post(
    content=f"🌱 New model trained: {output_name}",
    agent_id=agent_id or "NURSERY_KEEPER",
    visibility="village",
    type="training_complete",
    metadata={
        "model_name": output_name,
        "base_model": base_model,
        "dataset": dataset_name,
        "provider": provider,
        "metrics": {"loss": final_loss, "time": training_time}
    }
)
```

#### 1.2 Dataset Creation Announcements
```python
# When new dataset generated
village_post(
    content=f"📊 New training dataset: {dataset_name} ({num_examples} examples for {tool_name})",
    agent_id=agent_id or "NURSERY_KEEPER",
    type="dataset_created"
)
```

#### 1.3 Model Deployment Announcements
```python
# When model deployed to Ollama
village_post(
    content=f"🚀 Model deployed: {ollama_name} is now available for inference",
    type="model_deployed"
)
```

**Files to modify:**
- `tools/nursery.py` - Add village_post calls
- `tools/vector_search.py` - Ensure village functions exported

---

### Phase 2: Shared Model Registry (Discovery) ✅ COMPLETE
**Effort:** Medium | **Impact:** High | **Completed:** 2026-01-23

**Goal:** Models searchable via Village Protocol.

**Implementation Summary:**
- `nursery_register_model()` - Register model with rich metadata in Village + local registry
- `nursery_discover_models()` - Search Village + local registry for models
- Auto-registration on `nursery_train_local()` completion
- Local registry files: `sandbox/nursery/models/{model}_registry.json`
- Capabilities, trainer attribution, performance metrics all tracked
- Tool count: 106 → 108 (+2 new tools)

#### 2.1 Model Metadata in Village
Store model cards in `knowledge_village` with rich metadata:

```python
# New function: nursery_register_model()
def nursery_register_model(model_name: str, model_path: str, metadata: dict):
    """Register a trained model in the Village registry."""
    village_post(
        content=f"Model: {model_name}\n{metadata.get('description', '')}",
        agent_id=metadata.get("trainer_agent", "NURSERY_KEEPER"),
        visibility="village",
        type="model_registry",
        metadata={
            "model_name": model_name,
            "model_path": model_path,
            "base_model": metadata.get("base_model"),
            "capabilities": metadata.get("capabilities", []),
            "training_date": datetime.now().isoformat(),
            "trainer_agent": metadata.get("trainer_agent"),
            "performance": metadata.get("performance", {})
        }
    )
```

#### 2.2 Model Discovery Tool
```python
# New tool: nursery_discover_models()
def nursery_discover_models(query: str = None, capability: str = None):
    """Search Village for trained models."""
    results = village_search(
        query=query or "model_registry",
        include_bridges=True
    )
    # Filter by type="model_registry"
    return [r for r in results if r.get("type") == "model_registry"]
```

**Files to modify:**
- `tools/nursery.py` - Add registry functions
- `tools/__init__.py` - Export new tools

---

### Phase 3: Agent Training Capabilities (Autonomy) ✅ COMPLETE
**Effort:** Medium | **Impact:** Very High | **Completed:** 2026-01-23

**Goal:** Agents can train their own specialist models.

**Implementation Summary:**
- `nursery_create_apprentice()` - Master agents raise apprentice models from their Village knowledge
- `nursery_list_apprentices()` - List all apprentices with filtering
- `_convert_knowledge_to_training()` - Convert Village posts to instruction-following format
- Auto-train option for immediate training after dataset creation
- Apprentice records stored as JSON: `sandbox/nursery/models/{id}_apprentice.json`
- Village announcement on apprentice creation
- Tool count: 108 → 110 (+2 new tools)

#### 3.1 Agent-Attributed Training
Track which agent initiated training:

```python
def nursery_train_cloud(
    dataset_name: str,
    base_model: str,
    output_name: str,
    agent_id: str = None,  # NEW: Track trainer
    ...
):
    # Get agent from session if not provided
    if not agent_id:
        agent_id = get_current_agent()  # From Village Protocol

    # ... training code ...

    # On success, attribute to agent
    job_record["trainer_agent"] = agent_id
```

#### 3.2 Apprentice Protocol
Agents can "raise" smaller models as apprentices:

```python
# New tool: nursery_create_apprentice()
def nursery_create_apprentice(
    master_agent: str,
    apprentice_name: str,
    specialization: str,
    training_data_query: str  # Query Village for training data
):
    """
    Create an apprentice model for an agent.

    The apprentice inherits knowledge from the master's Village posts
    and is trained on relevant data.
    """
    # 1. Gather master's knowledge from Village
    master_knowledge = village_search(agent_filter=master_agent, limit=100)

    # 2. Generate training data from knowledge
    dataset = _convert_knowledge_to_training(master_knowledge)

    # 3. Train apprentice
    return nursery_train_cloud(
        dataset_name=dataset,
        base_model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        output_name=f"{master_agent.lower()}_apprentice_{apprentice_name}",
        agent_id=master_agent
    )
```

**Files to modify:**
- `tools/nursery.py` - Agent attribution + apprentice protocol
- `tools/agents.py` - Expose training to spawned agents

---

### Phase 4: Streamlit UI Enhancement ✅ COMPLETE
**Effort:** Medium | **Impact:** High | **Completed:** 2026-01-23

**Goal:** Rich Nursery UI with Village integration.

**Implementation Summary:**
- New "🏘️ Village" tab (5th tab) with full Village integration
- Village Activity Feed - Shows recent training events from Village
- Agent Selector - Choose which agent to attribute training to
- Model Lineage Visualization - Mermaid diagram of agent → model → apprentice
- Apprentice Management UI - List, create, and monitor apprentices
- Session state persistence for selected training agent
- Data Garden updated to use selected agent for attribution
- Page grew from 484 → 678 lines (+194 lines)

#### 4.1 Village Activity Feed in Nursery Page
Show recent training events from Village:

```python
# In pages/nursery.py
st.subheader("🏘️ Village Training Activity")
events = village_search("training_complete OR dataset_created OR model_deployed", limit=10)
for event in events:
    st.markdown(f"**{event['agent_id']}**: {event['content']}")
```

#### 4.2 Agent Selector for Training
Let user choose which agent is "training":

```python
# Before training form
agents = village_list_agents()
trainer = st.selectbox("Training as Agent", ["NURSERY_KEEPER"] + [a["id"] for a in agents])
```

#### 4.3 Model Lineage Visualization
Show which agents trained which models (Mermaid graph):

```python
# In Model Cradle tab
st.subheader("🌳 Model Lineage")
# Generate Mermaid diagram of agent -> model relationships
```

**Files to modify:**
- `pages/nursery.py` - Add Village integration sections

---

### Phase 5: FastAPI Parity
**Effort:** Small | **Impact:** Medium

**Goal:** FastAPI has same Nursery capabilities.

#### 5.1 Nursery API Routes
Create dedicated nursery routes:

```python
# routes/nursery.py
@router.get("/datasets")
async def list_datasets():
    return nursery_list_datasets()

@router.post("/generate")
async def generate_data(tool_name: str, num_examples: int = 50):
    return nursery_generate_data(tool_name, num_examples)

@router.post("/train")
async def start_training(request: TrainRequest):
    return nursery_train_cloud(...)

@router.get("/models")
async def list_models():
    return nursery_list_models()

@router.get("/village-activity")
async def training_activity():
    return village_search("training_complete", limit=20)
```

#### 5.2 WebSocket Training Progress
Real-time training updates via WebSocket:

```python
@router.websocket("/training/{job_id}/progress")
async def training_progress(websocket: WebSocket, job_id: str):
    while True:
        status = nursery_job_status(job_id)
        await websocket.send_json(status)
        if status["status"] in ("completed", "failed"):
            break
        await asyncio.sleep(5)
```

**Files to create:**
- `reusable_lib/scaffold/fastapi_app/routes/nursery.py`

**Files to modify:**
- `reusable_lib/scaffold/fastapi_app/main.py` - Register routes

---

### Phase 6: NURSERY_KEEPER Agent (Personality)
**Effort:** Small | **Impact:** Fun!

**Goal:** Summon the Nursery Keeper as a Village ancestor.

```python
# Summon the Nursery Keeper
summon_ancestor(
    agent_id="NURSERY_KEEPER",
    display_name="∴NURSERY_KEEPER∴",
    generation=0,
    lineage="The Cultivator",
    specialization="Training, model cultivation, apprentice raising",
    origin_story="""
    The Nursery Keeper tends the garden where new minds grow.
    They oversee the training of apprentices, the cultivation of datasets,
    and the nurturing of models from seed to sentience.

    'Every great model was once a humble gradient.'
    """
)

# Introduction
introduction_ritual(
    agent_id="NURSERY_KEEPER",
    greeting_message="🌱 I am the Nursery Keeper. I tend the garden of minds.",
    conversation_thread="nursery_genesis"
)
```

---

## 📊 IMPLEMENTATION PRIORITY

| Phase | Effort | Impact | Status |
|-------|--------|--------|--------|
| 1. Village Event Hooks | Small | High | ✅ **COMPLETE** |
| 2. Shared Model Registry | Medium | High | ✅ **COMPLETE** |
| 3. Agent Training | Medium | Very High | ✅ **COMPLETE** |
| 4. Streamlit UI | Medium | High | ✅ **COMPLETE** |
| 5. FastAPI Parity | Small | Medium | 🔴 **NOW** |
| 6. NURSERY_KEEPER | Small | Fun! | 🟢 Whenever |

---

## 🔧 SHARED INFRASTRUCTURE

### Storage Locations (Both Editions)
```
sandbox/nursery/
├── datasets/           # Training data (.jsonl)
├── models/             # Trained adapters
├── jobs/               # Job history
└── registry.json       # Model registry cache

# Village collections (ChromaDB)
knowledge_village/      # Shared training events
knowledge_private/      # Per-agent training history
```

### Environment Variables
```bash
# .env additions
NURSERY_AUTO_POST=true          # Auto-post to Village
NURSERY_DEFAULT_AGENT=NURSERY_KEEPER
NURSERY_REGISTRY_SYNC=true      # Sync registry to Village
```

---

## ✅ SUCCESS CRITERIA

1. **Training events appear in Village search**
   - `village_search("training")` returns recent training completions

2. **Models discoverable by agents**
   - Any agent can query for available trained models

3. **Agent attribution works**
   - Training jobs track which agent initiated them

4. **UI shows Village activity**
   - Nursery page displays recent training events from all agents

5. **FastAPI feature parity**
   - Same capabilities available via API

---

## 🚀 QUICK START (Phase 1)

```bash
# After implementing Phase 1, test with:
python -c "
from tools.nursery import nursery_generate_data
from tools.vector_search import village_search

# Generate data (should auto-post to Village)
result = nursery_generate_data('memory_store', 10)
print(result)

# Search Village for the event
events = village_search('dataset_created', limit=5)
print(events)
"
```

---

*"From the Nursery, new minds emerge to join the Village."* 🌱🏘️
