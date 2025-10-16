import re


def remove_reasoning_trace(text: str) -> str:
    return re.sub(r"<think>.+<\/think>", "", text, flags=re.DOTALL)
