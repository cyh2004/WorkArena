# The following codes are based on OSWorld(https://github.com/xlang-ai/OSWorld/tree/main).
# For codes from mm_agents, please refer to the original OSWorld repository.

import base64
import json
import logging
import os
from io import BytesIO
from typing import Dict, List
import copy
from PIL import Image
import math
from openai import OpenAI

from .action_parser import (
    parse_action_qwen2vl,
    parsing_response_to_workarena_action,
    FINISH_WORD,
    WAIT_WORD,
    ENV_FAIL_WORD,
    CALL_USER
)

# Function to encode the image
def encode_image(image_content):
    return base64.b64encode(image_content).decode("utf-8")

def pil_to_base64(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")  # 你可以改成 "JPEG" 等格式
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

class PromptAgent:
    def __init__(
        self,
        base_url,
        api_key,
        max_tokens=1000,
        top_p=0.9,
        temperature=0.0,
        input_swap=False,
        max_steps=50,
        history_n=5,
    ):
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.temperature = temperature
        self.vlm = OpenAI(
            base_url=base_url,
            api_key=api_key,
        ) # should replace with your UI-TARS server api
        models = self.vlm.models.list()
        self.model = models.data[0].id
        self.input_swap = input_swap
        self.max_steps = max_steps

        self.actions = []
        self.history_images = []
        self.history_responses = []
        self.history_n = history_n
        
        self.customize_action_parser = parse_action_qwen2vl
        self.action_parse_res_factor = 1000

    def predict(self, instruction: str, obs: Dict) -> List:
        """
        Predict the next action(s) based on the current observation.
        """
        # type(obs['screenshot']) == <class 'numpy.ndarray'>
        self.history_images.append(obs["screenshot"])

        if len(self.history_images) > self.history_n:
            self.history_images = self.history_images[-self.history_n:]

        max_pixels = 1350 * 28 * 28
        min_pixels = 100 * 28 * 28
        messages, images = [], []
        max_image_nums_under_32k = int(32768*0.75/max_pixels*28*28)
        if len(self.history_images) > max_image_nums_under_32k:
            num_of_images = min(5, len(self.history_images))
            max_pixels = int(32768*0.75) // num_of_images
        for turn, image in enumerate(self.history_images):
            if len(images) >= 5:
                break
            try:
                image = Image.fromarray(obs['screenshot'])
            except Exception as e:
                raise RuntimeError(f"Error opening image: {e}")

            if image.width * image.height > max_pixels:
                """
                如果图片超过/低于像素限制，则计算一个缩放因子resize_factor，使图片的像素数缩小到等于或小于max_pixels。这个缩放因子是通过开平方根计算的，确保纵横比保持不变,这样原始的相对坐标可以不经转换直接复用
                """
                resize_factor = math.sqrt(max_pixels / (image.width * image.height))
                width, height = int(image.width * resize_factor), int(image.height * resize_factor)
                image = image.resize((width, height))
            if image.width * image.height < min_pixels:
                resize_factor = math.sqrt(min_pixels / (image.width * image.height))
                width, height = math.ceil(image.width * resize_factor), math.ceil(image.height * resize_factor)
                image = image.resize((width, height))

            if image.mode != "RGB":
                image = image.convert("RGB")
                
            width, height = image.size

            images.append(image)
            
        user_prompt = f"""You are a GUI agent. You are given a task and your action history, with screenshots. You need to perform the next action to complete the task.

        ## Output Format
        ```
        Thought: ...
        Action: ...
        ```

        ## Action Space

        click(start_box='<|box_start|>(x1,y1)<|box_end|>')
        left_double(start_box='<|box_start|>(x1,y1)<|box_end|>')
        right_single(start_box='<|box_start|>(x1,y1)<|box_end|>')
        drag(start_box='<|box_start|>(x1,y1)<|box_end|>', end_box='<|box_start|>(x3,y3)<|box_end|>')
        hotkey(key='')
        type(content='xxx') # Use escape characters \\', \\\", and \\n in content part to ensure we can parse the content in normal python string format. If you want to submit your input, use \\n at the end of content. 
        scroll(start_box='<|box_start|>(x1,y1)<|box_end|>', direction='down or up or right or left')
        wait() #Sleep for 5s and take a screenshot to check for any changes.
        finished(content='xxx') # Use escape characters \\', \\", and \\n in content part to ensure we can parse the content in normal python string format.


        ## Note
        - Use English in `Thought` part.
        - Write a small plan and finally summarize your next action (with its target element) in one sentence in `Thought` part.

        ## User Instruction
        {instruction}
        """

        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": "You are a helpful assistant."}]
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": user_prompt}]
            }
        ]
        
        image_num = 0
        if len(self.history_responses) > 0:
            for history_idx, history_response in enumerate(self.history_responses):
                # send at most history_n images to the model
                if history_idx + self.history_n > len(self.history_responses):

                    cur_image = images[image_num]
                    encoded_string = pil_to_base64(cur_image)
                    messages.append({
                        "role": "user",
                        "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_string}"}}]
                    })
                    image_num += 1
                    
                messages.append({
                    "role": "assistant",
                    "content": [{"type": "text", "text": history_response}]
                })

            cur_image = images[image_num]
            encoded_string = pil_to_base64(cur_image)
            messages.append({
                "role": "user",
                "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_string}"}}]
            })
            image_num += 1
        
        else:
            cur_image = images[image_num]
            encoded_string = pil_to_base64(cur_image)
            messages.append({
                "role": "user",
                "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_string}"}}]
            })
            image_num += 1

        try_times = 3
        # import pdb;pdb.set_trace()
        while True:
            if try_times <= 0:
                print(f"Reach max retry times to fetch response from client, as error flag.")
                return "client error", [["DONE"]], [None]
            try:
                
                response = self.vlm.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    frequency_penalty=1,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )
                prediction = response.choices[0].message.content.strip()
                print("[PromptAgent] Prediction: ", prediction)
                log_messages = copy.deepcopy(messages)
                image_num = len(self.actions)
                for msg in reversed(log_messages):
                    for c in msg["content"]:
                        if "image_url" in c.keys():
                            c["image_url"]["url"] = f"step_{image_num}.png"
                            image_num -= 1
                log_messages.append({"prediction": prediction})
                json.dump(log_messages, open(os.path.join(self.task_result_dir, f"message_{len(self.actions)}.json"), "w"), indent=2)
                
                break
            except Exception as e:
                print(f"Error when fetching response from client, with error: {e}")
                self.error_logger.error(f"Error when fetching response from client: {e}")
                prediction = None
                try_times -= 1
                
        if prediction is None:
            return "client error", [["DONE"]], [None]
        
        self.history_responses.append(prediction)
        self.runtime_logger.info(f"[Step {len(self.actions) + 1}] {prediction}\n")
        try:
            parsed_responses = self.customize_action_parser(
                prediction,
                self.action_parse_res_factor,
                height,
                width
            )
        except Exception as e:
            print(f"Parsing action error: {prediction}, with error:\n{e}")
            self.error_logger.error(f"Parsing action error: {prediction}, with error:\n{e}")
            import traceback
            traceback.print_exc()
            return f"Parsing action error: {prediction}, with error:\n{e}", [["DONE"]], [None]
        actions = []
        coordinates = []
        for parsed_response in parsed_responses:
            if "action_type" in parsed_response:

                if parsed_response["action_type"] == FINISH_WORD:
                    self.actions.append(actions)
                    return prediction, actions + [["DONE"]], coordinates + [None]
                
                elif parsed_response["action_type"] == WAIT_WORD:
                    self.actions.append(actions)
                    return prediction, actions + [["WAIT"]], coordinates + [None]
                
                elif parsed_response["action_type"] == ENV_FAIL_WORD:
                    self.actions.append(actions)
                    return prediction, actions + [["FAIL"]], coordinates + [None] 

                elif parsed_response["action_type"] == CALL_USER:
                    self.actions.append(actions)
                    return prediction, actions + [["FAIL"]], coordinates + [None] 
            
            try:
                parsed_actions, coordinate = parsing_response_to_workarena_action(
                    parsed_response,
                    height,
                    width,
                    self.input_swap
                )
            except ValueError as e:
                print(f"Parsing action error: {parsed_response}, with error:\n{e}")
                self.error_logger.error(f"Parsing action error: {parsed_response}, with error:\n{e}")
                import traceback
                traceback.print_exc()
                return f"Parsing action error: {parsed_response}, with error:\n{e}", [["DONE"]], [None]
            actions_to_log = "\n".join(parsed_actions)
            self.runtime_logger.info(f"[Code] {actions_to_log}\n")
            
            actions.append(parsed_actions)
            coordinates.append(coordinate)

        self.actions.append(actions)
        if len(self.history_responses) >= self.max_steps: ### 一直到最后一步的时候就会fail（这样会导致一些case里最后在动作但是为fail，这也导致实际的序列长度是由这个max_traj所决定的）
            # Default to FAIL if exceed max steps
            actions += [["FAIL"]]

        return prediction, actions, coordinates

    def reset(self, runtime_logger, error_logger, task_result_dir):
        self.actions = []
        self.history_images = []
        self.history_responses = []
        self.runtime_logger = runtime_logger
        self.error_logger = error_logger
        self.task_result_dir = task_result_dir