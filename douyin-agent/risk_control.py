"""
风控与节流模块
保护账号安全：随机延迟、频率限制、消息队列调度
"""
import time
import random
import threading
import queue
from datetime import datetime, timedelta
from loguru import logger

from config import config


class RiskController:
    """风控控制器"""

    def __init__(self):
        self._reply_count = 0
        self._last_reset_time = datetime.now()
        self._lock = threading.Lock()

    def random_delay(self):
        """
        随机延迟，模拟真人反应速度
        使用正态分布让延迟更自然
        """
        delay = random.uniform(config.MIN_DELAY, config.MAX_DELAY)
        logger.debug(f"风控延迟: {delay:.2f}秒")
        time.sleep(delay)

    def can_reply(self) -> bool:
        """
        检查是否允许回复
        基于每小时最大回复数限制
        """
        with self._lock:
            now = datetime.now()
            # 每小时重置计数器
            if now - self._last_reset_time >= timedelta(hours=1):
                self._reply_count = 0
                self._last_reset_time = now

            if self._reply_count >= config.MAX_REPLIES_PER_HOUR:
                logger.warning(f"风控: 已达到每小时上限({config.MAX_REPLIES_PER_HOUR}条)，跳过回复")
                return False

            self._reply_count += 1
            logger.info(f"风控: 本小时第{self._reply_count}/{config.MAX_REPLIES_PER_HOUR}条回复")
            return True

    @property
    def remaining_quota(self) -> int:
        """返回当前小时剩余可回复次数"""
        with self._lock:
            now = datetime.now()
            if now - self._last_reset_time >= timedelta(hours=1):
                return config.MAX_REPLIES_PER_HOUR
            return max(0, config.MAX_REPLIES_PER_HOUR - self._reply_count)


class ReplyQueue:
    """
    回复消息队列 + 调度器
    所有待回复请求先入队，由调度器按频率依次处理
    """

    def __init__(self, risk_controller: RiskController):
        self._queue = queue.Queue()
        self._risk = risk_controller
        self._running = False
        self._worker_thread = None

    def enqueue(self, content: str, callback=None):
        """
        将回复请求加入队列
        callback: 实际发送函数，如 client.send_barrage
        """
        self._queue.put({
            "content": content,
            "callback": callback,
            "time": datetime.now(),
        })
        logger.info(f"回复已入队: {content[:20]}... (队列长度: {self._queue.qsize()})")

    def start(self):
        """启动队列处理线程"""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()
        logger.info("回复队列调度器已启动")

    def stop(self):
        """停止队列处理"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        logger.info("回复队列调度器已停止")

    def _worker(self):
        """队列处理工作线程"""
        while self._running:
            try:
                item = self._queue.get(timeout=1)
            except queue.Empty:
                continue

            # 风控检查
            if not self._risk.can_reply():
                logger.warning("风控拦截，丢弃该条回复")
                self._queue.task_done()
                continue

            # 随机延迟
            self._risk.random_delay()

            # 执行发送
            try:
                content = item["content"]
                callback = item.get("callback")
                if callback:
                    callback(content)
                else:
                    logger.info(f"[模拟发送] {content}")
            except Exception as e:
                logger.error(f"发送失败: {e}")

            self._queue.task_done()


# 全局实例
risk_controller = RiskController()
reply_queue = ReplyQueue(risk_controller)
