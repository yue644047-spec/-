"""
抖音陪玩Agent - 屏幕监控模式 (纯截屏OCR方案)
无需Cookie，通过截屏+OCR识别屏幕文字 -> 意图识别 -> 自动回复

支持参数:
  --window-hwnd <句柄>  指定窗口句柄(十进制整数)，只截取该窗口
  --window-title <标题>  窗口标题(仅用于日志显示)
"""
import sys
import os
import argparse
from loguru import logger

# ====== 修复Windows中文乱码 ======
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    # 设置控制台代码页为UTF-8
    try:
        os.system('chcp 65001 >nul 2>&1')
    except Exception:
        pass
# ================================

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from screen_monitor import ScreenMonitor


def setup_logger():
    log_dir = os.path.dirname(config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger.remove()
    logger.add(
        sys.stdout,
        level=config.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
    )
    if config.LOG_FILE:
        logger.add(
            config.LOG_FILE,
            level=config.LOG_LEVEL,
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}",
        )


def main():
    parser = argparse.ArgumentParser(description='抖音陪玩Agent - 屏幕监控')
    parser.add_argument('--window-hwnd', type=int, default=None, help='目标窗口句柄')
    parser.add_argument('--window-title', type=str, default='', help='窗口标题(日志显示)')
    parser.add_argument('--mode', type=str, default='screen', choices=['screen', 'comment'], help='运行模式')
    args = parser.parse_args()

    from screen_monitor import ScreenMonitor

    logger.info("=" * 50)
    logger.info("  抖音陪玩Agent - 屏幕监控")
    logger.info("=" * 50)
    logger.info(f"  意图识别: {config.INTENT_MODE}")
    logger.info(f"  每小时回复上限: {config.MAX_COMMENTS_PER_HOUR}")

    monitor = ScreenMonitor()

    # 屏幕监控模式 (默认)
    if args.mode == 'screen':
        logger.info(f"  目标模式: 窗口监控")
        try:
            monitor.run_window_mode(
                hwnd_int=args.window_hwnd,
                window_title=args.window_title,
                interval=config.CAPTURE_INTERVAL,
            )
        except KeyboardInterrupt:
            logger.info("已停止")
        return

    # 评论模式 (旧逻辑，已弃用)
    if args.mode == 'comment':
        logger.warning("  ⚠️ 评论模式已弃用，请使用屏幕监控模式")
        return


if __name__ == "__main__":
    setup_logger()
    main()
