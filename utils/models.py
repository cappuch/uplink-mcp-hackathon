import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
from utils.prompts import EXTRACT_PROMPT, BIAS_PROMPT, RANDOM_EXTRACT_PROMPT
import numpy as np
import re

load_dotenv()

api_key = os.environ.get("HF_TOKEN")
embedding_model = os.environ.get("EMBEDDING_MODEL")
extraction_model = os.environ.get("EXTRACTION_MODEL")
extraction_model_provider = os.environ.get("EXTRACTION_MODEL_PROVIDER", "auto")

embed_client = InferenceClient(
    provider="auto",
    api_key=api_key,
)

extraction_client = InferenceClient(
    provider=extraction_model_provider,
    api_key=os.environ["HF_TOKEN"],
)

def completion(messages: list) -> dict:
    result = extraction_client.chat.completions.create(
        model=extraction_model,
        messages=messages,
        temperature=0.1
    )
    return result.choices[0].message

def embed_text(text: str) -> list:
    result = embed_client.feature_extraction(
        text=text,
        model=embedding_model,
    )
    if hasattr(result, 'tolist'):
        return result.tolist()
    elif isinstance(result, (list, tuple)):
        return list(result)
    else:
        if isinstance(result, np.ndarray):
            return result.tolist()
        else:
            return list(result)

def extract(text: str, mode: str = None) -> str:
    if mode == "random":
        messages = [
            {"role": "system", "content": RANDOM_EXTRACT_PROMPT},
            {"role": "user", "content": text}
        ]
    else:
        messages = [
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": text},
        ]
    result = completion(messages)
    content = result.content
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    return content.strip()

def bias_to_number(bias: str) -> int:
    bias_map = {
        "left": -2,
        "slightly left": -1,
        "neutral": 0,
        "slightly right": 1,
        "right": 2,
    }
    return bias_map.get(bias, 0)

def bias(text: str) -> str:
    messages = [
        {"role": "system", "content": BIAS_PROMPT},
        {"role": "user", "content": text},
    ]
    result = completion(messages)
    content = result.content.lower()
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    return bias_to_number(content.strip())