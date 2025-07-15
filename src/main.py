from loguru import logger

from audio_player import close_stream_player
from config import config_manager
from webui import create_gradio_interface


def main():
    """主函数"""
    try:
        # 初始化时打印设备信息
        logger.info("初始化音频设备...")
        logger.info(f"当前 API URL: {config_manager.config.api_url}")

        # 创建并启动 Gradio 界面
        demo = create_gradio_interface()
        demo.launch(
            server_name="127.0.0.1",
            server_port=7860,  # 使用默认端口
            share=False,
            show_error=True,
            inbrowser=True,
        )
    finally:
        # 清理资源
        close_stream_player()


if __name__ == "__main__":
    main()
