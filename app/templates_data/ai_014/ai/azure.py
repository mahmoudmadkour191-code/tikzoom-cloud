import base64
import requests
from typing import Optional
from io import BytesIO

from openai import AzureOpenAI
from db.MySqlConn import config
from ai import OPENAI_CHAT_COMPLETION_OPTIONS


class AzureAIClient:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=config["AI"]["CHAT_TOKEN"],
            azure_endpoint=config["AI"]["CHAT_BASE"],
            api_version=config["AI"]["CHAT_VERSION"]
        )
        self.image_client = AzureOpenAI(
            api_key=config["AI"]["IMAGE_TOKEN"],
            azure_endpoint=config["AI"]["IMAGE_BASE"],
            api_version=config["AI"]["IMAGE_VERSION"]
        )

    def generate_image(self, prompt: str, size: str = "1024x1024", quality: str = "medium", n: int = 1) -> bytes:
        ai_config = config["AI"]
        endpoint = ai_config["IMAGE_BASE"].rstrip("/")
        deployment = ai_config["IMAGE_MODEL"]
        api_version = ai_config["IMAGE_VERSION"]
        api_key = ai_config["IMAGE_TOKEN"]

        url = f"{endpoint}/openai/deployments/{deployment}/images/generations?api-version={api_version}"

        response = requests.post(
            url,
            headers={
                "Api-Key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "prompt": prompt,
                "n": n,
                "size": size,
                "quality": quality,
                "output_format": "png",
            },
            timeout=120,
        )
        response.raise_for_status()

        return base64.b64decode(response.json()["data"][0]["b64_json"])
    
    def edit_image(
        self,
        prompt: str,
        image_data: bytes,
        mask_data: Optional[bytes] = None,
        size: str = "1024x1024",
        quality: str = "medium",
        n: int = 1
    ) -> bytes:
        ai_config = config["AI"]
        endpoint = ai_config["IMAGE_BASE"].rstrip("/")
        deployment = ai_config["IMAGE_MODEL"]
        api_version = ai_config["IMAGE_VERSION"]
        api_key = ai_config["IMAGE_TOKEN"]

        url = f"{endpoint}/openai/deployments/{deployment}/images/edits?api-version={api_version}"

        data = {
            "prompt": prompt,
            "n": n,
            "size": size,
            "quality": quality,
        }

        files = {
            "image": ("image.png", BytesIO(image_data), "image/png"),
        }
        if mask_data:
            files["mask"] = ("mask.png", BytesIO(mask_data), "image/png")

        response = requests.post(
            url,
            headers={"Api-Key": api_key},
            data=data,
            files=files,
            timeout=120,
        )
        response.raise_for_status()

        return base64.b64decode(response.json()["data"][0]["b64_json"])

    def chat_completions(self, messages: list):
        completion = self.client.chat.completions.create(
            model=OPENAI_CHAT_COMPLETION_OPTIONS["model"],
            messages=messages
        )
        # print(completion.choices[0].message)
        return completion
