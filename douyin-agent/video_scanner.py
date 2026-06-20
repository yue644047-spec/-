"""
视频扫描与评论回复模块
功能: 搜索/浏览视频 -> 读取评论 -> 意图识别 -> 自动回复评论
"""
import time
import random
import threading
from loguru import logger

from config import config
from intent import match_intent
from reply import get_comment_reply
from risk_control import RiskController, ReplyQueue


class VideoScanner:
    """
    视频扫描器
    支持两种模式:
    1. search_mode: 按关键词搜索视频，扫描评论区
    2. user_mode: 刷指定博主的所有视频评论区
    """

    def __init__(self, auth, api_client):
        """
        :param auth: DouyinAuth 认证对象
        :param api_client: DouyinAPI 实例
        """
        self.auth = auth
        self.api = api_client
        self.risk = RiskController()
        self.reply_queue = ReplyQueue(self.risk)
        self.max_comments = config.MAX_COMMENTS_PER_VIDEO  # 每个视频最多读取的评论数
        self._processed_videos = set()  # 已处理的视频ID，避免重复
        self._processed_comments = set()  # 已回复的评论ID，避免重复
        self._running = False
        self._stats = {
            "videos_scanned": 0,
            "comments_read": 0,
            "replies_sent": 0,
            "matches_found": 0,
        }

    # ============================================
    # 搜索模式: 按关键词搜索视频
    # ============================================
    def run_search_mode(self, query: str, max_videos: int = 20,
                        sort_type: str = '0', publish_time: str = '0'):
        """
        搜索关键词相关视频并扫描评论
        :param query: 搜索关键词 (如 "王者荣耀陪玩", "游戏上分")
        :param max_videos: 最大扫描视频数
        :param sort_type: 0综合/1最多点赞/2最新
        :param publish_time: 0不限/1一天内/7一周内/180半年内
        """
        logger.info("=" * 50)
        logger.info(f"  视频扫描器 - 搜索模式")
        logger.info(f"  关键词: {query} | 上限: {max_videos}个视频")
        logger.info("=" * 50)

        self._running = True
        self.reply_queue.start()

        try:
            videos = self.api.search_some_general_work(
                self.auth, query, max_videos,
                sort_type=sort_type, publish_time=publish_time,
                content_type="0"  # 0不限/1视频/2图文
            )
            logger.info(f"搜索到 {len(videos)} 个视频")

            for i, video in enumerate(videos):
                if not self._running:
                    break

                aweme_id = video.get("aweme_info", {}).get("aweme_id", "")
                if not aweme_id or aweme_id in self._processed_videos:
                    continue

                video_url = f"https://www.douyin.com/video/{aweme_id}"
                logger.info(f"\n--- [{i+1}/{len(videos)}] 处理视频: {video_url} ---")

                self._scan_video_comments(aweme_id, video_url)
                self._processed_videos.add(aweme_id)
                self._stats["videos_scanned"] += 1

                # 视频间随机间隔，模拟真人浏览
                browse_delay = random.uniform(5, 15)
                logger.debug(f"浏览下一个视频，等待 {browse_delay:.1f}s...")
                time.sleep(browse_delay)

        except KeyboardInterrupt:
            logger.info("收到中断信号...")
        except Exception as e:
            logger.error(f"搜索模式出错: {e}")
        finally:
            self.stop()
            self._print_stats()

    # ============================================
    # 博主模式: 扫描指定博主的所有视频
    # ============================================
    def run_user_mode(self, user_url: str, max_videos: int = 30):
        """
        扫描指定博主的所有视频评论
        :param user_url: 用户主页URL
        :param max_videos: 最大处理视频数
        """
        logger.info("=" * 50)
        logger.info(f"  视频扫描器 - 博主模式")
        logger.info(f"  博主: {user_url}")
        logger.info("=" * 50)

        self._running = True
        self.reply_queue.start()

        try:
            works = self.api.get_user_all_work_info(self.auth, user_url)
            logger.info(f"博主共有 {len(works)} 个作品")

            for i, work in enumerate(works[:max_videos]):
                if not self._running:
                    break

                aweme_id = work.get("aweme_id", "")
                if not aweme_id or aweme_id in self._processed_videos:
                    continue

                video_url = f"https://www.douyin.com/video/{aweme_id}"
                logger.info(f"\n--- [{i+1}/{min(len(works), max_videos)}] 处理视频: {video_url} ---")

                self._scan_video_comments(aweme_id, video_url)
                self._processed_videos.add(aweme_id)
                self._stats["videos_scanned"] += 1

                browse_delay = random.uniform(5, 15)
                time.sleep(browse_delay)

        except KeyboardInterrupt:
            logger.info("收到中断信号...")
        except Exception as e:
            logger.error(f"博主模式出错: {e}")
        finally:
            self.stop()
            self._print_stats()

    # ============================================
    # 核心方法: 扫描单个视频的评论
    # ============================================
    def _scan_video_comments(self, aweme_id: str, video_url: str):
        """
        扫描单个视频的评论区，匹配意图后回复
        """
        try:
            # 获取评论列表，限制数量
            comments = self.api.get_work_all_out_comment(self.auth, video_url)
            if not comments:
                logger.debug("该视频无评论或获取失败")
                return

            # 只处理前 N 条评论
            comments = comments[:self.max_comments]
            logger.info(f"  获取到 {len(comments)} 条评论 (限制前{self.max_comments}条)")

            matched_count = 0
            for comment in comments:
                if not self._running:
                    break

                comment_id = comment.get("cid", "")
                if comment_id in self._processed_comments:
                    continue

                username = comment.get("user", {}).get("nickname", "匿名用户")
                content = comment.get("text", "").strip()
                if not content:
                    continue

                self._stats["comments_read"] += 1
                logger.info(f"  [评论] {username}: {content}")

                # 意图识别
                if match_intent(content):
                    self._stats["matches_found"] += 1
                    matched_count += 1

                    reply_text = get_comment_reply()
                    logger.info(f"  *** 匹配成功! 准备回复: {reply_text} ***")

                    # 加入发送队列（携带回调）
                    self.reply_queue.enqueue(
                        reply_text,
                        callback=lambda text, aid=aweme_id, cid=comment_id: self._send_comment(aid, cid, text)
                    )

                    self._processed_comments.add(comment_id)

                # 评论处理间的小延迟
                time.sleep(random.uniform(0.5, 2))

            if matched_count > 0:
                logger.info(f"  本视频共匹配 {matched_count} 条目标评论")

        except Exception as e:
            logger.error(f"  扫描视频评论失败: {e}")

    def _send_comment(self, aweme_id: str, comment_id: str, content: str):
        """实际发送评论"""
        try:
            result = self.api.publish_comment(
                self.auth,
                aweme_id=aweme_id,
                content=content,
                reply_id=comment_id  # 回复指定评论
            )
            if result.get("status_code") == 0:
                logger.info(f"[评论已发送] 回复 @{comment_id[:8]}...: {content}")
                self._stats["replies_sent"] += 1
            else:
                logger.warning(f"[评论发送失败] {result}")
        except Exception as e:
            logger.error(f"[评论发送异常] {e}")

    def stop(self):
        """停止扫描器"""
        self._running = False
        self.reply_queue.stop()
        logger.info("视频扫描器已停止")

    def _print_stats(self):
        """打印统计信息"""
        s = self._stats
        logger.info("\n" + "=" * 50)
        logger.info("  扫描统计:")
        logger.info(f"  - 扫描视频数: {s['videos_scanned']}")
        logger.info(f"  - 读取评论数: {s['comments_read']}")
        logger.info(f"  - 匹配目标数: {s['matches_found']}")
        logger.info(f"  - 发送回复数: {s['replies_sent']}")
        logger.info(f"  - 剩余配额: {self.risk.remaining_quota}")
        logger.info("=" * 50)
