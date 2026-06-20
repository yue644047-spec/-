"""
意图识别模块
支持四种模式: 关键词匹配 / 正则表达式 / 本地模型(local) / 大模型(LLM)

本地模式使用 TF-IDF + NaiveBayes 分类器，无需API调用，完全离线运行。
"""
import re
import json
import os
from loguru import logger

from config import config


# ============================================
# 方案一: 关键词匹配 (默认)
# ============================================
KEYWORDS = [
    # 陪玩需求类
    "陪玩", "找陪玩", "求陪玩", "有没有陪玩", "接单吗",
    # 上分需求类
    "上分", "求带", "带我", "带带我", "带飞", "大神带",
    "一起玩", "组队", "缺人", "差人", "来个",
    # 询问/寻找类
    "滴滴", "私信", "怎么联系", "多少钱", "价格",
    "有人吗", "有老板吗", "上车", "排位",
    # 游戏相关
    "吃鸡", "王者上分", "星耀", "钻石", "代打",
    # 三角洲行动专用
    "三角洲", "三角洲行动", "烽火地带", "全面战场",
    "航站楼", "零号大坝", "长弓溪谷", "巴克什",
    "三角洲兄弟", "三角洲开黑", "三角洲组队",
    "三角洲上分", "三角洲陪玩", "三角洲代打",
]


def match_keyword(text: str) -> bool:
    """关键词精确匹配 - 最快"""
    text = text.strip()
    for kw in KEYWORDS:
        if kw in text:
            logger.info(f"  [关键词] 命中: \"{kw}\" in \"{text}\"")
            return True
    logger.info(f"  [关键词] 未命中")
    return False


# ============================================
# 方案二: 正则表达式模糊匹配
# ============================================
REGEX_PATTERNS = [
    r"陪?玩.*?(?:滴滴|来|找|要|求|有)",
    r"(?:求|找|来|要).*(?:陪|带|玩|飞)",
    r"(?:老板|有人|小姐姐).*?(?:带|陪|玩)",
    r"(?:上分|排位|王者|吃鸡).*?(?:带|陪|找)",
    r"滴滴.*?(?:上车|接单|陪玩)",
]


def match_regex(text: str) -> bool:
    """正则表达式模糊匹配"""
    text = text.strip()
    for pattern in REGEX_PATTERNS:
        m = re.search(pattern, text)
        if m:
            logger.info(f"  [正则] 命中: \"{pattern}\" -> \"{text}\"")
            return True
    logger.info(f"  [正则] 未命中")
    return False


# ============================================
# 方案三(NEW): 本地TF-IDF分类器 (推荐)
# ============================================

# 训练数据: 正样本(有需求) / 负样本(无需求)
_TRAIN_DATA = {
    "positive": [
        # 三角洲行动场景
        "三角洲行动太难了，有没有大佬带带",
        "这游戏队友太菜了，根本赢不了",
        "烽火地带怎么打啊，有人一起吗",
        "有人开黑吗？差两个人",
        "三角洲陪玩多少钱一局？滴滴我",
        "全面战场排位上不去，找个代打",
        "航站楼那个点怎么卡啊，求教",
        "三角洲兄弟求带飞！有人吗",
        "缺个陪玩一起吃鸡，滴滴我",
        "三角洲组队缺人，来个会玩的",
        "烽火地带单排太难了，找个队友",
        "有没有三角洲陪玩的？私信我",
        "这个模式太难了，求个带飞的",
        "三角洲行动找队友，滴滴上车",
        "长弓溪谷怎么过？有人教一下吗",
        "零号大坝蹲点，来个靠谱的",
        "巴克什地图找人一起跑图",
        "三角洲开黑缺一，来个会说话的",
        "全面战场冲分中，差个强力队友",
        "三角洲代打多少钱？星耀段位的",
        "烽火地带有人带新人吗",
        "三角洲兄弟们，有人上分吗",
        "这游戏一个人玩没意思，找队友",
        "三角洲行动求带！我是萌新",
        "有没有人一起三角洲的？滴滴我",
        "三角洲陪玩接单吗？想上个分",
        # 通用陪玩需求
        "来几个陪玩带带我上分",
        "有没有王者荣耀陪玩？滴滴",
        "求带！找个陪玩一起排位",
        "接单吗？想找个陪玩",
        "王者星耀求带飞！有人吗",
        "全面战场排位上不去，找个代打",
        "缺个陪玩一起吃鸡，滴滴我",
        "有人开黑吗？差两个人",
        "吃鸡四缺一，来个会玩的",
        "王者代打多少钱一局",
        "有没有人一起上分的？滴滴",
        "找个陪玩带带我，谢谢老板",
        "这游戏太难了，求大佬带",
        "有人带带我上分吗？新手一枚",
        "陪玩接单了吗？我想上个王者",
        "滴滴！找个靠谱的陪玩",
        "上分太难了，有没有人带",
        "排位连跪了，求个大神带飞",
        "有没有人一起玩的？私信我",
        "缺个陪玩，价格好说",
        "这个游戏一个人玩没意思",
        "求带飞！我是菜鸟",
        "有人组队吗？差一个",
        "代打接单吗？想上个分",
        "陪玩小姐姐在吗？想找个",
        "老板在吗？接单了没",
        "上车的滴滴我！",
        "找个人一起玩游戏",
        "游戏太无聊了，找人聊天",
    ],
    "negative": [
        # 纯夸奖/无需求
        "主播技术牛逼！学到了",
        "哈哈哈笑死我了这个视频",
        "今天天气不错，出去走走吧",
        "666666",
        "这个视频太好看了",
        "主播声音好听",
        "关注了关注了",
        "点赞收藏走一波",
        "这操作太秀了",
        "哈哈哈哈笑得肚子疼",
        "主播长得真好看",
        "已点赞已关注",
        "第一次来，支持一下",
        "这游戏画面真不错",
        "音乐好好听啊",
        "主播加油！",
        "这波操作绝了",
        "学到了学到了",
        "主播太强了吧",
        "这视频质量很高",
        "期待下一期",
        "终于更新了！",
        "每天必看系列",
        "主播辛苦了",
        "这把打得漂亮",
        "好厉害的操作",
        "这游戏我也在玩",
        "画面很清晰",
        "剪辑做得很好",
        "内容很丰富",
        "看完了，很不错",
        "支持主播！",
        "一直关注你",
        "老粉来了",
        "前排占座",
        "打卡打卡",
        "沙发沙发",
        "来了来了",
        "收到",
        "好的",
        "嗯嗯",
        "哈哈",
        "厉害",
        "牛逼",
        "牛批",
        "nb",
        "666",
        "👍",
        "🎉",
        "❤️",
        "🔥",
        # 游戏讨论但无需求
        "这个枪挺好用的",
        "我觉得M4比AK好用",
        "这地图我熟",
        "这个版本T0英雄是谁",
        "新出的皮肤好看吗",
        "这个赛季什么时候结束",
        "段位继承规则是什么",
        "这个角色怎么获得",
        "装备搭配推荐一下",
        "技能加点方案",
        "这个bug修了没有",
        "服务器又崩了",
        "维护时间是什么时候",
        "新版本更新了什么",
        "这个活动怎么参与",
        "积分有什么用",
        "商城东西太贵了",
        "抽卡概率太低了",
        "皮肤返场什么时候",
        "战令等级多少级了",
        "每日任务做了没",
        "周常任务有哪些",
        "成就系统怎么解锁",
        "好友上限是多少",
        "怎么加好友",
        "举报功能在哪",
        "设置在哪里找",
        "帧数怎么调",
        "灵敏度怎么设",
        "键位怎么改",
        "画质设置推荐",
        "手机配置要求",
        "电脑配置要求",
        "网络延迟太高了",
        "掉线怎么回事",
        "登录不上怎么办",
        "账号被封了",
        "密码忘记了",
        "实名认证怎么做",
        "未成年限制",
        "防沉迷系统",
        "充值不到账",
        "点券没用",
        "钻石不够用了",
        "金币怎么赚",
        "经验值怎么刷",
        "等级上限是多少",
        "转职条件是什么",
        "觉醒材料哪里刷",
        "强化成功率多少",
        "合成概率是多少",
        "掉落表在哪里看",
        "副本攻略分享",
        "BOSS打法教学",
        "PVP技巧讲解",
        "PVE阵容推荐",
        "公会玩法介绍",
        "社交系统说明",
        "交易系统详解",
        "经济系统分析",
        "职业平衡讨论",
        "版本强度排行",
        "英雄克制关系",
        "装备属性对比",
        "符文搭配指南",
        "天赋树解析",
        "技能连招教学",
        "操作手法演示",
        "意识培养教程",
        "团队配合技巧",
        "指挥思路分享",
        "战术布局分析",
        "资源管理策略",
        "时间规划建议",
        "效率提升方法",
        "收益最大化方案",
        "成本控制技巧",
        "风险规避指南",
        "安全注意事项",
        "常见问题解答",
        "新手入门指引",
        "进阶提升路径",
        "高手进阶心得",
        "专家深度分析",
        "数据统计报告",
        "趋势预测分析",
        "市场行情观察",
        "行业动态追踪",
        "政策法规解读",
        "技术发展趋势",
        "产品迭代方向",
        "用户体验反馈",
        "功能优化建议",
        "性能优化方案",
        "安全加固措施",
        "稳定性保障机制",
        "可扩展性设计",
        "兼容性处理方案",
        "国际化适配方案",
        "本地化实施策略",
        "多语言支持方案",
        "多平台适配方案",
        "移动端优化方案",
        "PC端优化方案",
        "Web端优化方案",
        "小程序优化方案",
        "App优化方案",
        "H5页面优化方案",
        "响应式布局方案",
        "自适应设计方案",
        "交互体验优化方案",
        "视觉设计优化方案",
        "动效设计优化方案",
        "音效设计优化方案",
        "文案优化方案",
        "图标设计优化方案",
        "配色方案优化",
        "字体选择优化",
        "间距调整优化",
        "对齐方式优化",
        "层级关系优化",
        "信息架构优化",
        "导航结构优化",
        "搜索功能优化",
        "筛选功能优化",
        "排序功能优化",
        "分页功能优化",
        "加载状态优化",
        "空状态优化",
        "错误状态优化",
        "异常处理优化",
        "边界情况处理",
        "极端情况应对",
        "压力测试方案",
        "性能监控方案",
        "日志收集方案",
        "告警机制方案",
        "故障排查流程",
        "问题定位方法",
        "解决方案总结",
        "经验教训提炼",
        "知识沉淀整理",
        "文档编写规范",
        "代码规范制定",
        "评审标准明确",
        "流程规范建立",
        "制度完善落地",
        "文化建设推进",
        "团队协作提升",
        "沟通效率改善",
        "执行力加强",
        "创新能力激发",
        "学习氛围营造",
        "成长路径清晰",
        "激励机制完善",
        "考核体系科学",
        "晋升通道畅通",
        "薪酬福利合理",
        "工作环境舒适",
        "生活平衡保障",
        "身心健康关注",
        "职业发展支持",
        "技能培训提供",
        "导师制度落实",
        "轮岗机会创造",
        "项目历练安排",
        "挑战性任务分配",
        "成就感来源明确",
        "归属感建立增强",
        "凝聚力持续提升",
        "战斗力稳步增强",
        "影响力逐步扩大",
        "品牌价值不断提升",
        "市场份额稳步增长",
        "用户规模持续扩大",
        "收入水平不断提高",
        "利润空间不断拓展",
        "成本结构持续优化",
        "运营效率显著提升",
        "服务质量明显改善",
        "客户满意度大幅提高",
        "口碑效应逐步形成",
        "竞争优势日益凸显",
        "行业地位稳步巩固",
        "发展前景更加广阔",
        "未来可期值得期待",
        "携手共进共创辉煌",
        "砥砺前行再创佳绩",
        "乘风破浪扬帆远航",
        "披荆斩棘勇往直前",
        "不忘初心方得始终",
        "牢记使命砥砺前行",
        "脚踏实地仰望星空",
        "志存高远脚踏实地",
        "厚积薄发行稳致远",
        "天道酬勤功不唐捐",
        "水滴石穿绳锯木断",
        "铁杵磨针持之以恒",
        "锲而不舍金石可镂",
        "精诚所至金石为开",
        "有志者事竟成",
        "苦心人天不负",
        "卧薪尝胆三千越甲可吞吴",
        "破釜沉舟百二秦关终属楚",
    ],
}

_local_model = None
_local_vectorizer = None


class LocalIntentClassifier:
    """
    本地意图识别分类器
    使用 TF-IDF 向量化 + NaiveBayes 分类器
    完全离线运行，无需GPU，首次加载约1秒
    """

    def __init__(self):
        self.vectorizer = None
        self.classifier = None
        self._loaded = False

    def _ensure_loaded(self):
        """懒加载模型（首次调用时训练）"""
        if self._loaded:
            return
        self._train()
        self._loaded = True

    def _train(self):
        """训练本地分类器"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.naive_bayes import MultinomialNB
            from sklearn.pipeline import Pipeline

            pos_texts = _TRAIN_DATA["positive"]
            neg_texts = _TRAIN_DATA["negative"]
            all_texts = pos_texts + neg_texts
            labels = [1] * len(pos_texts) + [0] * len(neg_texts)

            self.model = Pipeline([
                ('tfidf', TfidfVectorizer(
                    ngram_range=(1, 2),      # unigram + bigram
                    max_features=5000,         # 特征维度上限
                    min_df=1,
                    sublinear_tf=True,         # TF对数缩放
                )),
                ('clf', MultinomialNB(alpha=0.1)),
            ])
            self.model.fit(all_texts, labels)

            # 验证准确率
            accuracy = self.model.score(all_texts, labels)
            logger.info(f"[本地模型] 训练完成! 样本={len(all_texts)} (正{len(pos_texts)}+负{len(neg_texts)}), 准确率={accuracy:.1%}")

        except ImportError:
            logger.warning("[本地模型] sklearn未安装，回退到关键词模式")
            self.model = None

    def predict(self, text: str) -> dict:
        """
        预测文本意图
        返回: {"intent": bool, "confidence": float, "reason": str}
        """
        self._ensure_loaded()

        if self.model is None:
            # sklearn不可用，回退到关键词
            kw_result = match_keyword(text)
            return {"intent": kw_result, "confidence": 0.8 if kw_result else 0.2, "reason": "sklearn未安装，使用关键词回退"}

        proba = self.model.predict_proba([text])[0]
        # proba[0]=负类概率, proba[1]=正类概率(有需求)
        confidence = float(proba[1])
        is_intent = confidence > 0.45  # 阈值

        reason = (
            f"置信度={confidence:.1%}, "
            f"{'判定为有需求' if is_intent else '判定为无需求'}"
        )

        result = {"intent": is_intent, "confidence": round(confidence, 3), "reason": reason}
        logger.info(f"  [本地模型] 文本=\"{text[:40]}...\" -> {result}")
        return result


# 全局实例
_local_classifier = LocalIntentClassifier()


def match_local(text: str) -> dict:
    """使用本地模型进行意图识别"""
    return _local_classifier.predict(text)


# ============================================
# 方案四: 大模型意图识别 (可选)
# ============================================

LLM_SYSTEM_PROMPT = f"""你是一个抖音评论意图识别助手。

判断该评论是否有寻找游戏陪玩/代打/上分服务的潜在需求。
只返回JSON: {{"intent": true/false, "confidence": 0.0-1.0, "reason": "原因"}}"""


def match_llm(text: str) -> dict:
    """使用大模型进行意图识别（需要API Key）"""
    import httpx
    try:
        response = httpx.post(
            config.LLM_API_URL,
            headers={
                "Authorization": f"Bearer {config.LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": LLM_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.1,
                "max_tokens": 150,
            },
            timeout=10.0,
        )
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            logger.info(f"  [LLM] 结果: intent={parsed.get('intent')}, conf={parsed.get('confidence')}")
            return parsed
        return {"intent": False, "confidence": 0.0, "reason": "解析失败"}
    except Exception as e:
        logger.error(f"  [LLM错误] {e}")
        return {"intent": False, "confidence": 0.0, "reason": str(e)}


# ============================================
# 统一入口
# ============================================
def match_intent(text: str) -> bool:
    """
    根据配置的模式进行意图识别
    返回 True 表示匹配到陪玩相关意图

    模式说明:
      keyword - 关键词精确匹配 (最快)
      regex   - 正则表达式模糊匹配
      local   - 本地TF-IDF分类器 (推荐, 无需API)
      llm     - 大模型识别 (需API Key, 最准但慢)
    """
    mode = config.INTENT_MODE
    logger.info(f"[match_intent] 模式={mode}, 输入=\"{text}\"")

    if mode == "keyword":
        result = match_keyword(text)
    elif mode == "regex":
        result = match_regex(text)
    elif mode == "local":
        r = match_local(text)
        result = r.get("intent", False)
    elif mode == "llm":
        r = match_llm(text)
        confidence = r.get("confidence", 0)
        result = r.get("intent", False) and confidence > 0.6
    else:
        result = match_keyword(text)

    logger.info(f"[match_intent] 最终结果: {result}")
    return result
