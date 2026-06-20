"""
配置管理模块
从 .env 文件加载所有配置项，提供统一的配置访问接口
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Config:
    """全局配置类"""

    # 直播间配置
    ROOM_ID = os.getenv("ROOM_ID", "")

    # Cookie配置
    DOUYIN_COOKIE = os.getenv("DOUYIN_COOKIE", "")
    LIVE_COOKIE = os.getenv("LIVE_COOKIE", "")

    # 意图识别模式: keyword / regex / llm
    INTENT_MODE = os.getenv("INTENT_MODE", "keyword")

    # LLM配置
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_API_URL = os.getenv("LLM_API_URL", "https://api.deepseek.com/v1/chat/completions")
    LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

    # 风控配置
    MIN_DELAY = float(os.getenv("MIN_DELAY", "2"))
    MAX_DELAY = float(os.getenv("MAX_DELAY", "5"))
    MAX_REPLIES_PER_HOUR = int(os.getenv("MAX_REPLIES_PER_HOUR", "5"))

    # ============================================
    # 视频扫描配置 (刷视频+评论模式)
    # ============================================
    # 扫描模式: search(搜索视频) / user(博主视频) / live(直播间弹幕)
    SCAN_MODE = os.getenv("SCAN_MODE", "live")

    # 搜索模式关键词 (多个用逗号分隔)
    SEARCH_KEYWORDS = os.getenv("SEARCH_KEYWORDS", "王者荣耀陪玩,游戏上分,找陪玩")

    # 最大扫描视频数
    MAX_VIDEOS = int(os.getenv("MAX_VIDEOS", "20"))

    # 搜索排序: 0综合/1最多点赞/2最新
    SORT_TYPE = os.getenv("SORT_TYPE", "0")

    # 博主主页URL (user模式时使用)
    TARGET_USER_URL = os.getenv("TARGET_USER_URL", "")

    # 评论模式每小时最大回复数 (可独立于直播间的限制)
    MAX_COMMENTS_PER_HOUR = int(os.getenv("MAX_COMMENTS_PER_HOUR", "10"))

    # 每个视频最多读取的评论数
    MAX_COMMENTS_PER_VIDEO = int(os.getenv("MAX_COMMENTS_PER_VIDEO", "20"))

    # ============================================
    # 屏幕监控配置 (无需Cookie的截屏OCR方案)
    # ============================================
    # 监控区域坐标 (x, y, width, height)，留空则使用全屏或交互式选择
    MONITOR_REGION = os.getenv("MONITOR_REGION", "")  # 格式: "100,200,800,600"

    # 评论输入框点击位置 (x, y)
    INPUT_BOX_POS = os.getenv("INPUT_BOX_POS", "")  # 格式: "500,400"

    # 截屏间隔(秒)
    CAPTURE_INTERVAL = float(os.getenv("CAPTURE_INTERVAL", "3.0"))

    # OCR置信度阈值（低于此值的结果被过滤）
    OCR_CONFIDENCE_THRESHOLD = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.5"))

    # 是否使用GPU加速OCR
    USE_GPU = os.getenv("USE_GPU", "false").lower() == "true"

    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/agent.log")

    @classmethod
    def validate(cls):
        """验证关键配置项是否已填写"""
        errors = []
        if not cls.ROOM_ID or cls.ROOM_ID == "你的目标直播间ID":
            errors.append("ROOM_ID 未配置，请在 .env 中填写直播间ID")
        if not cls.DOUYIN_COOKIE or cls.DOUYIN_COOKIE == "你的www.douyin.com Cookie":
            errors.append("DOUYIN_COOKIE 未配置")
        if not cls.LIVE_COOKIE or cls.LIVE_COOKIE == "你的live.douyin.com Cookie":
            errors.append("LIVE_COOKIE 未配置")
        if cls.INTENT_MODE == "llm" and not cls.LLM_API_KEY:
            errors.append("LLM模式需要配置 LLM_API_KEY")
        return errors


# 全局配置实例
config = Config()
