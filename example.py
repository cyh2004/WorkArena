import random

from browsergym.core.env import BrowserEnv
from browsergym.workarena import ALL_WORKARENA_TASKS
from time import sleep
from browsergym.workarena import get_all_tasks_agents

L1_TASK = get_all_tasks_agents(filter="l1")

for task in L1_TASK:
    (task, seed) = task
    print("Task:", task)

    # Instantiate a new environment
    env = BrowserEnv(task_entrypoint=task,
                    headless=False)
    import pdb; pdb.set_trace()
    env.reset()

    # Cheat functions use Playwright to automatically solve the task
    env.chat.add_message(role="assistant", msg="On it. Please wait...")
    cheat_messages = []
    env.task.cheat(env.page, cheat_messages)

    # Send cheat messages to chat
    for cheat_msg in cheat_messages:
        env.chat.add_message(role=cheat_msg["role"], msg=cheat_msg["message"])

    # Post solution to chat
    env.chat.add_message(role="assistant", msg="I'm done!")

    # Validate the solution
    reward, stop, message, info = env.task.validate(env.page, cheat_messages)
    if reward == 1:
        env.chat.add_message(role="user", msg="Yes, that works. Thanks!")
    else:
        env.chat.add_message(role="user", msg=f"No, that doesn't work. {info.get('message', '')}")

    sleep(3)
    env.close()