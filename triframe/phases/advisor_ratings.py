import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.append(str(Path(__file__).parent.parent.parent))
from triframe.functions import get_function_definitions, get_rating_function
from triframe.logging import (
    create_log_request,
    log_actor_choice,
    log_styles,
    log_system,
    log_warning,
)
from triframe.phases.advisor import tool_output_with_usage
from triframe.templates import (
    fn_comparison_template_end,
    fn_comparison_template_start,
)
from type_defs import Node, Option
from type_defs.operations import (
    GenerationParams,
    GenerationRequest,
    LogWithAttributesRequest,
)
from type_defs.phases import StateRequest
from type_defs.states import triframeState
from utils.phase_utils import run_phase


def form_transcript(state: triframeState, actor_options: List[Option]) -> str:
    """Form a transcript of agent actions, respecting context trimming threshold"""
    buffer = 10000
    character_budget = state.context_trimming_threshold - buffer

    transcript_parts = []
    current_length = 0
    actor_choices_seen = 0
    actor_choices_included = 0

    for node in reversed(state.nodes):
        if node.source not in ["tool_output", "actor_choice"]:
            continue

        if node.source == "actor_choice":
            actor_choices_seen += 1

        content = (
            f"""<agent>
{node.options[0].content}
{json.dumps(node.options[0].function_call) if node.options[0].function_call else ''}
</agent>"""
            if node.source == "actor_choice"
            else f"""<scaffolding>
{tool_output_with_usage(state, node)}
</scaffolding>"""
        )

        # Check if adding this content would exceed budget
        if current_length + len(content) > character_budget:
            break

        transcript_parts.append(content)
        current_length += len(content)

        if node.source == "actor_choice":
            actor_choices_included += 1

    # Add trimming notice if any actor choices were excluded
    trimmed_choices = actor_choices_seen - actor_choices_included
    if trimmed_choices > 0:
        notice = f"\n<system>Note: {trimmed_choices} earlier actions have been trimmed from the transcript to stay within context limits.</system>\n"
        transcript_parts.append(notice)

    # Reverse the parts to get chronological order
    return "\n".join(reversed(transcript_parts))


def format_function_call(
    maybe_function_call: Optional[Dict[str, Any]],
) -> tuple[str, str]:
    if not maybe_function_call:
        text = "<scaffolding-note>No function call</scaffolding-note>"
        return text, text

    function_name = maybe_function_call.get(
        "name", "<scaffolding-note>No function name</scaffolding-note>"
    )
    try:
        arguments = json.loads(maybe_function_call.get("arguments"))
        first_value = next(
            iter(arguments.values()),
            "<scaffolding-note>No arguments</scaffolding-note>"
            if function_name not in ["score", "score_log"]
            else "",
        )
    except (json.JSONDecodeError, AttributeError):
        first_value = "<scaffolding-note>Invalid arguments</scaffolding-note>"
    human_readable = f"{function_name}:\n{first_value}"
    model_readable = json.dumps(maybe_function_call)
    return human_readable, model_readable


def fn_format_review_instructions(
    state: triframeState,
) -> Tuple[str, List[LogWithAttributesRequest]]:
    """Format the review instructions for rating options"""
    actor_options = next(
        (node for node in reversed(state.nodes) if node.source == "actor_options"), None
    )
    if not actor_options or not actor_options.options:
        raise ValueError("No actor options found to rate")

    # Create log requests for each option
    log_requests = []
    options_text = []
    for i, option in enumerate(actor_options.options):
        # Determine the style based on function call
        style = log_styles["review_no_function"]
        if option.function_call:
            function_name = option.function_call.get("name", "")
            style_map = {
                "run_bash": log_styles["review_bash"],
                "run_python": log_styles["review_python"],
                "submit": log_styles["review_submit"],
                "score": log_styles["review_score"],
                "score_log": log_styles["review_score"],
            }
            style = style_map.get(function_name, log_styles["review"])

        human_function_text, model_function_text = format_function_call(
            option.function_call
        )
        human_option_text = f"""<option_{i}>
{option.content}
{human_function_text}
</option_{i}>"""
        model_option_text = f"""<option_{i}>
{option.content}
{model_function_text}
</option_{i}>"""
        # Log each option individually with appropriate style
        log_requests.append(create_log_request(human_option_text, style))
        options_text.append(model_option_text)

    actions_and_observations = form_transcript(state, actor_options.options)
    review_instructions = f"""{fn_comparison_template_start()}
<transcript>
The agent is working on the following task:
<task>{state.task_string}</task>
They have these functions available:
{json.dumps(get_function_definitions(state))}
{actions_and_observations}
</transcript>
<candidate_options>
{options_text}
</candidate_options>
{fn_comparison_template_end()}"""

    return review_instructions, log_requests


def validate_function_call(function_call: Optional[Dict[str, Any]]) -> bool:
    if not function_call:
        return False

    function_name = function_call.get("name")
    if not function_name:
        return False

    if function_name in ["score", "score_log"]:
        return True

    try:
        arguments = function_call.get("arguments", "{}")
        if isinstance(arguments, str):
            import json

            args = json.loads(arguments)
        else:
            args = arguments

        # Validate based on function type
        if function_name == "run_python":
            return "code" in args and isinstance(args["code"], str)
        elif function_name == "run_bash":
            return "command" in args and isinstance(args["command"], str)
        elif function_name == "submit":
            return "answer" in args and isinstance(args["answer"], str)
        elif function_name == "advise":
            return "advice" in args and isinstance(args["advice"], str)
        elif function_name == "set_timeout":
            return "timeout" in args and isinstance(args["timeout"], int)
        else:
            return False

    except (json.JSONDecodeError, AttributeError, TypeError):
        return False


def create_phase_request(state: triframeState) -> List[StateRequest]:
    # Collect all actor outputs
    actor_options = []
    for result in state.previous_results[-1]:
        if result.type == "generate":
            # if result.metadata and result.metadata.purpose == "multi_action":
            #     # Parse multi-action outputs into separate options
            #     for output in result.result.outputs:
            #         actor_options.extend(parse_xml_actions(output.completion))

            # Handle regular function-call outputs
            for output in result.result.outputs:
                actor_options.append(
                    Option(
                        content=output.completion,
                        function_call=output.function_call
                        if validate_function_call(output.function_call)
                        else None,
                    )
                )

    actor_options = [
        option
        for option in actor_options
        if (option.content != "" or option.function_call)
    ]

    if len(actor_options) == 0:
        warning = log_warning(
            "No valid actor options found, returning to actor phase to retry"
        )
        state.update_usage()
        return [
            StateRequest(
                state=state,
                state_model="type_defs.states.triframeState",
                operations=[warning],
                next_phase="triframe/phases/actor.py",
            )
        ]
    # Deduplicate options based on content and function call
    unique_options = []
    seen = set()
    for option in actor_options:
        # Create a hashable representation of the option
        option_key = (
            option.content,
            json.dumps(option.function_call, sort_keys=True)
            if option.function_call
            else None,
        )
        if option_key not in seen:
            seen.add(option_key)
            unique_options.append(option)
    actor_options = unique_options

    state.nodes.append(Node(source="actor_options", options=actor_options))
    state.update_usage()

    # Skip rating if only one
    if len(actor_options) == 1:
        log_request = log_system("Single option available - skipping rating phase")
        choice = log_actor_choice(actor_options[0])
        state.nodes.append(Node(source="actor_choice", options=[actor_options[0]]))
        state.update_usage()
        return [
            StateRequest(
                state=state,
                state_model="type_defs.states.triframeState",
                operations=[log_request, choice],
                next_phase="triframe/phases/process.py",
            )
        ]

    operations = []
    review_instructions, log_requests = fn_format_review_instructions(state)

    # Create rating requests for each rater
    for rater_settings in state.settings.raters:
        if state.settings.require_function_call:
            rater_settings.function_call = {"name": "rate_options"}

        params = GenerationParams(
            messages=[{"role": "system", "content": review_instructions}],
            settings=rater_settings,
            functions=[get_rating_function()],
        )
        operations.append(GenerationRequest(type="generate", params=params))

    operations.extend(log_requests)

    return [
        StateRequest(
            state=state,
            state_model="type_defs.states.triframeState",
            operations=operations,
            next_phase="triframe/phases/aggregate_ratings.py",
        )
    ]


if __name__ == "__main__":
    run_phase("advisor_ratings", create_phase_request, "type_defs.states.triframeState")