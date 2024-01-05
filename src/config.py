import json
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

from pydantic import BaseModel, Field


def setup_logger():
    if not os.path.exists("log"):
        os.mkdir("log")
    log_file = "log/run.log"
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d - %(funcName)1s() ] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 创建一个 handler，用于写入日志文件，每小时更换一次文件
    handler = TimedRotatingFileHandler(log_file, when="H", interval=1, backupCount=5, encoding="utf-8")
    handler.setFormatter(formatter)

    # 创建一个 handler，用于将日志输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 获取或创建一个 logger
    my_logger = logging.getLogger("kinoko7danmaku")
    my_logger.setLevel(logging.INFO)
    my_logger.addHandler(handler)
    my_logger.addHandler(console_handler)


if "gInit" not in globals():
    setup_logger()
    gInit = True

logger = logging.getLogger("kinoko7danmaku")


# 定义模型，包含默认值
class ConfigModel(BaseModel):
    room_id: int = Field(default=213, description="房间号")
    gift_threshold: int = Field(default=5, description="≥这个值（单位：元）才会触发礼物")
    api_url: str = Field(default="", description="API地址，注意要带最后的 /")
    alias: dict = Field(default={}, description="别名，用于替换一些词语，例如：{'Merlin':'么林'}")
    normal_danmaku_on: bool = Field(default=True, description="普通弹幕是否触发")
    guard_on: bool = Field(default=True, description="舰长是否触发")
    super_chat_on: bool = Field(default=True, description="醒目留言是否触发")
    voice_name: str = Field(default="C酱", description="模型名")
    voice_channel: int = Field(default=-1, description="声道，默认-1为系统输出，如果有声卡，可以自行修改")
    debug: bool = Field(default=False, description="是否开启调试模式，不开启就行了")


# 读取或创建配置
def load_or_create_config(filename: str) -> ConfigModel:
    if not os.path.exists(filename):
        logger.info(f"{filename} 不存在，正在创建并初始化...")
        config = create_config_interactively({})
        save_config(filename, config)
    else:
        with open(filename, "r", encoding='utf8') as file:
            data = json.load(file)
        # 检查并填充缺失的值
        config = create_config_interactively(data)
        save_config(filename, config)
    return config


# 与用户交互以获取配置
def create_config_interactively(config_data: dict) -> ConfigModel:
    if len(config_data) != len(ConfigModel.model_fields):
        print("请按提示输入配置信息，直接回车则使用默认值")
    for field_name, field in ConfigModel.model_fields.items():
        if field_name not in config_data or config_data[field_name] is None:
            while True:
                sys.stdout.flush()
                # 检查字段类型是否为布尔型
                if isinstance(field.default, bool):
                    user_input = input(
                        f"请输入{field_name}（{field.description}）【y/n，默认值：{'y' if field.default else 'n'}】：").lower()
                    if user_input in ["", "y", "n"]:
                        user_input = (user_input.lower() == "y") if user_input else field.default
                        config_data[field_name] = user_input
                        break
                    else:
                        print("请输入 'y' 或 'n'")
                elif isinstance(field.default, dict):
                    config_data[field_name] = field.default
                    break
                elif isinstance(field.default, str):
                    user_input = input(
                        f"请输入{field_name}（{field.description}）【默认值：{field.default if field.default else '空'}】：") or field.default
                    try:
                        config_data[field_name] = str(user_input)
                        break
                    except ValueError:
                        print(f"输入的值类型不正确，请重新输入 {field_name}")
                else:
                    user_input = input(
                        f"请输入{field_name}（{field.description}）【默认值：{field.default}】：") or field.default
                    # 转换为正确的类型
                    correct_type = type(field.default)
                    try:
                        config_data[field_name] = correct_type(user_input)
                        break
                    except ValueError:
                        print(f"输入的值类型不正确，请重新输入 {field_name}")
    return ConfigModel(**config_data)


# 保存配置到文件
def save_config(filename: str, config: ConfigModel):
    with open(filename, "w", encoding="utf8") as file:
        json.dump(config.model_dump(), file, indent=4, ensure_ascii=False)


if "gConfig" not in globals():
    logger.info("正在读取配置...")
    gConfig = load_or_create_config("config.json")
    if not os.path.exists("cookies.json"):
        os.system(r"bin\biliup.exe login")
        if not os.path.exists("cookies.json"):
            logger.error("登录失败")
            exit(-1)
    logger.info("当前配置：")
    logger.info(gConfig.model_dump())
    if gConfig.alias:
        logger.info("当前别名：")
        for k, v in gConfig.alias.items():
            logger.info(f"{k} -> {v}")
    else:
        logger.info("当前别名：无")


def get_config() -> ConfigModel:
    return gConfig
