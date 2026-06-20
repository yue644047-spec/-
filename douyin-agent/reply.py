"""
智能回复引擎
提供多种风格的回复话术，支持随机选择和AI生成
"""
import random
import httpx

from config import config


# ============================================
# 预设话术库
# ============================================
REPLY_TEMPLATES = {
    "warm": [  # 热情风格
        "老板好！专业陪玩已就位，私信你了~",
        "需要陪玩的老板看这里！实力带飞~",
        "老板滴滴！接单中，随时上车~",
        "来了来了！专业陪玩在线等老板~",
    ],
    "cool": [  # 干练风格
        "接单中，滴滴上车",
        "在线接单，私信详聊",
        "陪玩接单中，老板说话",
        "实力带飞，私信我",
    ],
    "cute": [  # 可爱风格
        "老板~陪玩在这里等你哟(◕‿◕✿)",
        "滴滴滴~老板找我玩嘛~",
        "老板老板！这里有好玩的陪玩~",
        "找到我算你运气好哦~私信我啦",
    ],
}

# 默认使用全部话术
ALL_REPLIES = []
for replies in REPLY_TEMPLATES.values():
    ALL_REPLIES.extend(replies)


# ============================================
# 评论区专用话术 (更自然，不像广告)
# ============================================
COMMENT_REPLIES = {
    "natural": [  # 自然互动风（推荐用于评论）
        "我之前也是这样，后来找了陪玩就好了哈哈",
        "同感！可以试试找个陪玩带你，效率高很多",
        "哈哈 我也经常遇到这种情况",
        "确实，一个人玩太累了，找个陪玩会好很多",
        "姐妹/兄弟，我认识几个不错的陪玩，需要的话可以说~",
        "这个我可以！私信聊？",
        "巧了，我这边刚好有靠谱的陪玩资源~",
        "上分的话可以找我聊聊，专业带飞不墨迹",
        "滴滴我，安排到位",
        "有人带就是不一样，想上分的可以了解一下",
    ],
    "helpful": [  # 帮助型回复
        "建议找个固定的陪玩，比路人靠谱多了",
        "你可以试试去专门的陪玩平台看看",
        "这种情况下找个陪玩是最快的解决方案",
        "我之前也是卡在这个段位，后来找人带的",
    ],
}

ALL_COMMENT_REPLIES = []
for replies in COMMENT_REPLIES.values():
    ALL_COMMENT_REPLIES.extend(replies)


def get_comment_reply(style: str = None) -> str:
    """
    获取评论区专用回复话术
    更自然、更像真实用户互动
    """
    if style and style in COMMENT_REPLIES:
        return random.choice(COMMENT_REPLIES[style])
    return random.choice(ALL_COMMENT_REPLIES)


def get_reply(style: str = None) -> str:
    """
    获取随机回复话术
    style: warm/cool/cute，None则从全部话术中随机选
    """
    if style and style in REPLY_TEMPLATES:
        return random.choice(REPLY_TEMPLATES[style])
    return random.choice(ALL_REPLIES)


# ============================================
# AI生成回复 (可选)
# ============================================
REPLY_SYSTEM_PROMPT = """你是一个抖音陪玩接单助手。根据用户的弹幕内容，生成一条简短、自然、吸引人的回复话术。

要求:
- 回复要简短（不超过20个字）
- 语气友好但不卑微
- 引导用户私信或互动
- 不要过于推销感
- 直接输出回复内容，不要解释"""


def generate_ai_reply(user_message: str) -> str:
    """
    使用大模型生成个性化回复
    """
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
                    {"role": "system", "content": REPLY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.8,
                "max_tokens": 50,
            },
            timeout=10.0,
        )
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[AI回复生成失败] {e}, 使用预设话术")
        return get_reply()
