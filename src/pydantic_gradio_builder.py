import json
from typing import Any, get_origin

import gradio as gr
from loguru import logger
from pydantic import BaseModel

from bilibili.bili_service import get_bili_service
from config import TTSConfig


class PydanticGradioBuilder:
    """基于Pydantic模型的Gradio界面构建器"""

    def __init__(self, model_class: type[BaseModel]):
        self.model_class = model_class
        self.field_info = model_class.model_fields
        self.field_names = list(self.field_info.keys())

    def create_component(self, field_name: str, current_value: Any):
        """为指定字段创建Gradio组件"""
        if field_name not in self.field_info:
            raise ValueError(f"Field '{field_name}' not found in model")

        field = self.field_info[field_name]
        if field.annotation is int:
            return gr.Number(
                label=field.title,
                value=current_value,
                precision=0,
                info=field.description,
            )
        elif field.annotation is str:
            return gr.Textbox(
                label=field.title,
                value=current_value,
                placeholder=field.default if field.default != ... else "",
                info=field.description,
            )
        elif field.annotation is bool:
            return gr.Checkbox(
                label=field.title,
                value=current_value,
                info=field.description,
            )
        elif get_origin(field.annotation) is dict:
            return gr.Code(
                label=field.title,
                value=json.dumps(current_value, ensure_ascii=False, indent=4),
                language="python",
            )
        else:
            # 默认处理
            return gr.Textbox(
                label=field.title,
                value=str(current_value),
                info=field.description,
            )

    def create_update_function(self, config_manager):
        """创建配置更新函数"""

        async def update_config(*args) -> tuple:
            config_dict = dict(zip(self.field_names, args))

            # 处理字典字段 - 从Code文本框中解析值
            for field_name, field in self.field_info.items():
                if get_origin(field.annotation) is dict:
                    # 从Code文本框中获取值
                    code_value = config_dict.get(field_name, "{}")
                    try:
                        # 尝试解析JSON格式的字符串
                        dict_value = (
                            json.loads(code_value) if code_value.strip() else {}
                        )
                        if not isinstance(dict_value, dict):
                            raise ValueError("不是有效的字典格式")
                    except (json.JSONDecodeError, ValueError) as e:
                        gr.Error(f"字段 '{field.title}' 的JSON格式有误: {str(e)}")
                        return args
                    config_dict[field_name] = dict_value

            config: TTSConfig = self.model_class(**config_dict)

            # 自定义验证逻辑
            config_dict_check = config.model_dump()
            if (
                "api_url" in config_dict_check
                and not config_dict_check["api_url"].strip()
            ):
                gr.Error("API URL 不能为空")
                return args

            if "room_id" in config_dict_check and config_dict_check["room_id"] <= 0:
                gr.Error("房间号必须大于0")
                return args

            if config.room_id != config_manager.config.room_id:
                logger.info(f"房间号已更改，重新连接直播间: {config.room_id}")
                bili_service = get_bili_service()
                await bili_service.reload(config.room_id)

            success = config_manager.update_config(config)

            if success:
                gr.Info("配置已成功保存")
                config_values = config.model_dump()
                # 为字典字段返回JSON字符串
                return_values = []
                for field in self.field_names:
                    value = config_values[field]
                    if get_origin(self.field_info[field].annotation) is dict:
                        return_values.append(
                            json.dumps(value, ensure_ascii=False, indent=4)
                        )
                    else:
                        return_values.append(value)
                return tuple(return_values)
            else:
                gr.Error("保存配置失败")
                return args

        return update_config
