<div align="center">

# Kinoko7弹幕姬

_调用GradioAPI来播报哔哩哔哩直播中的弹幕、礼物、舰长等_

</div>



## 克隆

由于使用了git子模块，clone时需要加上`--recursive`参数：

```
git clone --recursive https://github.com/MerlinCN/kinoko7danmaku.git
```



如果已经clone，拉子模块的方法：

```
git submodule update --init --recursive
```



## 安装环境

```
pip install -r requirements.txt
```



## 开始使用

```
python src/main.py
```

注意工作目录要在根目录下



## 配置说明

- `room_id` (int): 直播间的房间号，默认为 `213`。这是监控的直播间的房间号。
- `gift_threshold` (int): 礼物触发阈值（单位：元）。只有当收到的礼物价值大于或等于这个值时，才会触发相应的功能。默认值为 `5`。
- `api_url` (str): API 地址。Gradio的API地址。
- `alias` (dict): 别名字典。用于替换某些特定的词语。例如，可以将 `{'Merlin': '么林'}` 添加到字典中，改善某些日英词语的发音。默认为空字典。
- `normal_danmaku_on` (bool): 普通弹幕触发开关。默认为 `True`。
- `guard_on` (bool): 舰长功能触发开关。默认为 `True`。
- `super_chat_on` (bool): 醒目留言功能触发开关。默认为 `True`。
- `voice_name` (str): 语音模型的名称。默认为 `"C酱"`。
- `voice_channel` (int): 声道设置。默认值 `-1` 表示系统输出。如果您有专用的声卡，可以根据需要修改此值。
- `debug` (bool): 调试模式开关。默认为 `False`。



## API 地址

可以自己本地部署，也可以填在线服务，具体网址可以进入[这里](https://www.modelscope.cn/studios/xzjosh/Bert-VITS2/summary) 查找

## 支持与贡献

觉得好用可以给这个项目点个 Star 或者去 [爱发电](https://afdian.net/a/MerlinCN) 投喂我。

有意见或者建议也欢迎提交  Issues 和 Pull requests。

## 许可证

本项目使用 [GNU AGPLv3](https://choosealicense.com/licenses/agpl-3.0/) 作为开源许可证。