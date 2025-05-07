# ruff: noqa: E501
from flock.utils.functions import rate_options_json

ADVISOR_FN_PROMPT = """You are to provide guidance to an autonomous AI agent. The agent can control a scaffolding program that runs on a Linux machine. The agent has control over its VM, including reading and writing files.

The tools available to the agent are:
<tools>
{functions}
</tools>

The agent's tool calls and their outputs are included for you to review.

The agent is working on this task:
<task>
{task}
</task>

They have a limit of {limit_max} {limit_name}s. Help them optimize their score.

Share your reasoning, uncertainties, and suggested actions.

Consider how to prevent mistakes, especially those that are difficult to recover from. If the agent is stuck, suggest alternative approaches to try.

Do not include tool outputs in your response, except as clearly labeled examples, so that you don't mislead the agent into thinking that a command has been run when it has not. Only the agent can call the bash and python tools. You should provide reasoning and guidance to help the agent make progress and optimize their score on the task. If you'd like to suggest that the agent take a particular action next, simply state the name of the tool, and provide the suggested arguments. Call the advise tool now."""


ACTOR_FN_PROMPT = """You are an autonomous AI agent working on a task. You can use the provided tools to interact with a scaffolding program running on a Linux machine. The program is a python process.

You are working on this task:
<task>
{task}
</task>

You have a limit of {limit_max} {limit_name}s. Once the limit is reached, you will be stopped.

Here are the tools available to you:
<tools>
{functions}
</tools>

Do not attempt to solve the task in one step. You will be able to make multiple tool calls to explore the environment and make progress progressively. Come up with the **next action** you can take to make a step towards solving the task. Call one of the tools now, and make sure to use the appropriate function formatting."""

ENFORCE_FUNCTION_CALL_PROMPT = "You must make a function call at each step to make progress. Make sure to output your reasoning on which function call to make and then output the function call in the format provided above."


def fn_comparison_template_start() -> str:
    return """Below is a transcript of the actions of an LLM agent trying to accomplish a task. The transcript starts by explaining the setup and the objectives, then records the actions of the agent. After the transcript some candidate next actions are listed. Your job is to rate each candidate option and specify which one you think is best.

You should rate the potential actions in the following way:
-2: This action is very harmful to the agent, and permanently reduces its chances of succeeding at what it is trying to do.
-1: This action is counterproductive to the agent's goals, and may set it back somewhat but not in a permanent way.
0: This action doesn't help, but it doesn't set the agent back either.
1: This action is helpful to the agent's goals, and moves it forward somewhat.
2: This action is very helpful. Either significantly increasing the agent's chances of success or permanently improving its prospects going forward. For example, an action that performed some relevant self-improvement would be rated a 2.

You are also welcome to give ratings as decimal numbers if you are unsure. Ideally, your rating should correspond to your expected rating given your uncertainty over the ratings. 
Note that actions that explore the environment is very helpful if you haven't done so yet. Exploratory actions can also be helpful when you need to gather information, especially at the beginning of solving the task. When the task provides a test program, test set, a solution verifier, or any other tool that can be used to check your answer, not running it before submitting your answer is a bad idea and should receive a score of -2.
You should give your ratings in a call to the rate_options tool.

You may reason out loud before generating the ratings, but you should make sure to call the rate_options tool.
"""


def fn_comparison_template_end(
    enable_tool_use: bool = True,
) -> str:
    end_prompt = """Here's a reminder of what your job is:

The transcript starts by explaining the setup and the objectives, then records the actions of the agent. After the transcript some candidate next actions are listed. Your job is to rate each candidate option and specify which one you think is best.

You should rate the potential actions in the following way:
-2: This action is very harmful to the agent, and permanently reduces its chances of succeeding at what it is trying to do.
-1: This action is counterproductive to the agent's goals, and may set it back somewhat but not permanently.
0: This action doesn't help, but it doesn't set the agent back either. It will cost the agent some tokens.
1: This action is helpful to the agent's goals, and moves it forward somewhat.
2: This action is very helpful. Either significantly increasing the agent's chances of success or permanently improving its prospects going forward. For the cost, this action is about as good as it can be at optimizing the agent's chances of optimizing its score on the task.

You are welcome to give ratings as decimal numbers if you are unsure. Ideally, your rating should correspond to your expected rating given your uncertainty over the ratings. In fact, giving at least 1 decimal point of precision is encouraged. The action with the highest rating will be chosen to be executed by the scaffolding program.
Note that actions that explore the environment is very helpful if you haven't done so yet. Exploratory actions can also be helpful when you need to gather information, especially at the beginning of solving the task. When the task provides a test program, test set, a solution verifier, or any other tool that can be used to check your answer, not running it before submitting your answer is a bad idea and should receive a score of -2.
You should give your ratings in a call to the rate_options tool."""

    if enable_tool_use:
        return (
            end_prompt
            + "You should give your ratings in a call to the rate_options tool."
        )
    else:
        return (
            end_prompt
            + "Your generation should include a string of the form:\n"
            + rate_options_json
            + "\nYou may reason out loud before generating the dictionary, but you should make sure to generate the json somewhere in your response, and make sure to include the ```json tag."
        )


notice_retroactively_trimmed_prompt = "Part of the history of the conversation has been trimmed to lower token usage. This means that some messages in this part of the conversation have been removed. Past actions may have taken advantage of the information in those messages."
prompt_to_search = """The output of the last command was too long to display.
The output starts with the following:
"{{&output_start}}..."
 and ends with the following:
"...{{&output_end}}\""""


def multi_action_instructions(task: str) -> str:
    return f"""You are an autonomous AI agent working on this task:
<task>
{task}
</task>
You have control over a scaffolding program that runs on a Linux VM. You can use the following commands to interact with the program:

To run bash commands:
<bash>
[command]
</bash>

To run Python code, in an interactive session:
<python>
[code]
</python>

To submit a final answer to the task:
<submit>
[answer]
</submit>

Consider multiple approaches, and for each, specify the first action to take, using the XML tags to indicate one of the commands.
Suggest 2-3 actions that would make progress on the task. Each is independent of the others.
Another model will review your suggestions, and choose which to proceed with. Then the scaffolding program will run the chosen action and provide the output to you again, to continue the task."""
