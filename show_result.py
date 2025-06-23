import os
import json

def show_result(base_dir, run_name):
    dir = os.path.join(base_dir, run_name)
    tasks = os.listdir(dir)
    all_reward = 0.0
    all_tasks = 0
    total_actions = 0
    total_steps = 0
    no_action_steps = 0
    total_time = 0.0
    right_total_actions = 0
    right_total_steps = 0
    right_no_action_steps = 0
    right_total_time = 0.0
    for t in tasks:
        path = os.path.join(dir, t)
        if os.path.isdir(path):
            try:
                eval_result = json.load(open(os.path.join(path, "eval_result.json")))
            except Exception as e:
                continue
            reward = eval_result["reward"]
            all_reward += reward
            all_tasks += 1
            total_actions += sum(eval_result["action_num_per_step"])
            total_steps += len(eval_result["action_num_per_step"])
            no_action_steps += eval_result["action_num_per_step"].count(0)
            total_time += sum(eval_result["time_per_step"])
            if reward == 1.0:
                right_total_actions += sum(eval_result["action_num_per_step"])
                right_total_steps += len(eval_result["action_num_per_step"])
                right_no_action_steps += eval_result["action_num_per_step"].count(0)
                right_total_time += sum(eval_result["time_per_step"])
                
    
    print(f"Result for {run_name}: {all_reward} / {all_tasks} = {all_reward/all_tasks}")
    print(f"avg action num per step: {total_actions} / {total_steps} = {total_actions/total_steps}")
    print(f"avg action num per step with action: {total_actions} / {total_steps} - {no_action_steps} = {total_actions/(total_steps - no_action_steps)}")
    print(f"avg time per action: {total_time} / {total_actions} = {total_time/total_actions}")
    print(f"avg right action num per step: {right_total_actions} / {right_total_steps} = {right_total_actions/right_total_steps}")
    print(f"avg right action num per step with action: {right_total_actions} / {right_total_steps} - {right_no_action_steps} = {right_total_actions/(right_total_steps - right_no_action_steps)}")
    print(f"avg right time per action: {right_total_time} / {right_total_actions} = {right_total_time/right_total_actions}")

if __name__ == "__main__":
    
    show_result("results", "uitars-7b-sft-lora-debug")