from config import gConfig


def pre_format(input_text: str) -> str:
    if not gConfig.alias:
        return input_text
    for k, v in gConfig.alias.items():
        input_text = input_text.lower().replace(k.lower(), v)
    return input_text
