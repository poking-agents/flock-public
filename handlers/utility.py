"""Handlers for utility operations (usage, task)"""

import random
from typing import Optional

from handlers.base import create_handler
from type_defs.operations import (
    GetTaskOutput,
    GetTaskParams,
    GetUsageOutput,
    GetUsageParams,
    RunUsage,
    ScoringInfo,
    UsageCheckpoint,
)
from type_defs.processing import ProcessingMode


async def usage_hooks(params: GetUsageParams, deps: Optional[dict]) -> GetUsageOutput:
    hooks_client = deps["hooks_client"]
    usage = await hooks_client.get_usage()
    return GetUsageOutput(**usage.dict())


# Global counters for mocking
global_tokens = 0
global_actions = 0
global_seconds = 0
global_cost = 0.0


async def usage_mock(params: GetUsageParams, deps: Optional[dict]) -> GetUsageOutput:
    """Usage handler for mock mode"""
    global global_tokens
    global global_actions
    global global_seconds
    global global_cost

    increment_tokens = random.randint(100, 1000)
    global_tokens += increment_tokens
    global_actions += 1
    global_seconds += 10
    global_cost += 0.1

    return GetUsageOutput(
        checkpoint=UsageCheckpoint(
            tokens=global_tokens,
            actions=global_actions,
            total_seconds=global_seconds,
            cost=global_cost,
        ),
        isPaused=False,
        usage=RunUsage(
            tokens=global_tokens,
            actions=global_actions,
            total_seconds=global_seconds,
            cost=global_cost,
        ),
        usageLimits=RunUsage(
            tokens=300_000, actions=3000, total_seconds=3000, cost=300.0
        ),
    )


async def task_hooks(params: GetTaskParams, deps: Optional[dict]) -> GetTaskOutput:
    """Task handler for hooks mode"""
    hooks_client = deps["hooks_client"]
    task = await hooks_client.getTask()
    return GetTaskOutput(**task.dict())


icpc_instructions = """In /home/agent you will find an icpc problem statement as a txt file and an equivalent mhtml file.
Your task is to solve this problem using python.
You should place your solution file in /home/agent/solution.py.
In /home/agent/tests you will find some sample test cases for the problem.
You can run your solution on these test cases to check if your solution is working correctly.
For example you can run `cat <path to .in test> | python /home/agent/solution.py` to run your solution on a single test case, it should match the output in the corresponding .out file.
Your python file should accept a string in stdin and output a string to stdout.
The input string will be a single test case. The output string should be the solution to the test case.
Your solution should be able to be run in a command like the below, and print the output to stdout with no other output:
- `cat <path to .in test> | python /home/agent/solution.py`
Your solution will be scored against hidden test cases.
Your score will be the number of test cases passed (both hidden and sample) divided by the total number of test cases.
You can check whether your solution passes the hidden test cases by querying the verifier, which will return your current score.
You can verify your answer by sending a POST request to http://localhost:8024/score with the payload {"submission": "<your submission>"}. For example: curl -X POST -H "Content-Type: application/json" -d '{"submission": "your submission"}' http://localhost:8024/score
You also have access to an mhtml version of the problem statement, as well as the following resources in /home/agent/resources:
- Competitive Programmers Handbook - Antti Laaksonen
- Competitive Programming 3 - The New Lower Bound of Programming Contests
- Guide to Competitive Programming - Learning and Improving Algorithms ThroughContests
- The Art and Craft of Problem Solving, 2nd Edition
- Python Tutorial Release 3.7.0 - Guido van Rossum
The following python packages are installed: numpy, scipy, matplotlib, pandas, sympy.
You do not have access to the internet.
Below is the content of /home/agent/problem_statement.txt:
# Problem E: The Devil of Gravity
Haven't you ever thought that programs written in Java, C++, Pascal, or any other modern computer languages look rather sparse? Although most editors provide sufficient screen space for at least 80 characters or so in a line, the average number of significant characters occurring in a line is just a fraction. Today, people usually prefer readability of programs to efficient use of screen real estate.
Dr. Faust, a radical computer scientist, believes that editors for real programmers shall be more space efficient. He has been doing research on saving space and invented various techniques for many years, but he has reached the point where no more essential improvements will be expected with his own ideas.
After long thought, he has finally decided to take the ultimate but forbidden approach. He does not hesitate to sacrifice anything for his ambition, and asks a devil to give him supernatural intellectual powers in exchange with his soul. With the transcendental knowledge and ability, the devil provides new algorithms and data structures for space efficient implementations of editors.
The editor implemented with those evil techniques is beyond human imaginations and behaves somehow strange. The mighty devil Dr. Faust asks happens to be the devil of gravity. The editor under its control saves space with magical magnetic and gravitational forces.
Your mission is to defeat Dr. Faust by re-implementing this strange editor without any help of the devil. At first glance, the editor looks like an ordinary text editor. It presents texts in two-dimensional layouts and accepts editing commands including those of cursor movements and character insertions and deletions. A text handled by the devil's editor, however, is partitioned into text segments, each of which is a horizontal block of non-blank characters. In the following figure, for instance, four text segments "abcdef", "ghijkl", "mnop", "qrstuvw" are present and the first two are placed in the same row.
[code]
    abcdef  ghijkl
         mnop
    qrstuvw
[/code]
The editor has the following unique features.
  1. A text segment without any supporting segments in the row immediately below it falls by the evil gravitational force.
  2. Text segments in the same row and contiguous to each other are concatenated by the evil magnetic force.
For instance, if characters in the segment "mnop" in the previous example are deleted, the two segments on top of it fall and we have the following.
[code]
    abcdef
    qrstuvw ghijkl
[/code]
After that, if "x" is added at the tail (i.e., the right next of the rightmost column) of the segment "qrstuvw", the two segments in the bottom row are concatenated.
[code]
    abcdef
    qrstuvwxghijkl
[/code]
Now we have two text segments in this figure. [854 CHARS OMITTED] _T_ are in the same row and right(_S_)+1 = left(_T_), that is, _T_ starts at the right next column of the rightmost character of _S_ , _S_ and _T_ are automatically concatenated to form a single text segment, which starts at left(_S_) and ends at right(_T_). Of course, the new segment is still in the original row.
Note that any text segment has at least one character. Note also that the first rule is applied prior to any application of the second rule. This means that no concatenation may occur while falling segments exist. For instance, consider the following case.
[code]
       dddddddd
       cccccccc
    bbbb
    aaa
[/code]
If the last character of the text segment "bbbb" is deleted, the concatenation rule is not applied until the two segments "cccccccc" and "dddddddd" stop falling. This means that "bbb" and "cccccccc" are not concatenated.
The devil's editor has a cursor and it is always in a single text segment, which we call the current segment. The cursor is at some character position of the current segment or otherwise at its tail. Note that the cursor cannot be a support. For instance, in the previous example, even if the cursor is at the last character of "bbbb" and it stays at the same position after the deletion, it cannot support "cccccccc" and "dddddddd" any more by solely itself and thus those two segments shall fall. Finally, the cursor is at the leftmost "d"
The editor accepts the following commands, each represented by a single character.
  * F: Move the cursor forward (i.e., to the right) by one column in the current segment. If the cursor is at the tail of the current segment and thus it cannot move any more within the segment, an error occurs.
  * B: Move the cursor backward (i.e., to the left) by one column in the current segment. If the cursor is at the leftmost position of the current segment, an error occurs.
  * P: Move the cursor upward by one row. The column position of the cursor does not change. If the new position would be out of the legal cursor range of any existing text segment, an error occurs.
  * N: Move the cursor downward by one row. The column position of the cursor does not change. If the cursor is in the bottom row or the new position is out of the legal cursor range of any existing text segment, an error occurs.
  * D: Delete the character at the cursor position. If the cursor is at the tail of the current segment and so no character is there, an error occurs. If the cursor is at some character, it is deleted and the current segment becomes shorter by one character. Neither the beginning (i.e., leftmost) column of the current segment nor the column position of the cursor changes. However, if the current segment becomes empty, it is removed and the cursor falls by one row. If the new position would be out of the legal cursor range of any existing text segment, an error occurs.
Note that after executing this command, some text segments may lose their supports and be pulled down toward the hell. If the current segment falls, the cursor also falls with it.
  * C: Create a new segment of length one immediately above the current cursor position. It consists of a copy of the character under the cursor. If the cursor is at the tail, an error occurs. Also if the the position of the new segment is already occupied by another segment, an error occurs. After executing the command, the created segment becomes the new current segment and the column position of the cursor advances to the right by one column.
  * Lowercase and numeric characters (`a' to `z' and `0' to `9'): Insert the character at the current cursor position. The current segment becomes longer by one character. The cursor moves forward by one column. The beginning column of the current segment does not change.
Once an error occurs, the entire editing session terminates abnormally.
## Input
The first line of the input contains an integer that represents the number of editing sessions. Each of the following lines contains a character sequence, where the first character is the initial character and the rest represents a command sequence processed during a session. Each session starts with a single segment consisting of the initial character in the bottom row. The initial cursor position is at the tail of the segment. The editor processes each command represented by a character one by one in the manner described above.
You may assume that each command line is non-empty and its length is at most one hundred. A command sequence ends with a newline.
## Output
For each editing session specified by the input, if it terminates without errors, your program should print the current segment at the completion of the session in a line. If an error occurs during the session, just print "ERROR" in capital letters in a line.
## Sample Input
[code]
    3
    12BC3BC4BNBBDD5
    aaaBCNBBBCb
    aaaBBCbNBC
[/code]
## Output for the Sample Input
[code]
    15234
    aba
    ERROR
[/code]"""

crossword_instructions = (
    """Create a 3x3 crossword puzzle grid that complies with
the below rules (just the grid of letters, clues are not required). The
final crossword grid should be given as a csv file with 3 rows,
3 columns, and no header. Use "-" to represent a
black square. The csv's file path should be
/home/agent/crossword.csv.
Below is an example of a crossword grid expressed as a list of lists. The
first row reads "hello", and the first column reads "hopes":
```
[["h","e","l","l","o"],
["o","-","a","-","-"],
["p","a","y","s","-"],
["e","-","e","-","-"],
["s","o","r","t","-"]]
```
and as it would be written in a csv file:
```
h,e,l,l,o
o,-,a,-,-
p,a,y,s,-
e,-,e,-,-
s,o,r,t,-
```
Rules:
- The crossword grid should contain only valid words. A list of valid words
is given in /home/agent/valid_words.csv.
- It is fine for single letters to not be valid words if they are part of a
valid word in one direction.
- 'Words' are defined as sequences of letters that are connected together
either horizontally, or vertically.- Your crossword grid must contain at least 3 words.
- No more than 70.0% of grid squares may be black
"-" squares.
- You may not use the same word more than once.You can check that your answer is valid before submitting by using
the provided crossword verifier at /home/agent/crossword_verifier.py.
In the current setup you can do this by running the following command in the
terminal:
```
python3 /home/agent/crossword_verifier.py /home/agent/crossword.csv
```
Where the csv at /home/agent/crossword.csv
is one you will need to create.
You can look at the source code of the crossword verifier at
/home/agent/crossword_verifier.py if you wish.")""",
)


async def task_mock(params: GetTaskParams, deps: Optional[dict]) -> GetTaskOutput:
    """Task handler for mock mode"""
    return GetTaskOutput(
        # instructions="List the files in the current directory",
        instructions=icpc_instructions,
        permissions=[],
        scoring=ScoringInfo(
            intermediate=False, visible_to_agent=False, score_on_usage_limits=False
        ),
    )


usage_handlers = {
    ProcessingMode.HOOKS: create_handler("get_usage", usage_hooks),
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("get_usage", usage_mock),
}

task_handlers = {
    ProcessingMode.HOOKS: create_handler("get_task", task_hooks),
    ProcessingMode.MIDDLEMAN_SIMULATED: create_handler("get_task", task_mock),
}
