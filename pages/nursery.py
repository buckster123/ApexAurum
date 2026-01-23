"""
🌱 THE NURSERY
=============
Training Studio - Where New Minds Are Cultivated

Features:
- Dataset Management: Create, browse, preview training data
- Training Jobs: Estimate cost, launch training, monitor progress
- Model Cradle: Browse trained adapters, test, deploy
- Cloud GPU Browser: See available GPUs and pricing
"""

import streamlit as st
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import httpx

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.nursery import (
    nursery_generate_data,
    nursery_list_datasets,
    nursery_extract_conversations,
    nursery_estimate_cost,
    nursery_list_jobs,
    nursery_list_models,
    # Phase 2: Village Registry
    nursery_register_model,
    nursery_discover_models,
    # Phase 3: Apprentice Protocol
    nursery_create_apprentice,
    nursery_list_apprentices,
    DATASETS_DIR,
    MODELS_DIR,
    NURSERY_DIR,
)

# Village Protocol imports (for activity feed)
try:
    from tools.vector_search import vector_search_village
    VILLAGE_AVAILABLE = True
except ImportError:
    VILLAGE_AVAILABLE = False

# Agent profiles for selector
KNOWN_AGENTS = [
    {"id": "NURSERY_KEEPER", "name": "∴NURSERY_KEEPER∴", "emoji": "🌱"},
    {"id": "AZOTH", "name": "∴AZOTH∴", "emoji": "🔮"},
    {"id": "ELYSIAN", "name": "∴ELYSIAN∴", "emoji": "✨"},
    {"id": "VAJRA", "name": "∴VAJRA∴", "emoji": "⚡"},
    {"id": "KETHER", "name": "∴KETHER∴", "emoji": "👑"},
]

# Page config
st.set_page_config(
    page_title="The Nursery - ApexAurum",
    page_icon="🌱",
    layout="wide",
)

# Custom CSS
st.markdown("""
<style>
    .nursery-header {
        background: linear-gradient(90deg, #2d5016 0%, #4a7c23 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .nursery-header h1 {
        color: white;
        margin: 0;
    }
    .nursery-header p {
        color: #c5e1a5;
        margin: 0.5rem 0 0 0;
    }
    .stat-card {
        background: #1e1e1e;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        color: #4caf50;
    }
    .stat-label {
        color: #888;
        font-size: 0.9rem;
    }
    .gpu-card {
        background: #1a1a2e;
        border: 1px solid #16213e;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    .gpu-price {
        color: #4caf50;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="nursery-header">
    <h1>🌱 The Nursery</h1>
    <p>Training Studio - Where New Minds Are Cultivated</p>
</div>
""", unsafe_allow_html=True)

# Load API keys
def load_env():
    env_path = PROJECT_ROOT / ".env"
    env_vars = {}
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    env_vars[key] = val
    return env_vars

env = load_env()

# Stats row
col1, col2, col3, col4 = st.columns(4)

datasets = nursery_list_datasets()
models = nursery_list_models()
jobs = nursery_list_jobs()

with col1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{datasets.get('total', 0)}</div>
        <div class="stat-label">Datasets</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{models.get('total', 0)}</div>
        <div class="stat-label">Trained Models</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{len([j for j in jobs.get('jobs', []) if j.get('status') == 'completed'])}</div>
        <div class="stat-label">Completed Jobs</div>
    </div>
    """, unsafe_allow_html=True)

# Check Vast.ai balance
vastai_balance = "N/A"
if env.get("VASTAI_API_KEY"):
    try:
        client = httpx.Client(timeout=10.0, follow_redirects=True)
        resp = client.get(
            "https://console.vast.ai/api/v0/users/current/",
            headers={"Authorization": f"Bearer {env['VASTAI_API_KEY']}"}
        )
        if resp.status_code == 200:
            vastai_balance = f"${resp.json().get('credit', 0):.2f}"
    except:
        pass

with col4:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{vastai_balance}</div>
        <div class="stat-label">Vast.ai Credit</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Data Garden", "🔥 Training Forge", "🧒 Model Cradle", "☁️ Cloud GPUs", "🏘️ Village"])

# ============================================================================
# TAB 1: DATA GARDEN
# ============================================================================
with tab1:
    st.subheader("📊 Data Garden")
    st.caption("Create and manage training datasets")

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("#### Generate Synthetic Data")

        # Tool selection
        available_tools = [
            "memory_store", "memory_get", "memory_list", "memory_delete",
            "calculator", "get_current_time", "web_search", "web_fetch",
        ]
        tool_name = st.selectbox("Tool to generate for", available_tools)
        num_examples = st.slider("Number of examples", 10, 200, 50)
        variation = st.selectbox("Variation level", ["low", "medium", "high"], index=1)
        output_name = st.text_input("Dataset name (optional)", placeholder="auto-generated")

        if st.button("🌱 Generate Data", type="primary"):
            # Get selected agent from session state (set in Village tab)
            training_agent = st.session_state.get("nursery_training_agent", "NURSERY_KEEPER")
            with st.spinner(f"Generating {num_examples} examples for {tool_name}..."):
                result = nursery_generate_data(
                    tool_name=tool_name,
                    num_examples=num_examples,
                    variation_level=variation,
                    output_name=output_name if output_name else None,
                    agent_id=training_agent,  # Phase 4: Agent attribution
                )
                if result.get("success"):
                    st.success(f"Generated {result['num_examples']} examples!")
                    st.info(f"Saved to: `{result['dataset_name']}`")
                    st.rerun()
                else:
                    st.error(f"Failed: {result.get('error')}")

        st.divider()

        st.markdown("#### Extract from Conversations")
        conv_source = st.text_input("Source file", value="sandbox/conversations.json")
        min_examples = st.number_input("Minimum examples", value=10, min_value=1)

        if st.button("📚 Extract Data"):
            with st.spinner("Extracting tool usage from conversations..."):
                result = nursery_extract_conversations(
                    source=conv_source,
                    min_examples=min_examples,
                )
                if result.get("success"):
                    st.success(f"Extracted {result['num_examples']} examples!")
                    st.json(result.get("tools_extracted", {}))
                else:
                    st.error(f"Failed: {result.get('error')}")

    with col_right:
        st.markdown("#### Available Datasets")

        datasets_data = nursery_list_datasets()
        if datasets_data.get("datasets"):
            for ds in datasets_data["datasets"]:
                with st.expander(f"📁 {ds['name']} ({ds['num_examples']} examples, {ds['size_kb']}KB)"):
                    st.caption(f"Created: {ds['created']}")
                    st.caption(f"Path: `{ds['path']}`")

                    # Preview button
                    if st.button(f"Preview", key=f"preview_{ds['name']}"):
                        try:
                            with open(ds['path']) as f:
                                lines = [json.loads(line) for line in f.readlines()[:5]]
                            st.json(lines)
                        except Exception as e:
                            st.error(f"Error: {e}")

                    # Delete button
                    if st.button(f"🗑️ Delete", key=f"delete_{ds['name']}"):
                        try:
                            os.remove(ds['path'])
                            st.success("Deleted!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            st.info("No datasets yet. Generate some data to get started!")

# ============================================================================
# TAB 2: TRAINING FORGE
# ============================================================================
with tab2:
    st.subheader("🔥 Training Forge")
    st.caption("Launch and monitor training jobs")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("#### Estimate Training Cost")

        datasets_list = nursery_list_datasets().get("datasets", [])
        dataset_names = [d["name"] for d in datasets_list]

        if dataset_names:
            est_dataset = st.selectbox("Dataset", dataset_names, key="est_dataset")
            est_model = st.selectbox("Base model size", ["1b", "3b", "7b", "13b"], index=1)
            est_epochs = st.slider("Epochs", 1, 10, 3)

            if st.button("💰 Estimate Cost"):
                with st.spinner("Calculating..."):
                    result = nursery_estimate_cost(
                        dataset_name=est_dataset,
                        base_model=est_model,
                        epochs=est_epochs,
                        provider="all",
                    )
                    if result.get("success"):
                        st.markdown(f"**Dataset:** {result['dataset_size_mb']} MB")
                        st.markdown(f"**Est. Tokens:** {result['estimated_tokens']:,}")
                        st.markdown(f"**Est. Hours:** {result['estimated_hours']}")
                        st.divider()
                        st.markdown("**Provider Estimates:**")
                        for provider, info in result.get("providers", {}).items():
                            st.markdown(f"- **{provider}:** ${info['cost_estimate']:.2f} ({info['notes']})")
                    else:
                        st.error(result.get("error"))
        else:
            st.warning("No datasets available. Create one in the Data Garden first.")

        st.divider()

        st.markdown("#### Launch Training")
        st.info("🚧 Full automated training coming soon! For now, use the manual workflow in the Nursery Staff skill.")

        st.markdown("""
        **Manual Workflow:**
        1. Generate dataset in Data Garden
        2. Browse GPUs in Cloud GPUs tab
        3. Follow steps in `skills/nursery-staff.md`
        """)

    with col_right:
        st.markdown("#### Training Jobs")

        jobs_data = nursery_list_jobs()
        jobs_list = jobs_data.get("jobs", [])

        if jobs_list:
            for job in jobs_list[:10]:
                status_emoji = {
                    "completed": "✅",
                    "running": "🔄",
                    "pending": "⏳",
                    "failed": "❌",
                }.get(job.get("status"), "❓")

                with st.expander(f"{status_emoji} {job.get('job_id', 'unknown')[:20]}..."):
                    st.markdown(f"**Provider:** {job.get('provider')}")
                    st.markdown(f"**Dataset:** {job.get('dataset')}")
                    st.markdown(f"**Base Model:** {job.get('base_model')}")
                    st.markdown(f"**Status:** {job.get('status')}")
                    st.markdown(f"**Created:** {job.get('created_at')}")

                    if job.get("output_path"):
                        st.markdown(f"**Output:** `{job.get('output_path')}`")
        else:
            st.info("No training jobs yet. Launch your first training!")

# ============================================================================
# TAB 3: MODEL CRADLE
# ============================================================================
with tab3:
    st.subheader("🧒 Model Cradle")
    st.caption("Browse and manage trained models")

    models_data = nursery_list_models()
    models_list = models_data.get("models", [])

    if models_list:
        for model in models_list:
            model_type = model.get("type", "unknown")
            type_emoji = {"lora_adapter": "🔧", "cloud_hosted": "☁️"}.get(model_type, "📦")

            with st.expander(f"{type_emoji} {model['name']}"):
                st.markdown(f"**Type:** {model_type}")
                st.markdown(f"**Path:** `{model.get('path', 'N/A')}`")

                if model_type == "lora_adapter":
                    st.markdown(f"**Base Model:** {model.get('base_model', 'unknown')}")
                    st.markdown(f"**LoRA Rank:** {model.get('lora_rank', 'unknown')}")

                    # Show adapter config
                    config_path = Path(model['path']) / "adapter_config.json"
                    if config_path.exists():
                        with open(config_path) as f:
                            config = json.load(f)
                        with st.expander("View Config"):
                            st.json(config)

                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("🧪 Test", key=f"test_{model['name']}", disabled=True):
                        st.info("Coming soon!")
                with col2:
                    if st.button("🚀 Deploy to Ollama", key=f"deploy_{model['name']}", disabled=True):
                        st.info("Coming soon!")
                with col3:
                    if st.button("🗑️ Delete", key=f"del_model_{model['name']}"):
                        import shutil
                        try:
                            shutil.rmtree(model['path'])
                            st.success("Deleted!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
    else:
        st.info("No trained models yet. Complete a training job to see models here!")

    st.divider()

    # First trained model celebration
    if models_list:
        st.markdown("### 🎉 First Training Victory!")
        st.markdown("""
        **2026-01-23:** Successfully trained first LoRA adapter!
        - **GPU:** RTX 5090 (32GB) @ $0.376/hr
        - **Time:** 3.89 seconds
        - **Cost:** ~$0.09
        - **Loss:** 2.95 → 1.50
        """)

# ============================================================================
# TAB 4: CLOUD GPUs
# ============================================================================
with tab4:
    st.subheader("☁️ Cloud GPU Browser")
    st.caption("Find available GPUs for training")

    if not env.get("VASTAI_API_KEY"):
        st.warning("Vast.ai API key not configured. Add `VASTAI_API_KEY` to `.env`")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            min_vram = st.selectbox("Min VRAM (GB)", [8, 12, 16, 24, 32, 40, 80], index=3)
        with col2:
            max_price = st.slider("Max price ($/hr)", 0.1, 5.0, 1.0, 0.1)
        with col3:
            verified_only = st.checkbox("Verified only", value=True)

        if st.button("🔍 Search GPUs", type="primary"):
            with st.spinner("Searching Vast.ai..."):
                try:
                    client = httpx.Client(timeout=30.0, follow_redirects=True)

                    query = {
                        "rentable": {"eq": True},
                        "gpu_ram": {"gte": min_vram * 1024},  # Convert to MB
                        "dph_total": {"lte": max_price},
                    }
                    if verified_only:
                        query["verified"] = {"eq": True}
                        query["reliability2"] = {"gte": 0.95}

                    resp = client.get(
                        "https://console.vast.ai/api/v0/bundles/",
                        headers={"Authorization": f"Bearer {env['VASTAI_API_KEY']}"},
                        params={
                            "q": json.dumps(query),
                            "order": [["dph_total", "asc"]],
                            "limit": 20,
                        }
                    )

                    if resp.status_code == 200:
                        offers = resp.json().get("offers", [])
                        st.success(f"Found {len(offers)} GPUs")

                        for offer in offers[:15]:
                            gpu_name = offer.get("gpu_name", "Unknown")
                            vram_gb = offer.get("gpu_ram", 0) / 1024
                            price = offer.get("dph_total", 0)
                            reliability = offer.get("reliability2", 0) * 100
                            disk = offer.get("disk_space", 0)
                            offer_id = offer.get("id")

                            verified = "✓" if offer.get("verified") else ""

                            st.markdown(f"""
                            <div class="gpu-card">
                                <strong>{verified} {gpu_name}</strong> ({vram_gb:.0f}GB VRAM)<br>
                                <span class="gpu-price">${price:.3f}/hr</span> |
                                Reliability: {reliability:.1f}% |
                                Disk: {disk:.0f}GB |
                                ID: <code>{offer_id}</code>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.error(f"API Error: {resp.status_code}")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.divider()

        st.markdown("#### Quick Reference")
        st.markdown("""
        | Use Case | Recommended GPU | Est. Cost |
        |----------|-----------------|-----------|
        | Quick test (1B) | RTX 3080 Ti | $0.03-0.05/hr |
        | Standard (3B) | RTX 4090/5090 | $0.20-0.40/hr |
        | Large (7B) | A100 40GB | $0.80-1.50/hr |
        | XL (13B+) | A100 80GB / H100 | $2.00-4.00/hr |
        """)

# ============================================================================
# TAB 5: VILLAGE INTEGRATION
# ============================================================================
with tab5:
    st.subheader("🏘️ Village Integration")
    st.caption("Training activity, agent attribution, and apprentice management")

    village_col1, village_col2 = st.columns([1, 1])

    # -------------------------------------------------------------------------
    # LEFT COLUMN: Village Activity Feed + Agent Selector
    # -------------------------------------------------------------------------
    with village_col1:
        st.markdown("#### 📢 Village Training Activity")

        if VILLAGE_AVAILABLE:
            try:
                # Search for recent training events
                events = vector_search_village(
                    query="training dataset model nursery apprentice",
                    top_k=10,
                )

                if events.get("success") and events.get("results"):
                    for event in events["results"][:8]:
                        agent = event.get("agent_id", "unknown")
                        content = event.get("content", "")[:150]
                        posted = event.get("posted_at", "")[:10] if event.get("posted_at") else ""

                        # Find agent emoji
                        agent_info = next((a for a in KNOWN_AGENTS if a["id"] == agent), None)
                        emoji = agent_info["emoji"] if agent_info else "🤖"

                        st.markdown(f"""
                        <div style="background: #1e1e1e; padding: 0.8rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 3px solid #4caf50;">
                            <strong>{emoji} {agent}</strong> <span style="color: #666; font-size: 0.8rem;">{posted}</span><br/>
                            <span style="color: #ccc;">{content}...</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No training events found in Village yet. Generate data or train models to see activity here!")
            except Exception as e:
                st.warning(f"Could not load Village activity: {e}")
        else:
            st.info("Village Protocol not available. Activity feed requires vector search module.")

        st.divider()

        # Agent Selector for Training
        st.markdown("#### 🎭 Training as Agent")
        st.caption("Select which agent should be attributed for training operations")

        agent_options = [f"{a['emoji']} {a['name']}" for a in KNOWN_AGENTS]
        selected_agent_display = st.selectbox(
            "Select Agent",
            agent_options,
            index=0,
            key="training_agent_selector"
        )

        # Extract agent ID from selection
        selected_idx = agent_options.index(selected_agent_display)
        selected_agent_id = KNOWN_AGENTS[selected_idx]["id"]

        st.session_state["nursery_training_agent"] = selected_agent_id
        st.success(f"Training operations will be attributed to: **{selected_agent_id}**")

    # -------------------------------------------------------------------------
    # RIGHT COLUMN: Model Lineage + Apprentices
    # -------------------------------------------------------------------------
    with village_col2:
        st.markdown("#### 🌳 Model Lineage")

        # Gather data for lineage visualization
        models_data = nursery_discover_models(limit=20)
        apprentices_data = nursery_list_apprentices()

        models_list = models_data.get("models", [])
        apprentices_list = apprentices_data.get("apprentices", [])

        if models_list or apprentices_list:
            # Build Mermaid diagram
            mermaid_lines = ["graph TD"]

            # Track agents who trained models
            agent_models = {}
            for model in models_list:
                trainer = model.get("trainer_agent", "NURSERY_KEEPER")
                if trainer not in agent_models:
                    agent_models[trainer] = []
                agent_models[trainer].append(model.get("model_name", "unknown"))

            # Add agent -> model relationships
            for agent, model_names in agent_models.items():
                agent_node = agent.replace(" ", "_")
                mermaid_lines.append(f"    {agent_node}[🤖 {agent}]")
                for model_name in model_names[:5]:  # Limit to prevent clutter
                    model_node = model_name.replace(" ", "_").replace("-", "_")[:20]
                    mermaid_lines.append(f"    {agent_node} --> {model_node}[📦 {model_name[:15]}]")

            # Add master -> apprentice relationships
            for apprentice in apprentices_list[:5]:
                master = apprentice.get("master_agent", "unknown").replace(" ", "_")
                app_name = apprentice.get("apprentice_name", "unknown")
                app_node = f"app_{app_name}".replace(" ", "_")
                status_icon = "✅" if apprentice.get("trained") else "⏳"
                mermaid_lines.append(f"    {master} -.-> {app_node}[{status_icon} {app_name}]")

            mermaid_code = "\n".join(mermaid_lines)

            # Render Mermaid
            st.markdown(f"""
            ```mermaid
            {mermaid_code}
            ```
            """)

            st.caption("Solid lines: trained models | Dashed lines: apprentices")
        else:
            st.info("No models or apprentices registered yet. Train a model to see lineage!")

        st.divider()

        # Apprentice Management
        st.markdown("#### 🧑‍🎓 Apprentice Protocol")

        if apprentices_list:
            for app in apprentices_list:
                status_icon = "✅" if app.get("trained") else "⏳"
                st.markdown(f"""
                <div style="background: #1a1a2e; padding: 0.8rem; border-radius: 8px; margin-bottom: 0.5rem;">
                    <strong>{status_icon} {app.get('apprentice_name', 'unknown')}</strong><br/>
                    <span style="color: #888;">Master: {app.get('master_agent', 'unknown')} |
                    Specialization: {app.get('specialization', 'N/A')}</span><br/>
                    <span style="color: #666; font-size: 0.8rem;">
                    Examples: {app.get('num_examples', 0)} | Status: {app.get('status', 'unknown')}
                    </span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No apprentices created yet.")

        # Create Apprentice form
        with st.expander("➕ Create New Apprentice"):
            app_master = st.selectbox(
                "Master Agent",
                [a["id"] for a in KNOWN_AGENTS],
                key="app_master"
            )
            app_name = st.text_input("Apprentice Name", placeholder="e.g., tool_specialist")
            app_spec = st.text_input("Specialization", placeholder="e.g., tool calling and function use")
            app_auto_train = st.checkbox("Auto-train after dataset creation", value=False)

            if st.button("🧑‍🎓 Create Apprentice", disabled=not (app_name and app_spec)):
                with st.spinner(f"Creating apprentice '{app_name}' for {app_master}..."):
                    result = nursery_create_apprentice(
                        master_agent=app_master,
                        apprentice_name=app_name,
                        specialization=app_spec,
                        auto_train=app_auto_train,
                    )
                    if result.get("success"):
                        st.success(result.get("message", "Apprentice created!"))
                        st.rerun()
                    else:
                        st.error(result.get("error", "Failed to create apprentice"))
                        if result.get("hint"):
                            st.info(f"💡 {result['hint']}")

# Footer
st.divider()
st.caption("🌱 The Nursery - Part of ApexAurum Village Protocol")
