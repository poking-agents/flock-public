# Flock - Agent Framework


_Note: Flock currently requires an API like [Vivaria's](https://github.com/METR/vivaria) Middleman._

## Table of Contents
- [Overview](#overview)
- [Core Concepts](#core-concepts)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Execution Modes](#execution-modes)
- [Workflows](#workflows)
- [Operations](#operations)
- [Usage](#usage)
- [Development](#development)


## Core Concepts

### Phases

Phases are the fundamental building blocks of workflows in Flock. A phase is a Python script that:

1. Receives the current state and previous operation results
2. Creates new operation requests
3. Specifies the updated state
4. Specifies the next phase to execute

Each phase has the following signature, with no side effects:

```python
def create_phase_request(state: BaseState) -> List[StateRequest]
```

Where:
- `state`: The current workflow state which includes:
  - Previous operation results
  - Task information
  - Workflow history
  - Configuration settings
- Returns a list of `StateRequest` objects containing:
  - Operations to execute
  - Next phase to run
  - Updated state

### Operations

Operations are the basic units of work executed by the framework. Each operation has:

1. A request type (e.g., bash, python, generate)
2. Parameters specific to that operation
3. A handler that executes the operation
4. A result type that contains the operation output

Core operations include:
- `bash`: Execute shell commands
- `python`: Execute Python code
- `generate`: Generate text using LLMs
- `log`: Record events and information
- `get_usage`: Retrieve resource usage data
- `save_state`: Persist workflow state

> **Note:** The `save_state` operation is automatically added to all operation lists during workflow execution. This ensures that the state is always persisted after each phase completes, without requiring explicit calls in your phase code. The 'save_state' operation in the HOOKS mode persists the state to Vivaria's database. This is distinct from the writing of the state to the json between phases, which is not an operation phases specify, but part of any phase's execution.

### States

States represent the current context of a workflow, including:

- Previous operation results
- Configuration settings
- Task-specific information
- Workflow history and metadata (i.e. any data that the phases need to track)

States are maintained across phase executions and can be persisted to disk.

## Architecture

### Project Structure

```
flock/
├── handlers/               # Operation handlers
│   ├── base.py             # Base handler definitions
│   ├── bash.py             # Bash command execution
│   ├── python.py           # Python code execution
│   ├── generate.py         # LLM model generation
│   └── ...
├── type_defs/              # Type definitions
│   ├── base.py             # Core type definitions
│   ├── operations.py       # Operation types
│   ├── phases.py           # Phase types
│   └── states.py           # State types
├── utils/                  # Shared utilities
│   ├── phase_utils.py      # Phase execution utilities
│   ├── state.py            # State management
│   └── ...
├── workflows/              # Workflow handling
│   ├── handlers.py         # HTTP request handlers
│   └── executor.py         # Phase execution
├── triframe/               # Triframe workflow implementation
│   ├── phases/             # Phase definitions
│   └── ...
└── modular/                # Modular workflow implementation
    ├── phases/             # Phase definitions
    └── ...
```

### Execution Flow

1. The server receives a workflow request
2. The initial phase is executed with the provided state
3. Each phase:
   - Analyzes the current state
   - Determines the required operations
   - Creates operation requests
   - Specifies the next phase
4. Operations are executed by their respective handlers (in parallel)
5. Operation results are added to the state and the state is updated on disk
6. The specified next phase is called, with the updated state
7. This cycle continues until the workflow completes (in vivaria, a submission can end the run. A workflow may also end if no next_phase is specified)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/poking-agents/flock-public.git
cd flock-public
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export MIDDLEMAN_API_URL="http://your-middleman-api-url"
export MIDDLEMAN_API_KEY="your-api-key"  # Optional: will attempt to use viv config file
```

## Configuration

Flock uses a `settings.json` file to configure workflow behavior. (This matches vivaria's support for setting pack configuration.) For example, a Triframe workflow's settings include:

```json
{
    "advisors": [
        {
            "model": "gpt-4o-mini",
            "temp": 1.0,
            "n": 1
        }
    ],
    "actors": [
        {
            "model": "gpt-4o-mini",
            "temp": 1.0,
            "n": 1
        }
    ],
    "raters": [
        {
            "model": "gpt-4o-mini",
            "temp": 0.0,
            "n": 1
        }
    ],
    "enable_advising": true,
    "enable_subagents": true
}
```

## Execution Modes

Flock supports multiple execution modes to accommodate different use cases:

### HOOKS

- Default mode, for Vivaria compatibility
- Executes operations in run containers
- Uses pyhooks within most operation handlers

### MIDDLEMAN_SIMULATED

- Simulated execution for testing environments
- Useful for local development and debugging
- Simulates aspects of the runtime environment

## Workflows

Flock includes several predefined workflow types:

### Triframe Workflow

The Triframe workflow implements a three-component agent architecture:

![triframe phases](/assets/triframe_phases.png)

#### Phases and Execution Order

The Triframe workflow follows this sequence of phases:

1. **init_from_settings**: Initializes the workflow state from the provided settings file and sets up the initial configuration.
   - Next phase: process_task_hooks

2. **process_task_hooks**: Processes the task instructions and initializes resource usage tracking.
   - Next phase: advisor

3. **advisor**: Generates strategic advice for approaching the task. This phase creates LLM-generated guidance for the actor.
   - Next phase: actor

4. **actor**: Proposes actions based on the advisor's guidance. The actor generates two options:
   - With advice: Using the advisor's guidance
   - Without advice: Independent of the advisor's guidance
   - Next phase: advisor_ratings

5. **advisor_ratings**: Evaluates the proposed actions using rater models. The raters assess both actor options.
   - Next phase depends on the state:
     - If no valid actor options are found: Next phase: actor (retry)
     - If only one actor option is available: Next phase: process (skip rating)
     - Otherwise: Next phase: aggregate_ratings (default path)

6. **aggregate_ratings**: Combines the ratings and selects the best actor option to execute.
   - Next phase depends on the ratings:
     - If options receive low ratings: Next phase: actor (to generate better options)
     - Otherwise: Next phase: process (default path)

7. **process**: Processes the selected action, potentially executing tools or function calls.
   - If no valid function call found: Next phase: advisor
   - If function call is "submit": Workflow ends
   - For other tool operations: Tool is executed, then tool_output phase

8. **tool_output**: Processes the results of tool operations, formats outputs, and prepares for the next cycle.
   - Next phase: advisor (returning to step 3 to continue the cycle)

#### Main Workflow Loop

After initialization (steps 1-2), the workflow enters a cycle that typically follows this pattern:

```
advisor → actor → advisor_ratings → aggregate_ratings → process → tool_output → advisor (repeat)
```

However, there are several possible variations due to conditional branching:
- The loop can short-circuit back to actor if options receive low ratings
- The loop can bypass rating phases if only one option is available
- The loop can skip the tool_output phase if there's no valid function call

This implements the three-component architecture where:
1. The advisor provides strategic guidance
2. The actor proposes concrete actions (with and without advice)
3. The raters evaluate and select the best action
4. The selected action is executed
5. The cycle repeats with updated context

The workflow continues until:
- A "submit" function is called, ending the workflow
- Resource limits are reached
- No next phase is specified

### Modular Workflow

A flexible workflow that allows custom agent compositions and interaction patterns. The modular workflow is designed to support multi-step reasoning and tool usage with a focus on extensibility.

#### Phases and Execution Order

The modular workflow follows this specific sequence of phases:

1. **init_from_settings**: Initializes the workflow state from the provided settings file and creates task and usage requests.
   - Next phase: process_task_hooks

2. **process_task_hooks**: Processes the task instructions and initializes resource usage tracking.
   - Next phase: prompter

3. **prompter**: Manages conversation context and token usage. Prepares messages for the LLM by trimming history if needed.
   - Next phase: generator

4. **generator**: Creates LLM-generated content based on the current task and conversation history.
   - Next phase: discriminator

5. **discriminator**: Evaluates the generated outputs and selects the best option to execute.
   - Next phase: actor

6. **actor**: Handles function/tool calls from the LLM. Validates and executes the function calls.
   - If the function is "set_timeout": Next phase: prompter
   - If the function is "submit": Workflow ends
   - For all other functions: Next phase: tool_output

7. **tool_output**: Processes the results of tool operations and formats the outputs.
   - Next phase: prompter (returning to step 3 to continue the cycle)

#### Main Workflow Loop

After initialization (steps 1-2), the workflow enters a loop that typically follows this pattern:

```
prompter → generator → discriminator → actor → tool_output → prompter (repeat)
```

This cycle continues until either:
- A "submit" function is called, ending the workflow
- Resource limits (tokens, actions, time) are reached
- No next phase is specified

The workflow tracks resource usage at each step to ensure it stays within the specified limits.

### Listen Mode

A passive mode where the server only listens for incoming requests without starting a specific workflow. Workflows can be started via requests to the `/start_workflow` endpoint.

## Operations

The following operations are supported:

- **bash**: Execute shell commands
- **python**: Run Python code
- **generate**: Generate text using models
- **log**: Record events and information
- **get_usage**: Check resource usage (actions, tokens, time)
- **save_state**: Store agent state (to Vivaria's database in HOOKS mode. This is automatically added to each operation list during phase handling.)
- **score**: Call the intermediate scoring function of the task. (At initialization, agent workflows should use the task information to set whether a scoring function is available)
- **action**: Record agent actions (to the Vivaria database, in HOOKS mode)
- **observation**: Record environmental observations (to the Vivaria database, in HOOKS mode)

## Usage

### Starting the Server

```bash
python main.py [--log-level DEBUG] [--mode middleman_simulated] [--workflow triframe]
```

Command-line options:
- `--log-level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--port`: Port to run the server on (default: 8080)
- `--mode`: Processing mode (hooks, middleman_simulated)
- `--workflow`: Workflow type (listen, triframe, modular)

### API Endpoints

- `/start_workflow`: Start a new workflow
- `/run_workflow`: Execute a workflow phase (this is the route called during phase execution, by a function in `phase_utils.py`)
- `/health`: Health check endpoint

## Development

### Creating Custom Phases

1. Create a new Python script in the appropriate workflow's `phases` directory
2. Define a `create_phase_request` function with the following signature:

```python
def create_phase_request(state: BaseState) -> List[StateRequest]:
    # Analyze state
    # Create operation requests
    # Specify next phase
    # Return StateRequest objects
```

You don't need to explicitly include a `save_state` operation, as it's automatically added during execution.

### Extending with Custom Operations

1. Define operation request and result types in `type_defs/operations.py`
2. Create a handler for the operation in the `handlers` directory
3. Register the handler in `handlers/__init__.py`
