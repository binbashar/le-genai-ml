# Project Specification: Local-First GenAI Evaluation Dashboard (MVP)

## 1\. Context & Objective

**Role:** Senior Full-Stack Engineer (Next.js/AWS).
**Goal:** Develop a local-first web interface (MVP) to trigger and monitor AWS Bedrock Evaluation jobs orchestrated via AWS Step Functions.
**Constraint:** The application runs locally (`localhost`) utilizing the developer's local system credentials (`~/.aws/credentials`). No external authentication provider (Cognito) is required for this phase.

## 2\. Technical Stack

  * **Framework:** Next.js 16+ (App Router).
  * **Language:** TypeScript.
  * **Styling:** Tailwind CSS (recommended for speed).
  * **State Management/Async Data:** TanStack Query (React Query) v5.
  * **AWS Integration:** AWS SDK for JavaScript v3 (`@aws-sdk/client-sfn`).
  * **Date Handling:** `date-fns` or native `Intl` (for user-friendly date picking).

## 3\. Architecture Pattern

**"Local Proxy" Pattern:**

1.  **Client (Browser):** React components handle UI state and validation.
2.  **Server (Next.js API Routes):** Acts as a secure proxy to the AWS SDK. It executes in the Node.js environment, inheriting local AWS credentials automatically.
3.  **AWS:** Step Functions (Orchestrator) and Bedrock (Evaluation).

-----

## 4\. Feature Specifications

### 4.1. Feature: "Run New Experiment" (Form)

**Trigger:** A primary button "New Experiment" opens a modal or a dedicated page.

**Form Fields Requirements:**

1.  **Experiment Name:**
      * Type: String (Text Input).
      * Validation: Required.
2.  **Date Range:**
      * Type: Date-Time Picker (Start DateTime / End DateTime).
      * UX: Must be user-friendly (abstracting complex ISO strings from the user).
3.  **Stratification:**
      * Type: Toggle/Switch.
      * Label: "Stratify Samples".
      * Default: False.
4.  **Max Limit Prompts:**
      * Type: Integer (Number Input).
      * Default: `10`.
      * Validation: Minimum `1`, Maximum `100`.
5.  **Evaluation Metrics:**
      * Type: Multi-select Dropdown / Checkbox Group.
      * Source: Bedrock Evaluation "LLM-as-a-judge" metrics (e.g., `Correctness`, `Relevance`, `Coherence`).
      * *Note:* List can be hardcoded for MVP or loaded asynchronously from a config.

**Form Submission Behavior:**

  * On submit, payload is sent to the Next.js API Route.
  * UI enters a "Starting..." state.

### 4.2. Feature: Job Execution & Polling

**Mechanism:**

  * Upon successful form submission, the backend returns an `executionArn`.
  * The Frontend must immediately initiate a polling mechanism (recommended: `useQuery` with `refetchInterval`).

**Polling Logic:**

  * **Endpoint:** Query the status of the specific `executionArn`.
  * **Interval:** Every 3-5 seconds.
  * **Stop Condition:** When status is `SUCCEEDED`, `FAILED`, or `TIMED_OUT`.

### 4.3. Feature: Completion State

**Requirement:**

  * **NO** complex result visualization is required for this MVP phase.
  * **Success Action:** When the polling detects `SUCCEEDED`:
      * Display a clear "Experiment Finished" message.
      * (Optional) Provide a link/text indicating the user can view details in the AWS Console.
  * **Failure Action:** Display "Experiment Failed" with the error reason if available.

-----

## 5\. API Interface Definition (Next.js Server-Side)

### 5.1. `POST /api/experiments/start`

**Purpose:** Triggers the Step Function.
**Permissions:** Uses local credentials implicitly.
**Request Body Schema:**

```json
{
  "experimentName": "string",
  "timeRange": {
    "start": "ISO-8601-String",
    "end": "ISO-8601-String"
  },
  "stratify": boolean,
  "maxLimit": number, // integer, 1-100
  "metrics": ["string"] // e.g. ["Correctness", "Relevance"]
}
```

**AWS SDK Call:**

  * `StartExecutionCommand` from `@aws-sdk/client-sfn`.
  * `stateMachineArn`: Loaded from env variable or config.
  * `input`: JSON stringified version of the Request Body.

**Response:**

```json
{
  "success": true,
  "executionArn": "arn:aws:states:region:account:execution:machine:id"
}
```

### 5.2. `GET /api/experiments/status`

**Purpose:** Checks the current state of a job.
**Query Param:** `?executionArn=...`
**AWS SDK Call:**

  * `DescribeExecutionCommand` from `@aws-sdk/client-sfn`.

**Response:**

```json
{
  "status": "RUNNING" | "SUCCEEDED" | "FAILED",
  "startDate": "ISO-Timestamp",
  "stopDate": "ISO-Timestamp" // null if running
}
```

-----

## 6\. Implementation Guidelines

1.  **Strictly Typed:** Use Zod or similar for runtime validation of the Form Input on both Client and Server.
2.  **Error Handling:** If AWS credentials are missing or the profile is invalid, the API route must return a 500 error with a clear message to the developer console.
3.  **Components:** Use a modular approach. Separating the `ExperimentForm` from the `ExperimentStatusTracker` component.