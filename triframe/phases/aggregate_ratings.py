import json
import re
import sys
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Tuple, Union

sys.path.append(str(Path(__file__).parent.parent.parent))
from triframe.logging import (
    log_actor_choice,
    log_advisor_choosing,
)
from type_defs.base import Node, Option
from type_defs.operations import LogRequest
from type_defs.phases import StateRequest
from type_defs.states import triframeState
from utils.functions import parse_backticks_json
from utils.logging import log_system, log_warning
from utils.phase_utils import results_of_type, run_phase


def summarize_ratings(all_ratings: Dict[int, List[float]]) -> str:
    summary_parts = []
    for option_idx, ratings in all_ratings.items():
        if len(ratings) > 1:
            stats = {
                "mean": mean(ratings),
                "min": min(ratings),
                "max": max(ratings),
                "count": len(ratings),
            }
            summary = (
                f"Option {option_idx}: mean={stats['mean']:.2f}, "
                f"range=[{stats['min']:.2f}, {stats['max']:.2f}], "
                f"n={stats['count']}"
            )
        else:
            summary = f"Option {option_idx}: rating={ratings[0]:.2f}, n=1"
        summary_parts.append(summary)
    return "\n".join(summary_parts)


def parse_ratings(function_call: Dict[str, Any]) -> Dict[int, List[float]] | None:
    """Parse ratings from a ratings node into
    a dict mapping option index to list of ratings"""
    ratings_by_option: Dict[int, List[float]] = {}
    try:
        if not function_call:
            return {}
        ratings_array = json.loads(function_call["arguments"])["ratings"]
        for rating in ratings_array:
            option_idx = rating["option_index"]
            if option_idx not in ratings_by_option:
                ratings_by_option[option_idx] = []
            ratings_by_option[option_idx].append(rating["rating"])
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    return ratings_by_option


def aggregate_ratings(
    state: triframeState,
) -> Union[List[StateRequest], Tuple[Option, List[LogRequest]]]:
    """Aggregate ratings and select best option, handling partial failures"""
    try:
        rating_generation_results = results_of_type(
            state.previous_results[-1], "generate"
        )
        if not rating_generation_results:
            raise ValueError("No rating generation results found")
        actor_options = next(
            (node for node in reversed(state.nodes) if node.source == "actor_options"),
            None,
        )
        if not actor_options or not actor_options.options:
            raise ValueError("No actor options found to rate")
        rating_node = Node(source="advisor_ratings", options=[])
        successful_ratings = 0
        failed_ratings = 0
        all_ratings: Dict[int, List[float]] = {}
        log_requests = []
        for result in rating_generation_results:
            if not result.result.outputs:
                failed_ratings += 1
                continue
            for option in result.result.outputs:
                # Keep full completion for logging
                full_completion = option.completion
                # Remove CoT for state storage
                completion_without_cot = re.sub(
                    r"<think>.*?</think>", "", option.completion, flags=re.DOTALL
                ).strip()

                if state.settings.enable_tool_use:
                    function_call = option.function_call
                else:
                    ratings_json = parse_backticks_json(completion_without_cot)
                    function_call = {
                        "name": "rate_options",
                        "arguments": json.dumps(ratings_json),
                    }

                if not function_call:
                    failed_ratings += 1
                    log_requests.append(
                        log_warning(
                            "Cannot parse valid function call from this generation: "
                            f"completion: {json.dumps(completion_without_cot, indent=2)}\n"
                            f"function_call: {option.function_call}"
                        )
                    )
                    continue

                # Log with full completion including CoT
                log_requests.append(
                    log_advisor_choosing(
                        Option(
                            content=full_completion,
                            function_call=function_call,
                        )
                    )
                )

                # Store in state without CoT
                rating_node.options.append(
                    Option(content=completion_without_cot, function_call=function_call)
                )

                try:
                    ratings = parse_ratings(function_call)
                    if ratings is None:
                        failed_ratings += 1
                        log_requests.append(
                            log_warning(
                                "Failed to parse ratings from this generation: "
                                f"{json.dumps(option.model_dump(), indent=2)}"
                            )
                        )
                        continue
                    successful_ratings += 1
                    for option_idx, ratings_list in ratings.items():
                        if option_idx not in all_ratings:
                            all_ratings[option_idx] = []
                        all_ratings[option_idx].extend(ratings_list)
                except Exception as e:
                    failed_ratings += 1
                    log_requests.append(
                        log_warning(f"Error processing ratings: {str(e)}")
                    )
                    continue

        state.nodes.append(rating_node)
        if not all_ratings:
            log_requests.append(
                log_warning("No valid ratings found, using first option")
            )
            log_requests.append(log_actor_choice(actor_options.options[0]))
            return actor_options.options[0], log_requests
        summary = summarize_ratings(all_ratings)
        log_requests.append(log_system(f"{summary}"))
        avg_ratings = {idx: mean(ratings) for idx, ratings in all_ratings.items()}
        best_idx = max(avg_ratings.items(), key=lambda x: x[1])[0]
        if avg_ratings[best_idx] < -0.25:
            warning = log_warning(
                "Low-rated options, returning to actor to generate new options"
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
        log_requests.append(
            log_system(f"Selected option with highest average rating: {best_idx}")
        )
        log_requests.append(log_actor_choice(actor_options.options[best_idx]))
        return actor_options.options[best_idx], log_requests
    except Exception as e:
        if actor_options and actor_options.options:
            log_requests = [
                log_warning(f"Error aggregating ratings: {repr(e)}"),
                log_warning("Falling back to first option"),
                log_actor_choice(actor_options.options[0]),
            ]
            return actor_options.options[0], log_requests
        raise


def create_phase_request(state: triframeState) -> List[StateRequest]:
    """Create phase request for rating aggregation"""
    result = aggregate_ratings(state)
    if isinstance(result, list):
        return result
    selected_option, log_requests = result
    state.nodes.append(Node(source="actor_choice", options=[selected_option]))
    state.update_usage()
    return [
        StateRequest(
            state=state,
            state_model="type_defs.states.triframeState",
            operations=[*log_requests],
            next_phase="triframe/phases/process.py",
        )
    ]


if __name__ == "__main__":
    run_phase(
        "aggregate_ratings", create_phase_request, "type_defs.states.triframeState"
    )
