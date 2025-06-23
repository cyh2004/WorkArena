"""
A demonstration of how observation/action traces can be extracted
for WorkArena tasks without modifying the task code.

Author: Alexandre Drouin (alexandre.drouin@servicenow.com)

Notes:
- This approach relies on monkey patching the playwright actions to log the actions and observations.
  It has not been tested for parallel execution. It might work with multiprocessing, but it will for
  sure not work with multithreading.

"""

import importlib
import logging
import os
import pickle
from time import sleep
import json
import playwright.sync_api as playwright_sync
import pyautogui
import numpy as np

from browsergym.core.env import BrowserEnv
from browsergym.workarena import ALL_WORKARENA_TASKS
from collections import defaultdict
from tenacity import retry, stop_after_attempt, wait_fixed
from time import time
from PIL import Image
from browsergym.workarena import get_all_tasks_agents
from browsergym.workarena.tasks import form, service_catalog, dashboard, knowledge
from browsergym.workarena.tasks import list as wa_list
from browsergym.workarena.tasks import knowledge
from browsergym.workarena.tasks import service_catalog, dashboard
from browsergym.core.action.highlevel import HighLevelActionSet

all_tasks = [
    wa_list.FilterAssetListTask,
    wa_list.FilterChangeRequestListTask,
    wa_list.FilterHardwareListTask,
    wa_list.FilterServiceCatalogItemListTask,
    wa_list.FilterUserListTask,
    wa_list.SortAssetListTask,
    wa_list.SortChangeRequestListTask,
    wa_list.SortHardwareListTask,
    wa_list.SortIncidentListTask,
    wa_list.SortServiceCatalogItemListTask,
    wa_list.SortUserListTask,
    form.CreateIncidentTask,
    form.CreateHardwareAssetTask,
    form.CreateProblemTask,
    form.CreateUserTask,
    form.CreateChangeRequestTask,
    service_catalog.OrderDeveloperLaptopTask,
    service_catalog.OrderIpadMiniTask,
    service_catalog.OrderIpadProTask,
    service_catalog.OrderSalesLaptopTask,
    service_catalog.OrderStandardLaptopTask,
    service_catalog.OrderAppleWatchTask,
    service_catalog.OrderAppleMacBookPro15Task,
    service_catalog.OrderDevelopmentLaptopPCTask,
    service_catalog.OrderLoanerLaptopTask
]

filter_tasks = [
    wa_list.FilterAssetListTask,
    wa_list.FilterChangeRequestListTask,
    wa_list.FilterHardwareListTask,
    wa_list.FilterServiceCatalogItemListTask,
    wa_list.FilterUserListTask,
]

sort_tasks1 = [
    wa_list.SortAssetListTask,
    wa_list.SortChangeRequestListTask,
    wa_list.SortHardwareListTask,
]

sort_tasks2 = [
    wa_list.SortIncidentListTask,
    wa_list.SortServiceCatalogItemListTask,
    wa_list.SortUserListTask,
]

form_tasks1 = [
    form.CreateIncidentTask,
    form.CreateHardwareAssetTask,
]

form_tasks2 = [
    form.CreateProblemTask,
    form.CreateUserTask
]

form_tasks3 = [
    form.CreateChangeRequestTask,
]

service_tasks = [
    service_catalog.OrderDeveloperLaptopTask,
    service_catalog.OrderIpadMiniTask,
    service_catalog.OrderIpadProTask,
    service_catalog.OrderSalesLaptopTask,
    service_catalog.OrderStandardLaptopTask,
    service_catalog.OrderAppleWatchTask,
    service_catalog.OrderAppleMacBookPro15Task,
    service_catalog.OrderDevelopmentLaptopPCTask,
    service_catalog.OrderLoanerLaptopTask
]

dashboard_tasks = [
    dashboard.SingleChartValueRetrievalTask,
    dashboard.SingleChartMinMaxRetrievalTask,
    dashboard.MultiChartValueRetrievalTask,
    dashboard.MultiChartMinMaxRetrievalTask,
]

kb_tasks = [
    knowledge.KnowledgeBaseSearchTask
]

L1_TASK = get_all_tasks_agents(filter="l1")

N_PER_TASK = 10


def monkey_patch_playwright(observation_callback, trace_storage):
    """
    A function that overrides the default playwright actions to log the actions and observations.

    Parameters:
    ------------
    observation_callback: callable
        A function that returns the observation of the environment.
    trace_storage: list
        A list to store the trace of the actions and observations.
        These will be appended in-place.

    """

    def wrapper(func, interface):
        def wrapped(*arguments, **kwargs):
            import pdb; pdb.set_trace()
            perform = kwargs.pop("perform", True)
            record = kwargs.pop("record", True)
            press_last_char = kwargs.pop("press_last_char", False)
            use_pyautogui = kwargs.pop("use_pyautogui", False)
            empty = kwargs.pop("empty", False)
            # Temporarily set to False
            use_pyautogui = False
            if use_pyautogui:
                screenshot = pyautogui.screenshot(region=(73, 105, 1280, 720))

            # Get the observation
            obs = observation_callback()

            if empty:
                trace_storage.append(
                    {
                        "obs": obs,
                        "action": "empty",
                        "args": (),
                        "kwargs": {},
                        "bid": "empty",
                        "time": time(),
                    }
                )
                return
            
            if use_pyautogui:
                # img = Image.fromarray(obs["screenshot"])
                # img.paste(screenshot, (0, 0))
                obs["screenshot"] = np.array(screenshot)

            # Get the BID of the element on which we are acting.
            if interface.__name__ == "Locator":
                # Get the locator
                locator = arguments[0]
                # Get the BID
                bid = locator.element_handle().evaluate('(el) => el.getAttribute("bid")')
            elif interface.__name__ == "Keyboard":
                # Get the BID of the element
                bid = "keyboard"
            elif interface.__name__ == "Mouse":
                # Get the BID of the element
                bid = "mouse"
            else:
                # Get the BID of the element
                bid = arguments[0].evaluate('(el) => el.getAttribute("bid")')
            if record:
                if func.__name__ == "click":
                    if bid == "mouse":
                        x = arguments[1]
                        y = arguments[2]
                    else:
                        extra_props = obs["extra_element_properties"][bid]
                        assert extra_props["visibility"]
                        bbox = extra_props["bbox"]
                        x = bbox[0] + bbox[2] / 2
                        y = bbox[1] + bbox[3] / 2
                    img = Image.fromarray(obs["screenshot"])
                    width, height = img.size
                    x_rel = int(x / width * 1000)
                    y_rel = int(y / height * 1000)
                    print(f"Action: click({x} / {width} = {x_rel}, {y} / {height} = {y_rel})")
                    trace_storage.append(
                        {
                            "obs": obs,
                            "action": func.__name__,
                            "args": (x, y),
                            "kwargs": kwargs,
                            "bid": bid,
                            "time": time(),
                        }
                    )
                elif func.__name__ == "fill":
                    trace_storage.append(
                        {
                            "obs": obs,
                            "action": "type",
                            "args": (arguments[1],),
                            "kwargs": kwargs,
                            "bid": bid,
                            "time": time(),
                        }
                    )
                
                elif func.__name__ == "press":
                    if press_last_char:
                        trace_storage[-1]["args"] = (trace_storage[-1]["args"][0] + arguments[1],)
                    else:
                        trace_storage.append(
                            {
                                "obs": obs,
                                "action": "hotkey",
                                "args": (arguments[1],),
                                "kwargs": kwargs,
                                "bid": bid,
                                "time": time(),
                            }
                        )
                
                elif func.__name__ == "wheel":
                    x = arguments[1]
                    y = arguments[2]
                    trace_storage.append(
                        {
                            "obs": obs,
                            "action": func.__name__,
                            "args": (x, y),
                            "kwargs": kwargs,
                            "bid": bid,
                            "time": time(),
                        }
                    )

                elif func.__name__ == "select_option":
                    options = arguments[0].locator("option").all()
                
                    print("num options: ", len(options))
                    for op in options:
                        if op.text_content() == arguments[1]:
                            bid = op.evaluate('(el) => el.getAttribute("bid")')
                            print("option selected: ", op.text_content(), " ", bid)
                            break
            print(f"Action: {func.__name__} BID: {bid}  --   args: {arguments[1:]} {kwargs} {perform}, {record}")

            if perform:
                # Resume action
                return func(*arguments, **kwargs)

        return wrapped

    # Interfaces and actions we want to monkey patch
    importlib.reload(playwright_sync)
    from playwright.sync_api import Page, Frame, Locator, Keyboard, ElementHandle, Mouse

    # TODO: Make sure the list of interfaces and actions is exhaustive
    #       It covers all that is used in WorkArena cheats as of April 11, 2024
    interfaces = [Page, Frame, Locator, Keyboard, ElementHandle, Mouse]
    actions = ["click", "select_option", "set_checked", "fill", "press", "type", "down", "up", "move", "wheel"]

    for interface in interfaces:
        for action in actions:
            if hasattr(interface, action):
                if not hasattr(interface, "origin_" + action):
                    setattr(interface, "origin_" + action, getattr(interface, action))
                setattr(interface, action, wrapper(getattr(interface, "origin_" + action), interface))
                # print(f"Monkey patched {interface.__name__}.{action}")


# @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def extract_trace(task_cls, headless=True, seed=None):
    """
    Extracts the trace of actions and observations for a given task.

    Parameters:
    ------------
    task_cls: class
        The class of the task to extract the trace from.

    """
    # Instantiate a new environment
    env = BrowserEnv(task_entrypoint=task_cls, 
                     headless=headless, 
                     slow_mo=1000, 
                     action_mapping=HighLevelActionSet(["chat", "infeas", "nav", "tab", "coord", "bid"]).to_python_code,
                     )
    

    # Setup customized tracing
    trace = []
    monkey_patch_playwright(observation_callback=env._get_obs, trace_storage=trace)

    obs, info = env.reset(seed=seed)
    print(obs["goal"])
    sleep(5)
    env.task.cheat(env.page, env.chat.messages)

    obs = env._get_obs()
    trace.append(
        {
            "obs": obs,
            "action": "finish",
            "args": (),
            "kwargs": {},
            "bid": "finish",
            "time": time(),
        }
    )

    sleep(5)
    env.close()

    return trace


if __name__ == "__main__":
    os.makedirs("trace_profiling", exist_ok=True)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    for j in range(10):

        task_traces = defaultdict(list)
        try:
            for task in all_tasks:
                for i in range(2):
                    print("Task:", task)
                    trace = extract_trace(task, headless=False, seed=114514+i)
                    print(f"Trace length: {len(trace)}")
                    task_traces[task].append(trace)
        finally:
            # pickle.dump(task_traces, open(f"trace_profiling/SFTData{j}.pkl", "wb"))
            pass
