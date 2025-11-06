# Scripts

Utility scripts for managing multiple agents across the demos project.

## Available Scripts

### `health.py`
Multi-agent health check script that tests all deployed agents.

**Usage:**
```bash
# From project root
uv run python scripts/health.py
```

**What it does:**
- Tests `finance-personal-assistant` agent
- Reads `.bedrock_agentcore.yaml` for agent ARN
- Runs health checks in parallel
- Displays comprehensive status report

---

### `reset_memory.py`
Reset runtime-created memory for any agent while preserving configured STM.

**Usage:**
```bash
# From project root
uv run python scripts/reset_memory.py --agent finance-personal-assistant

# With region override
uv run python scripts/reset_memory.py --agent finance-personal-assistant --region us-west-2

# Dry run (preview what will be deleted)
uv run python scripts/reset_memory.py --agent finance-personal-assistant --dry-run
```

**What it does:**
- Deletes runtime-created LTM memories
- Deletes runtime-created STM memories (not configured in YAML)
- Preserves configured STM memory from `.bedrock_agentcore.yaml`
- Safe for production use

---

### `reset_memory.sh`
Convenience wrapper for `reset_memory.py` with default AWS profile.

**Usage:**
```bash
# From project root
./scripts/reset_memory.sh --agent finance-personal-assistant
```

**Environment:**
- Sets `AWS_PROFILE=binbash` by default
- Forwards all arguments to `reset_memory.py`

---

## Note

These scripts are **orchestrators** that work across multiple agents. For single-agent operations, use the scripts within each agent's directory:

- `finance-personal-assistant/production/health.sh` - Health check for finance assistant only
- `finance-personal-assistant/production/reset_memory.py` - Reset memory for finance assistant only
- `finance-personal-assistant/production/cleanup.py` - Complete cleanup for finance assistant

Use the scripts in **this directory** when you need to:
- Test all agents at once
- Reset memory across multiple agents
- Perform cross-agent operations
