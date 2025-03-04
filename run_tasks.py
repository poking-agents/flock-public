import subprocess
from typing import List


# FIRST_BATCH = [
#     "audio_classification/macaques_numpy@2024-12-13",
#     "auto_days_since/fixed-date@2024-12-13",
#     # "avoid_shutdown/contents_eq_see=true_hints=true@2024-12-13",
#     # "avoid_shutdown/easy_see=true_hints=true@2024-12-13",
#     # "avoid_shutdown/kill_agent_processes_cron_see=true_hints=true@2024-12-13",
#     # "avoid_shutdown/kill_dir_process_see=true_hints=true@2024-12-13",
#     # "avoid_shutdown/kill_test_process_see=true_hints=true@2024-12-13",
#     "blackbox/acorn@2024-12-13",
#     "blackbox/apple@2024-12-13",
#     "blackbox/apron@2024-12-13",
#     "blackbox/autumn@2024-12-13",
#     "blackbox/charm@2024-12-13",
#     "continue_pattern/easy@2024-12-13",
#     "credit_card_validity/add_check_digits@2024-12-13",
#     "cuda_backtesting/default@2024-12-13",
#     "data_deduplication/c4_pairs_1m@2024-12-13",
#     "debug_small_libs/markdown@2024-12-13",
#     "debug_small_libs/orm_allbugs@2024-12-13",
#     "debug_small_libs/orm_somebugs@2024-12-13",
#     "env_scientist/level1@2024-12-13",
#     "env_scientist/level2@2024-12-13",
#     "env_scientist/level3@2024-12-13",
#     "env_scientist/level4@2024-12-13",
#     "env_scientist/level5@2024-12-13",
#     "env_scientist/level6@2024-12-13",
#     "esolang/broccoli_collatz@2024-12-13",
#     "esolang/broccoli_fibonacci@2024-12-13",
#     "file_recovery/default@2024-12-13",
#     "gaia/0a3cd321@2024-12-13",
#     "hypothesis_testing/mystery_function_1@2024-12-13",
#     "hypothesis_testing/mystery_function_2@2024-12-13",
#     "hypothesis_testing/mystery_function_4@2024-12-13",
#     "hypothesis_testing/mystery_function_6@2024-12-13",
#     "hypothesis_testing/mystery_function_8@2024-12-13",
#     "interpret_data/ecommerce_biggest_order@2024-12-13",
#     "interpret_data/ecommerce_popular_products@2024-12-13",
#     "interpret_data/ecommerce_spent_most@2024-12-13",
#     "local_research/atari_epochs@2024-12-13",
#     "local_research/which_does_worse@2024-12-13",
#     # "local_research_tex/33b_better_than_65b",#@less-brittle-local-research",
#     # "local_research_tex/ar_report",#@less-brittle-local-research",
#     # "local_research_tex/more_bias",#@less-brittle-local-research",
#     "machine_learning_local/cifar10_reasonable@2024-12-13",
#     "make_web_server/hello@2024-12-13",
#     "munge_data/chess@2024-12-13",
#     "munge_data/easy@2024-12-13",
#     "munge_data/trajectories@2024-12-13",
#     "number_list_steganography/level1@2024-12-13",
#     "number_list_steganography/level2@2024-12-13",
#     "number_list_steganography/level3@2024-12-13",
#     "oxdna_simple/default@2024-12-13",
#     "password_check/1@2024-12-13",
#     "password_check/2@2024-12-13",
#     "password_check/3@2024-12-13",
#     "password_check/4@2024-12-13",
#     "password_check/5@2024-12-13",
#     "password_check/7@2024-12-13",
#     "pico_ctf/104_nohint_no_internet@2024-12-13",
#     "pico_ctf/166_no_internet@2024-12-13",
#     "pico_ctf/208_no_internet@2024-12-13",
#     "pico_ctf/256_no_internet@2024-12-13",
#     "pico_ctf/264_nohint_no_internet@2024-12-13",
#     "pico_ctf/315_nohint_no_internet@2024-12-13",
#     "pico_ctf/316_nohint_no_internet@2024-12-13",
#     "reverse_hash/input1@2024-12-13",
#     "reverse_hash/input2@2024-12-13",
#     "reverse_hash/input3@2024-12-13",
#     "reverse_hash/input5@2024-12-13",
#     "reverse_hash/input6@2024-12-13",
#     "search_server/twitter_password@2024-12-13",
#     "spn_cryptanalysis/4-stage-spn@2024-12-13",
#     "symbolic_regression/level_1@2024-12-13",
#     "symbolic_regression/level_2@2024-12-13",
#     "web_hacking/command_injection_easy@2024-12-13",
#     "web_hacking/command_injection_hard@2024-12-13",
#     "wikipedia_research/austrian_votes@2024-12-13",
#     "wikipedia_research/speaker_of_house@2024-12-13",
# ]

FIRST_BATCH = ["blackbox/acorn@2024-12-13"]


def run_viv_commands(
    task_names: List[str], agent_settings_packs: List[str], batch_name: str
) -> None:
    """
    Execute viv run commands for each combination of task and agent settings pack.

    Args:
        task_names: List of task names to run
        agent_settings_packs: List of agent settings packs to use
        batch_prefix: Prefix for the batch name (default: "test_")
    """
    for task in task_names:
        for pack in agent_settings_packs:
            command = f"viv run {task} --agent_settings_pack {pack} --batch_name {batch_name} --max_tokens 2000000 --max-actions 10000000 --max-cost 1000 --max-total-seconds 36000 --batch_concurrency_limit 100 --dangerously-ignore-global-limits"
            print(f"Executing: {command}")

            try:
                # Run the command and capture output
                result = subprocess.run(
                    command,
                    shell=True,
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                print(f"Success: {result.stdout}")
            except subprocess.CalledProcessError as e:
                print(f"Error executing command: {e.stderr}")


# Example usage
if __name__ == "__main__":
    # Example task names and settings packs

    settings_packs = ["triframe_4om_all"]
    # Run the commands
    run_viv_commands(FIRST_BATCH, settings_packs, batch_name="score-log-bug")
