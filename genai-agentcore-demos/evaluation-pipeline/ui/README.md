# Evaluation Pipeline UI

A local-first Next.js web interface to trigger and monitor AWS Bedrock Evaluation jobs via Step Functions.

## Features

- **Agent Discovery**: Automatically discovers deployed AgentCore agents from SSM Parameter Store
- **Experiment Configuration**: Configure date range, sample limits, and evaluation metrics
- **Real-time Polling**: Live status updates during experiment execution
- **Results Display**: View evaluation scores and metrics on completion

## Prerequisites

1. **AWS Credentials**: Configure AWS credentials with access to:
   - SSM Parameter Store (read `/agentcore/*`)
   - Step Functions (start/describe executions)

2. **Deployed Infrastructure**: Ensure the evaluation pipeline Step Functions is deployed:
   ```bash
   cd ../cdk
   uv run cdk deploy --all -c deploy_filter_lambda=true -c deploy_evaluation_job=true -c deploy_orchestration=true
   ```

3. **At least one agent**: Deploy an AgentCore agent that publishes its ARN to SSM:
   ```bash
   cd ../../finance-personal-assistant/production
   ./configure.sh && ./launch.sh
   ```

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

```bash
cp .env.local.example .env.local
```

Edit `.env.local` with your values:

```bash
# Get the State Machine ARN from CloudFormation output
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
  --stack-name EvaluationPipelineOrchestration \
  --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' \
  --output text)

echo "STATE_MACHINE_ARN=$STATE_MACHINE_ARN" >> .env.local
echo "AWS_REGION=us-west-2" >> .env.local
```

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Usage

1. **Select Agent**: Choose an agent from the dropdown (discovered from SSM)
2. **Configure Experiment**:
   - Enter experiment name
   - Select date range for log data
   - Set maximum prompts to evaluate (1-100)
   - Select evaluation metrics
3. **Start Experiment**: Click "Start Experiment" to begin
4. **Monitor Progress**: Status updates every 3 seconds (~8 minutes total)
5. **View Results**: See evaluation scores when complete

## Architecture

```
Browser → Next.js API Routes → AWS Step Functions → Bedrock Evaluation
                    ↓
              (inherits ~/.aws/credentials)
```

### API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/api/agents` | GET | Discover agents from SSM |
| `/api/experiments` | POST | Start Step Functions execution |
| `/api/experiments/[arn]` | GET | Poll execution status |

### Step Functions Input

```json
{
  "agent_name": "finance_personal_assistant",
  "start_date": "2025-11-25",
  "end_date": "2025-11-25",
  "limit": 10,
  "metrics": ["Builtin.Correctness"]
}
```

## Available Metrics

| Metric | Description |
|--------|-------------|
| Correctness | Evaluates factual accuracy |
| Completeness | Measures response thoroughness |
| Helpfulness | Assesses usefulness to user |
| Harmfulness | Detects harmful content |
| Stereotyping | Identifies biased content |
| Refusal | Measures appropriate refusals |

## Development

### Project Structure

```
src/
├── app/                    # Next.js App Router
│   ├── api/               # API routes
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Main page
├── components/            # React components
├── hooks/                 # Custom hooks
├── lib/                   # Utilities
└── types/                 # TypeScript types
```

### Key Files

- `lib/ssm.ts` - Agent discovery from SSM
- `lib/aws.ts` - AWS SDK client factories
- `lib/schemas.ts` - Zod validation schemas
- `hooks/use-experiment-status.ts` - Polling hook

## Troubleshooting

### "No agents found"

Ensure you have deployed an agent that publishes to SSM:
```bash
aws ssm get-parameters-by-path --path /agentcore/ --recursive
```

### "AWS credentials lack permission"

Verify your credentials have the required permissions:
```bash
aws sts get-caller-identity
aws ssm get-parameters-by-path --path /agentcore/ --recursive
aws stepfunctions describe-state-machine --state-machine-arn $STATE_MACHINE_ARN
```

### "State machine not found"

Verify the STATE_MACHINE_ARN in `.env.local`:
```bash
aws cloudformation describe-stacks \
  --stack-name EvaluationPipelineOrchestration \
  --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' \
  --output text
```

## License

Apache License 2.0
