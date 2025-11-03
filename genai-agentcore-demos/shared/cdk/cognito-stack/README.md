# Shared Cognito User Pool for AgentCore Demos

This CDK stack creates a **single shared Cognito User Pool** for all AgentCore agents.

## Purpose

Enables:
- ✅ **Independent agent deployments** (no deployment order dependency)
- ✅ **Single sign-on** across all agents (one login for all)
- ✅ **Centralized user management** (add users once, access all agents)

## Architecture

```
┌─────────────────────────────────────┐
│  Shared Cognito User Pool          │
│  (deployed once)                    │
│                                     │
│  - Demo users from .demo_users.json│
│  - Pool ID stored in SSM            │
└─────────────────────────────────────┘
              │
              │ SSM: /agentcore/shared/cognito-pool-id
              │
    ┌─────────┴──────────┬─────────────────┐
    │                    │                 │
┌───▼────┐         ┌─────▼──┐        ┌────▼────┐
│Finance │         │Market  │        │Gateway  │
│Agent   │         │Trends  │        │(future) │
└────────┘         └────────┘        └─────────┘
```

## Deployment

### First Time Setup

1. **Add demo users** (optional):
   ```bash
   cp .demo_users.json.example .demo_users.json
   # Edit .demo_users.json with your demo users
   ```

2. **Deploy the stack**:
   ```bash
   ./deploy.sh
   ```

3. **Deploy agents** (any order):
   ```bash
   cd ../../finance-personal-assistant/cdk && ./deploy.sh
   cd ../../market-trends-agent/cdk && ./deploy.sh
   ```

### Demo Users Format

`.demo_users.json`:
```json
[
  {
    "username": "broker_demo",
    "password": "DemoPass123!",
    "email": "broker@example.com",
    "name": "Demo Broker"
  }
]
```

**Note:** Demo users file is **gitignored** - never commit credentials!

## SSM Parameters

This stack creates:
- `/agentcore/shared/cognito-pool-id` - Cognito User Pool ID (referenced by all agents)

## Cleanup

⚠️ **Warning:** This stack uses `RemovalPolicy.RETAIN` to protect user data.

To fully delete:
```bash
cdk destroy
aws ssm delete-parameter --name /agentcore/shared/cognito-pool-id
```

## Migration from Agent-Specific Pools

If you previously had agent-specific Cognito pools:

1. Deploy this shared stack
2. Update agent CDK apps to reference SSM parameter (already implemented)
3. Redeploy agents
4. Delete old agent-specific Cognito stacks (optional)
