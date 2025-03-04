# Flock - Agent Framework

_Note: flock currently requires an API like [Vivaria's](https://github.com/METR/vivaria) Middleman._

## Core Concepts

### Phases

Phases are the fundamental building blocks of workflows in flock. A phase is a Python script that:

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

Operations are the basic units of work that can be executed by the framework. Each operation has:

1. A request type (e.g., bash, python, generate)
2. Parameters specific to that operation
3. A handler that executes the operation
4. A result type that contains the operation output

Core operations include:
- `bash`: Execute shell commands
- `python`: Execute Python code
- `generate`: Generate text using AI models

## Project Structure

```
flock/
├── handlers/               # Operation handlers
│   ├── base.py             # Base handler definitions
│   ├── bash.py             # Bash command execution
│   ├── python.py           # Python code execution
│   ├── generate.py         # AI model generation
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
```

## Execution Modes

1. **HOOKS**: Execution in run containers
   - Uses pyhooks for integration with Vivaria

2. **MIDDLEMAN_SIMULATED**: Simulated execution
   - Testing environment

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

## Triframe Agent Phases
![triframe phases](/assets/triframe_phases.png)


## Usage

### Starting the Server

```bash
python main.py [--log-level DEBUG] [--mode middleman_simulated] [--workflow triframe]
```