import random
import hydra
import logging
import os
from omegaconf import DictConfig, OmegaConf
from PIL import Image, ImageDraw, ImageFont
import io
import datetime
import json
import numpy as np
import time
import shutil

from bgym import HighLevelActionSet
from browsergym.core.env import BrowserEnv
from browsergym.workarena import ATOMIC_TASKS
from agents import PromptAgent
from time import sleep
from browsergym.workarena.tasks import form, service_catalog, dashboard, knowledge

from browsergym.workarena.tasks import list as wa_list

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

def split_text(text, max_chars_per_line=90):
    # print(len(text))
    splitted = [text[i:i+max_chars_per_line] for i in range(0, len(text), max_chars_per_line)]
    for i in range(len(splitted)):
        if "\n" not in splitted[i]:
            splitted[i] += "\n"
    # print(splitted)
    return "".join(splitted)

def process_image(image_array: np.ndarray, circle_pos, caption, radius=10, font_size=28) -> Image.Image:
    '''
    画出 Agent 点击的位置，并以 caption 的形式展示模型的 action
    '''

    caption = split_text(caption)
    count = caption.count("\n")
    extension_height = min(55 * count, 1000)
    if count < 6:
        extension_height += 50

    # 将字节数据转换为Image对象
    original_img = Image.fromarray(image_array).convert("RGB")
    orig_width, orig_height = original_img.size

    # 创建新画布（原图高度 + 扩展区域高度）
    new_height = orig_height + extension_height
    new_img = Image.new("RGB", (orig_width, new_height), 'white')

    # 将原图粘贴到新画布顶部
    new_img.paste(original_img, (0, 0))
    
    # 创建绘图对象
    draw = ImageDraw.Draw(new_img)
    
    # 绘制圆圈
    if circle_pos is not None:
        x, y = circle_pos
        bbox = [(x - radius, y - radius), (x + radius, y + radius)]
        draw.ellipse(bbox, outline="red", width=5)

    try:
        # 尝试加载中文字体（根据系统调整路径）
        font = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", font_size)
    except IOError:
        print("Please install chinese font by `sudo apt install fonts-wqy-microhei`\nPlease install chinese font by `sudo apt install fonts-wqy-microhei`\nPlease install chinese font by `sudo apt install fonts-wqy-microhei`\nPlease install chinese font by `sudo apt install fonts-wqy-microhei`\nPlease install chinese font by `sudo apt install fonts-wqy-microhei`\nAnd then comment out this line")
        # 回退到默认字体（可能不支持中文）
        font = ImageFont.load_default().font_variant(size=font_size)
    
    # 计算文本尺寸
    bbox = draw.textbbox((0, 0), caption, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # 计算文字位置（在扩展区域居中）
    x_pos = (orig_width - text_width) // 2
    y_pos = orig_height + (extension_height - text_height) // 2
    
    # 添加字幕（带黑色描边）
    draw.text((x_pos, y_pos), caption, font=font, fill="black")

    return new_img

def setup_logger(task_name, task_result_dir, logger_name="runtime"):
    runtime_logger = logging.getLogger(f"{logger_name}.{task_name}")
    runtime_logger.setLevel(logging.DEBUG)
    runtime_logger.addHandler(logging.FileHandler(os.path.join(task_result_dir, f"{logger_name}.log")))
    return runtime_logger

@hydra.main(version_base=None, config_path=None, config_name=None)
def main(config: "DictConfig"):
    random.shuffle(ATOMIC_TASKS)
    # agent = PromptAgent(base_url="http://101.126.156.90:55890/v1", api_key="empty")
    for task in all_tasks:
        task = wa_list.SortAssetListTask
        print("Task:", task)

        # Instantiate a new environment
        env = BrowserEnv(task_entrypoint=task,
                        headless=False,
                        slow_mo=1000,
                        action_mapping=HighLevelActionSet("coord", "nav", "tab").to_python_code
                    )
        obs, info = env.reset()
        env.task.partial_validate(env.page)
        
        task_result_dir = os.path.join(
            config.result_dir,
            config.agent_name,
            task.__name__,
        )
        if os.path.exists(os.path.join(task_result_dir, "eval_result.json")):
            print(f"Task result directory {task_result_dir} already exists. Skipping...")
            continue
        if os.path.exists(task_result_dir):
            shutil.rmtree(task_result_dir)
            
        os.makedirs(task_result_dir, exist_ok=True)
        runtime_logger = setup_logger(task.__name__, task_result_dir)
        error_logger = setup_logger(task.__name__, task_result_dir, logger_name="error")
        agent.reset(runtime_logger, error_logger, task_result_dir)
        # runtime_logger.info(f"[Instruction] {instruction}")
        
        sleep(10)
        instruction = obs["goal"]
        # Cheat functions use Playwright to automatically solve the task
        env.chat.add_message(role="assistant", msg="On it. Please wait...")
        
        step_idx = 0
        done = False

        eval_record = {
            "step_num": 0,
            "action_num_per_step": [],
            "time_per_step": [],
            "reward": 0,
        }
        while step_idx < config.max_steps:
            step_idx += 1
            start = time.time()
            response, actions, coordinates = agent.predict(instruction, obs)  
            img = Image.fromarray(obs['screenshot']).convert("RGB")
            img.save(os.path.join(task_result_dir, f"step_{step_idx}.png"))
            for action, coordinate in zip(actions, coordinates):
                # Capture the timestamp before executing the action
                action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
                image = process_image(obs['screenshot'], coordinate, response)
                image.save(os.path.join(task_result_dir, f"step_{step_idx}_{action_timestamp}.png"))
                for a in action:
                    if a == "WAIT":
                        sleep(3)
                        continue
                    elif a in ["DONE", "FAIL"]:
                        done = True
                        break
                    retry_time = 3
                    while True:
                        try:
                            import pdb; pdb.set_trace()
                            obs, reward, terminated, truncated, info = env.step(a)
                            break
                        except Exception as e:
                            retry_time -= 1
                            if retry_time == 0:
                                raise e
                            continue
                    if terminated:
                        done = True
                        break
                if done:
                    break
            end = time.time()
            eval_record["time_per_step"].append(end-start)
            eval_record["action_num_per_step"].append(len(actions))
            if done:
                break
        eval_record["step_num"] = step_idx

        # Post solution to chat
        env.chat.add_message(role="assistant", msg="I'm done!")

        # Validate the solution
        reward, stop, message, info = env.task.validate(env.page, env.chat.messages)
        if reward == 1:
            env.chat.add_message(role="user", msg="Yes, that works. Thanks!")
        else:
            env.chat.add_message(role="user", msg=f"No, that doesn't work. {info.get('message', '')}")
            

        eval_record["reward"] = reward
        with open(os.path.join(task_result_dir, "eval_result.json"), "w") as f:
            f.write(json.dumps(eval_record, indent=4))

        sleep(3)
        env.close()
        
if __name__ == "__main__":
    main()