import platform
import subprocess
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import gradio as gr
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from loguru import logger

from audio_player import close_stream_player
from config import config_manager
from bilibili import BiliService
from webui import create_gradio_interface
from bilibili.model import DanmuMessage, SendGift


def login_biliup():
    biliup_path = Path("bin") / "biliup.exe"
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        biliup_path = Path("bin") / "biliup-aarch64-macos"

    cookies_path = Path("cookies.json")
    if cookies_path.exists():
        # todo: 做登录校验
        subprocess.run([biliup_path, "renew"])
        return

    subprocess.run(
        [
            biliup_path,
            "login",
        ]
    )


login_biliup()
# 全局变量存储服务实例
bili_service = BiliService()


@bili_service.room_obj.on("DANMU_MSG")
async def on_danmaku(event):
    if not config_manager.config.normal_danmaku_on:
        return
    danmu_message = DanmuMessage.parse(event)
    logger.info(danmu_message)


@bili_service.room_obj.on("SEND_GIFT")
async def on_send_gift(event):
    gift_message = SendGift.parse(event)
    if (
        gift_message.gift_price / 1000 * gift_message.gift_num
        < config_manager.config.gift_threshold
    ):
        return
    logger.info(gift_message)
    await bili_service.send_gift(gift_message)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # global bili_service

    # 启动时初始化
    logger.info("启动应用...")
    logger.info("初始化音频设备...")
    logger.info(f"当前 API URL: {config_manager.config.api_url}")

    # 启动 bilibili 服务
    logger.info("启动 bilibili 直播间连接...")
    asyncio.create_task(bili_service.run())

    yield

    # 关闭时清理资源
    logger.info("关闭应用...")
    close_stream_player()


# 创建 FastAPI 应用
fastapi_app = FastAPI(
    title="Kinoko7 弹幕系统",
    description="B站直播弹幕处理系统",
    version="0.1.0",
    lifespan=lifespan,
)


@fastapi_app.get("/")
async def root():
    """根路径重定向到 Gradio 界面"""
    return RedirectResponse(url="/gradio")


@fastapi_app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "message": "Kinoko7 弹幕系统运行正常",
        "config": {
            "room_id": config_manager.config.room_id,
            "api_url": config_manager.config.api_url,
        },
    }


@fastapi_app.get("/api/config")
async def get_config():
    """获取当前配置"""
    return config_manager.config.model_dump()


def main():
    # 登录 bilibili

    """主函数"""
    # 创建 Gradio 界面
    demo = create_gradio_interface()

    # 将 Gradio 挂载到 FastAPI
    app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=7860,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
