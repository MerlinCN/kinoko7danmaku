from contextlib import asynccontextmanager
import logging

import gradio as gr
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from loguru import logger

from audio_player import close_stream_player, get_stream_player
from bilibili.bili_service import get_bili_service
from config import config_manager
from webui import create_gradio_interface

LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 7860


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""

    # 启动时初始化
    logger.info("启动应用...")
    logger.info("初始化音频设备...")
    logger.info(f"当前 API URL: {config_manager.config.api_url}")

    # 启动 bilibili 服务
    logger.info("启动 bilibili 直播间连接...")
    bili_service = get_bili_service()
    # bili_service.room_obj.logger.setLevel(logging.DEBUG)
    # 启动 bilibili 服务
    logger.info("启动 bilibili 直播间连接完成")
    if config_manager.config.welcome_on:
        stream_player = get_stream_player()
        await stream_player.play_from_text("弹幕姬，启动！")

    logger.info(f"配置和测试地址: http://{LOCAL_HOST}:{LOCAL_PORT}")
    await bili_service.run()
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
        host=LOCAL_HOST,
        port=LOCAL_PORT,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
