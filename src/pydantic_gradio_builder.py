from typing import Any

import gradio as gr
from pydantic import BaseModel


class PydanticGradioBuilder:
    """基于Pydantic模型的Gradio界面构建器"""

    def __init__(self, model_class: type[BaseModel]):
        self.model_class = model_class
        self.field_info = model_class.model_fields
        self.field_names = list(self.field_info.keys())

    def create_component(self, field_name: str, current_value: Any) -> gr.Component:
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
        else:
            # 默认处理
            return gr.Textbox(
                label=field.title,
                value=str(current_value),
                info=field.description,
            )

    def create_update_function(self, config_manager):
        """创建配置更新函数"""

        def update_config(*args) -> tuple:
            config_dict = dict(zip(self.field_names, args))

            try:
                config = self.model_class(**config_dict)

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

                success = config_manager.update_config(config)

                if success:
                    gr.Info("配置已成功保存")
                    config_values = config.model_dump()
                    return tuple(config_values[field] for field in self.field_names)
                else:
                    gr.Error("保存配置失败")
                    return args

            except Exception as e:
                gr.Error(f"更新失败: {str(e)}")
                return args

        return update_config
