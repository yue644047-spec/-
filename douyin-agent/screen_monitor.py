"""
屏幕监控模块 - 纯监控模式（无自动回复）
通过截屏 + OCR 识别屏幕文字 → 本地模型意图识别 → 记录匹配目标

使用方式:
1. 在浏览器中打开抖音直播间/视频页面（已登录）
2. 将浏览器窗口调整到合适位置
3. 运行本程序，选择监控窗口

依赖: mss(截屏), easyocr(文字识别), PIL(图像处理)
"""
import time
import random
import re
from collections import deque
from datetime import datetime
from loguru import logger

from config import config
from intent import match_intent
from reply import get_reply
from risk_control import RiskController


class ScreenMonitor:
    """
    屏幕监控器 - 截屏OCR方案（纯监控，不自动回复）
    功能: 截屏 -> OCR识别 -> 意图识别 -> 记录匹配目标到清单
    """

    def __init__(self, on_match_callback=None):
        self.risk = RiskController()
        self._running = False
        self._ocr_reader = None
        self._seen_texts = deque(maxlen=500)  # 去重缓存
        self._on_match = on_match_callback     # 匹配回调，通知前端
        self._matched_targets = []            # 匹配目标清单
        self._stats = {
            "screenshots": 0,
            "texts_found": 0,
            "matches": 0,
        }

    # ============================================
    # OCR 引擎初始化
    # ============================================
    def _init_ocr(self):
        """懒加载 OCR 引擎"""
        if self._ocr_reader is not None:
            return
        try:
            import easyocr
            logger.info("正在加载 EasyOCR 引擎（首次较慢，请耐心等待）...")
            self._ocr_reader = easyocr.Reader(
                ['ch_sim', 'en'],
                gpu=config.USE_GPU,
                verbose=False,
            )
            logger.info("OCR 引擎加载完成")
        except Exception as e:
            logger.error(f"OCR引擎加载失败: {e}")
            raise

    # ============================================
    # 截屏方法
    # ============================================
    def capture_region(self, x, y, width, height):
        """截取屏幕指定区域"""
        import mss
        with mss.mss() as sct:
            screenshot = sct.grab({
                "left": int(x), "top": int(y),
                "width": int(width), "height": int(height),
            })
        from PIL import Image
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

    def capture_fullscreen(self):
        """截取全屏"""
        import mss
        with mss.mss() as sct:
            screenshot = sct.grab(sct.monitors[1])
        from PIL import Image
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

    def capture_window(self, hwnd_int=None, region=None):
        """
        截取指定窗口或窗口内的指定区域
        :param hwnd_int: 窗口句柄(int)，None则全屏
        :param region: (x,y,w,h) 相对于窗口的子区域
        :return: PIL Image 对象
        """
        import mss
        import ctypes
        from ctypes import wintypes

        if hwnd_int is None:
            return self.capture_region(*region) if region else self.capture_fullscreen()

        try:
            user32 = ctypes.windll.user32
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd_int, ctypes.byref(rect))
            win_x, win_y = rect.left, rect.top
            win_w, win_h = rect.right - rect.left, rect.bottom - rect.top

            if region:
                cap_x, cap_y = win_x + region[0], win_y + region[1]
                cap_w, cap_h = min(region[2], win_w - region[0]), min(region[3], win_h - region[1])
            else:
                cap_x, cap_y, cap_w, cap_h = win_x, win_y, win_w, win_h

            with mss.mss() as sct:
                screenshot = sct.grab({"left": int(cap_x), "top": int(cap_y),
                                       "width": int(cap_w), "height": int(cap_h)})
            from PIL import Image
            return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        except Exception as e:
            logger.warning(f"窗口截屏失败，回退全屏: {e}")
            return self.capture_fullscreen()

    # ============================================
    # OCR 文字识别
    # ============================================
    def ocr_image(self, image):
        """对图片进行 OCR 文字识别"""
        self._init_ocr()
        import numpy as np
        results = self._ocr_reader.readtext(np.array(image))
        texts = []
        for (_box, text, confidence) in results:
            if confidence > config.OCR_CONFIDENCE_THRESHOLD and text.strip():
                texts.append({"text": text.strip(), "confidence": float(confidence)})
        return texts

    # ============================================
    # 文本过滤与去重
    # ============================================
    def _is_new_text(self, text):
        """检查是否为新文本（去重）"""
        normalized = re.sub(r'\s+', '', text).lower()
        if normalized in self._seen_texts or len(normalized) < 3:
            return False
        self._seen_texts.append(normalized)
        return True

    def filter_comments(self, raw_texts):
        """从OCR结果中过滤出有效评论/弹幕，排除UI噪音"""
        noise_patterns = [
            r'^\d{1,2}:\d{2}$',           # 时间戳
            r'^\d+万?$|^[\d.]+w$',         # 数字/播放量
            r'^点赞|关注|分享|评论',       # UI按钮
            r'@.*$',                       # @用户名
            r'^直播中|在线\d+',            # 直播状态
            r'^发送$',                     # 发送按钮
            r'^抖音',                      # 抖音水印
            r'^#.*#$',                     # 话题标签
            r'^热评|置顶|热门',           # 评论区标签
            r'^写评论',                    # 输入框提示
        ]
        comments = []
        for item in raw_texts:
            text = item["text"]
            is_noise = any(re.match(p, text) for p in noise_patterns)
            if is_noise:
                continue
            if not self._is_new_text(text):
                continue
            comments.append(item)
        return comments

    # ============================================
    # 用户名提取 + 匹配记录
    # ============================================
    def _extract_username(self, text):
        """尝试从文本中提取用户名 (格式: "用户名: 评论内容")"""
        for sep in [':', '\uff1a']:   # 冒号 / 中文冒号
            if sep in text:
                parts = text.split(sep, 1)
                if len(parts) == 2:
                    name, comment = parts[0].strip(), parts[1].strip()
                    if 1 <= len(name) <= 20 and comment:
                        return name, comment
        return None, text

    def _record_match(self, text, reply_text):
        """记录一个匹配目标并通知回调"""
        username, comment = self._extract_username(text)
        target = {
            "id": len(self._matched_targets) + 1,
            "username": username or "\u672a\u77e5\u7528\u6237",
            "comment": comment,
            "raw_text": text,
            "time": datetime.now().strftime("%H:%M:%S"),
            "reply": reply_text,
        }
        self._matched_targets.append(target)
        logger.info(
            f"[\u6e05\u5355] #{target['id']} | "
            f"\u7528\u6237: {target['username']} | "
            f"\u8bc4\u8bba: \"{target['comment']}\" | "
            f"\u56de\u590d: {target['reply']}"
        )
        if self._on_match:
            try:
                self._on_match(target)
            except Exception as e:
                logger.warning(f"[清单] 回调通知失败: {e}")

    # ============================================
    # 核心监控循环 (窗口模式)
    # ============================================
    def run_window_mode(self, hwnd_int=None, window_title="", interval=3.0):
        """
        窗口监控主循环
        :param hwnd_int: 窗口句柄(int)，None则全屏
        :param window_title: 窗口标题(日志用)
        :param interval: 截屏间隔(秒)
        """
        mode_str = config.INTENT_MODE.upper()
        logger.info("=" * 50)
        logger.info(f"  \u6296\u97f3\u9664\u73a9Agent - \u5c4f\u5e55\u76d1\u63a7")
        logger.info(f"  \u610f\u56fe\u8bc6\u522b: {mode_str}")
        logger.info("=" * 50)

        if hwnd_int:
            logger.info(f"  \u76ee\u6807\u7a97\u53e3: {window_title}")
        else:
            logger.info("  \u76ee\u6807\u7a97\u53e3: \u5168\u5c4f")

        self._running = True
        logger.info(f"  \u622a\u5c4f\u95f4\u9694: {interval}\u79d2")
        logger.info("  \u5f00\u59cb\u76d1\u63a7...")

        try:
            while self._running:
                loop_start = time.time()

                # 1. 截屏
                img = self.capture_window(hwnd_int=hwnd_int)
                self._stats["screenshots"] += 1
                logger.debug(
                    f"[\u622a\u5c4f] #{self._stats['screenshots']} "
                    f"{img.size[0]}x{img.size[1]}"
                )

                # 2. OCR识别
                raw_texts = self.ocr_image(img)
                comments = self.filter_comments(raw_texts)
                self._stats["texts_found"] += len(comments)

                # 3. 意图识别 + 记录
                for item in comments:
                    text = item["text"]
                    logger.info(f"[\u6587\u672c] \"{text}\" ({item['confidence']:.2f})")

                    if not self._running:
                        break

                    matched = match_intent(text)
                    if matched:
                        self._stats["matches"] += 1
                        reply_text = get_reply()
                        logger.info(
                            f"*** [\u5339\u914d\u6210\u529f!] *** "
                            f"\"{text}\" -> \"{reply_text}\""
                        )
                        self._record_match(text, reply_text)

                # 4. 等待下一轮
                elapsed = time.time() - loop_start
                wait_time = max(interval + random.uniform(-0.5, 0.5) - elapsed, 0.5)
                time.sleep(wait_time)

        except KeyboardInterrupt:
            logger.info("\u6536\u5230\u4e2d\u65ad\u4fe1\u53f7...")
        finally:
            self.stop()

    # ============================================
    # 停止 + 统计
    # ============================================
    def stop(self):
        """停止监控并输出统计"""
        self._running = False
        s = self._stats
        logger.info("")
        logger.info("=" * 50)
        logger.info("  \u76d1\u63a7\u7edf\u8ba1:")
        logger.info(f"  - \u622a\u5c4f\u6b21\u6570: {s['screenshots']}")
        logger.info(f"  - \u8bc6\u522b\u6587\u672c: {s['texts_found']}")
        logger.info(f"  - \u5339\u914d\u76ee\u6807: {s['matches']}")
        logger.info(f"  - \u6e05\u5355\u603b\u6570: {len(self._matched_targets)}")
        for t in self._matched_targets[-10:]:
            logger.info(f"    #{t['id']} {t['username']}: \"{t['comment']}\"")
        if len(self._matched_targets) > 10:
            logger.info(f"    ... \u5171{len(self._matched_targets)}\u6761")
        logger.info("=" * 50)

    def get_matched_targets(self):
        """获取匹配目标清单"""
        return self._matched_targets

    def get_stats(self):
        """获取实时统计"""
        return dict(self._stats)
