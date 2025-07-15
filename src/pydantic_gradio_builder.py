import json
from typing import Any, get_origin

import gradio as gr
from pydantic import BaseModel


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
            return self._create_dict_component(field_name, field, current_value)
        else:
            # 默认处理
            return gr.Textbox(
                label=field.title,
                value=str(current_value),
                info=field.description,
            )

    def _create_dict_component(self, field_name: str, field, current_value: dict):
        """创建字典字段组件 - 每行有删除按钮"""

        # 初始化当前值为字典格式
        if not isinstance(current_value, dict):
            current_value = {}

        # 最大支持10行（可以根据需要调整）
        MAX_ROWS = 10

        # 创建隐藏的JSON文本框来存储实际值
        json_value = json.dumps(current_value, ensure_ascii=False)
        hidden_json = gr.Textbox(
            value=json_value, visible=False, label=f"{field_name}_json_data"
        )

        with gr.Group(elem_classes="dict-group"):
            gr.HTML(f"""
            <h3>{field.title}</h3>
            <style>
            .dict-group {{
                background-color: white !important;
            }}
            .dict-group .styler {{
                background-color: white !important;
            }}
            .dict-group .block {{
                background-color: white !important;
            }}
            .dict-row {{
                align-items: flex-end !important;
            }}
            .dict-row > div {{
                align-items: flex-end !important;
            }}
            .dict-row .block-info {{
                display: none !important;
            }}
            .dict-row .svelte-g2oxp3 {{
                display: none !important;
            }}
            .dict-row button {{
                margin-bottom: 10px !important;
            }}
            </style>
            """)

            # 行可见性状态
            visible_count = gr.State(value=max(1, len(current_value)))

            # 预创建所有行
            key_inputs = []
            value_inputs = []
            delete_buttons = []
            rows = []

            current_items = list(current_value.items())

            for i in range(MAX_ROWS):
                is_visible = i < len(current_items)
                key_val = current_items[i][0] if i < len(current_items) else ""
                value_val = current_items[i][1] if i < len(current_items) else ""

                with gr.Row(visible=is_visible, elem_classes="dict-row") as row:
                    key_input = gr.Textbox(
                        label=None,
                        value=key_val,
                        placeholder="弹幕中原来的词",
                        scale=2,
                        container=True,
                    )
                    value_input = gr.Textbox(
                        label=None,
                        value=value_val,
                        placeholder="替换为",
                        scale=3,
                        container=True,
                    )
                    delete_btn = gr.Button("❌", scale=1, min_width=40)

                    key_inputs.append(key_input)
                    value_inputs.append(value_input)
                    delete_buttons.append(delete_btn)
                    rows.append(row)

            # 添加新行按钮
            add_button = gr.Button("➕ 添加新行", size="sm", variant="secondary")

            # 更新隐藏JSON的函数
            def update_hidden_json(*all_inputs):
                """根据所有输入更新隐藏的JSON值"""
                dict_data = {}
                # 前half是键，后half是值
                half = len(all_inputs) // 2
                keys = all_inputs[:half]
                values = all_inputs[half:]

                for key, value in zip(keys, values):
                    if key and key.strip():
                        dict_data[key.strip()] = value

                new_json = json.dumps(dict_data, ensure_ascii=False)
                return new_json

            # 为所有输入框设置change事件
            all_inputs = key_inputs + value_inputs
            for inp in all_inputs:
                inp.change(
                    fn=update_hidden_json, inputs=all_inputs, outputs=[hidden_json]
                )

            # 添加新行
            def add_new_row(current_visible):
                new_visible = min(current_visible + 1, MAX_ROWS)
                # 返回所有行的可见性状态
                visibilities = [
                    gr.Row(visible=i < new_visible) for i in range(MAX_ROWS)
                ]
                return [new_visible] + visibilities

            add_button.click(
                fn=add_new_row, inputs=[visible_count], outputs=[visible_count] + rows
            )

            # 为每个删除按钮设置事件
            for i, delete_btn in enumerate(delete_buttons):

                def create_delete_function(row_index):
                    def delete_row(current_visible, *all_inputs):
                        # 获取当前所有有效的键值对
                        half = len(all_inputs) // 2
                        keys = list(all_inputs[:half])
                        values = list(all_inputs[half:])

                        # 删除指定行的数据
                        if row_index < len(keys):
                            keys.pop(row_index)
                            values.pop(row_index)

                        # 重新分配数据到输入框
                        new_keys = keys + [""] * (MAX_ROWS - len(keys))
                        new_values = values + [""] * (MAX_ROWS - len(values))

                        # 更新可见行数
                        new_visible = max(1, len([k for k in keys if k.strip()]))

                        # 更新JSON
                        dict_data = {}
                        for key, value in zip(keys, values):
                            if key and key.strip():
                                dict_data[key.strip()] = value
                        new_json = json.dumps(dict_data, ensure_ascii=False)

                        # 返回更新后的值
                        visibilities = [
                            gr.Row(visible=i < new_visible) for i in range(MAX_ROWS)
                        ]
                        return (
                            [new_visible, new_json]
                            + new_keys
                            + new_values
                            + visibilities
                        )

                    return delete_row

                delete_btn.click(
                    fn=create_delete_function(i),
                    inputs=[visible_count] + all_inputs,
                    outputs=[visible_count, hidden_json]
                    + key_inputs
                    + value_inputs
                    + rows,
                )

        return hidden_json

    def create_update_function(self, config_manager):
        """创建配置更新函数"""

        def update_config(*args) -> tuple:
            config_dict = dict(zip(self.field_names, args))

            # 处理字典字段 - 从JSON文本框中解析值
            for field_name, field in self.field_info.items():
                if get_origin(field.annotation) is dict:
                    # 从JSON文本框中获取值
                    json_value = config_dict.get(field_name, "{}")
                    try:
                        dict_value = (
                            json.loads(json_value) if json_value.strip() else {}
                        )
                    except json.JSONDecodeError as e:
                        gr.Error(f"字段 '{field.title}' 的JSON格式有误: {str(e)}")
                        return args
                    config_dict[field_name] = dict_value

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
                # 为字典字段返回JSON字符串
                return_values = []
                for field in self.field_names:
                    value = config_values[field]
                    if get_origin(self.field_info[field].annotation) is dict:
                        return_values.append(json.dumps(value, ensure_ascii=False))
                    else:
                        return_values.append(value)
                return tuple(return_values)
            else:
                gr.Error("保存配置失败")
                return args

        return update_config
