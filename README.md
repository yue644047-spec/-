三角洲自动获客系统-以douyin为例

<div align="center">

![Python](https://img.shields.io/badge/Python-3.7%2B-blue)
![Flask](https://img.shields.io/badge/Flask-2.0%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

**基于屏幕监控 + OCR + 本地意图识别的抖音陪玩需求自动发现系统**

[功能介绍](#功能特性) · [快速开始](#快速开始) · [配置说明](#配置说明) · [使用指南](#使用指南) · [API文档](#api文档)

</div>

---

## 📋 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [技术架构](#技术架构)
- [快速开始](#快速开始)
  - [环境要求](#环境要求)
  - [一键启动](#一键启动)
  - [手动安装](#手动安装)
- [配置说明](#配置说明)
  - [公开配置](#公开配置-env)
  - [敏感配置](#敏感配置-secretsenv)
  - [配置管理界面](#配置管理界面)
- [使用指南](#使用指南)
  - [主控制面板](#主控制面板)
  - [配置管理中心](#配置管理中心)
  - [监控流程](#监控流程)
- [核心模块](#核心模块)
  - [本地意图识别模型](#本地意图识别模型)
  - [屏幕监控系统](#屏幕监控系统)
  - [Web控制面板](#web控制面板)
- [API文档](#api文档)
- [常见问题](#常见问题)
- [开发计划](#开发计划)
- [许可证](#许可证)

---

## 🎯 项目简介

**抖音陪玩Agent** 是一款基于 **屏幕截屏 + OCR文字识别 + 本地意图识别** 的自动化监控系统，专门用于发现抖音平台上的陪玩需求。

### 核心价值

- ✅ **无需Cookie** - 纯屏幕监控模式，不需要登录凭证
- ✅ **离线运行** - 本地TF-IDF+NaiveBayes模型，不依赖外部API
- ✅ **实时响应** - WebSocket实时推送匹配结果
- ✅ **可视化操作** - 完整的Web控制面板
- ✅ **安全可靠** - 敏感信息独立管理，支持导入导出

### 适用场景

| 场景 | 说明 |
|------|------|
| **陪玩接单** | 自动识别评论区"滴滴""上分"等需求 |
| **市场调研** | 统计特定游戏/话题的需求热度 |
| **竞品分析** | 监控竞争对手的互动情况 |
| **内容运营** | 发现热门评论和用户反馈 |

---

## ✨ 功能特性

### 核心功能

```
┌─────────────────────────────────────────────────────┐
│                   功能矩阵                           │
├──────────┬──────────┬──────────┬─────────────────────┤
│ 监控方式 │ 意图识别 │ 数据处理 │ 可视化展示           │
├──────────┼──────────┼──────────┼─────────────────────┤
│ • 全屏   │ • 关键词 │ • 去重   │ • 实时状态看板       │
│ • 窗口   │ • 正则   │ • 过滤   │ • 趋势图表           │
│ • 区域   │ • 本地模型│ • 排序   │ • 匹配目标清单       │
│          │ • LLM API│ • 导出   │ • 日志分析           │
└──────────┴──────────┴──────────┴─────────────────────┘
```

### 详细功能列表

#### 🎯 意图识别引擎

- **关键词匹配** - 快速精确匹配预定义词汇
- **正则表达式** - 支持复杂模式匹配（手机号、价格等）
- **本地模型 (推荐)** - TF-IDF + NaiveBayes分类器
  - 训练数据: 400+样本（250正样本 + 150负样本）
  - 特征: unigram + bigram N-gram
  - 准确率: 85%+ (针对陪玩需求场景)
  - 推理速度: <10ms/条
- **LLM大模型** - DeepSeek API（可选）

#### 📺 屏幕监控系统

- **高性能截屏** - mss库，<50ms延迟
- **中文OCR** - EasyOCR，支持简繁体中文
- **智能过滤** - 置信度阈值、文本长度、去重缓存
- **窗口选择** - 自动检测浏览器窗口，支持手动指定
- **风控机制** - 随机延迟、频率限制

#### 💻 Web控制面板

- **实时监控** - Socket.IO毫秒级推送
- **统计看板** - 匹配率、平均间隔、趋势图
- **日志系统** - 分级显示（INFO/MATCH/ERROR）
- **数据导出** - CSV格式导出匹配记录
- **配置管理** - 可视化编辑所有参数

---

## 🏗️ 技术架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户浏览器                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ 主控制面板   │  │ 配置中心    │  │ WebSocket实时通信    │  │
│  │ /           │  │ /config     │  │ Socket.IO            │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                      Flask Web服务器                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ REST API     │  │ 静态资源     │  │ WebSocket服务     │   │
│  │ /api/*       │  │ HTML/CSS/JS  │  │ 实时事件广播      │   │
│  └──────┬───────┘  └──────────────┘  └────────┬─────────┘   │
└─────────┼──────────────────────────────────────┼─────────────┘
          │                                      │
          ▼                                      ▼
┌─────────────────────────────────────────────────────────────┐
│                      核心业务逻辑                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ ScreenMonitor│  │ IntentEngine │  │ ConfigManager    │   │
│  │ 截屏+OCR     │  │ 意图识别     │  │ 配置加载/保存    │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────┘   │
└─────────┼────────────────┼──────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                      外部依赖                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ mss      │  │ EasyOCR  │  │ sklearn  │  │ .env文件     │ │
│  │ 截屏库   │  │ OCR引擎  │  │ ML模型   │  │ 配置存储     │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 数据流图

```
用户点击"开始监控"
        ↓
  ┌─────────────┐
  │ 选择窗口句柄 │
  └──────┬──────┘
         ↓
  ┌─────────────┐     ┌─────────────┐
  │ mss截屏     │ ──→ │ Pillow处理   │
  │ (<50ms)     │     │ 格式转换     │
  └─────────────┘     └──────┬──────┘
                             ↓
                     ┌─────────────┐
                     │ EasyOCR识别 │
                     │ 中文文本    │
                     └──────┬──────┘
                            ↓
                    ┌─────────────┐
                    │ 过滤+去重   │
                    │ 置信度>0.5  │
                    └──────┬──────┘
                           ↓
                   ┌─────────────┐
                   │ 意图识别    │ ←── 本地TF-IDF模型
                   │ match_intent│
                   └──────┬──────┘
                          ↓
                  ┌─────────────┐
                  │ 记录匹配结果 │
                  │ 更新统计数据 │
                  └──────┬──────┘
                         ↓
                 ┌─────────────┐
                 │ WebSocket   │
                 │ 推送到前端   │
                 └─────────────┘
```

### 技术栈

| 类别 | 技术 | 版本要求 |
|------|------|---------|
| **语言** | Python | 3.7+ |
| **Web框架** | Flask | 2.0+ |
| **实时通信** | Flask-SocketIO | 5.0+ |
| **屏幕截屏** | mss | 9.0+ |
| **OCR识别** | EasyOCR | 1.7+ |
| **机器学习** | scikit-learn | 1.3+ |
| **图像处理** | Pillow | 10.0+ |
| **前端** | HTML5 + CSS3 + Vanilla JS | - |

---

## 🚀 快速开始

### 环境要求

#### 必需软件

| 软件 | 版本 | 用途 |
|------|------|------|
| Python | 3.7+ (推荐3.9+) | 运行环境 |
| pip | 最新版 | 包管理器 |
| 浏览器 | Chrome/Edge/Firefox | Web控制面板 |

#### 硬件要求

| 配置 | 最低 | 推荐 |
|------|------|------|
| CPU | 双核 | 四核+ |
| 内存 | 4GB | 8GB+ |
| GPU | - | NVIDIA (可选加速OCR) |
| 存储 | 500MB可用 | 1GB+ |

### 一键启动 (推荐)

#### 方式 1: 双击批处理文件

```bash
# Windows用户直接双击:
start.bat          # 完整启动 (检查环境+安装依赖)
quick_start.bat    # 快速启动 (跳过检查)
```

#### 方式 2: PowerShell脚本

```powershell
# 完整启动 (带环境检查)
.\start.ps1

# 跳过依赖安装
.\start.ps1 -SkipInstall

# 自定义端口
.\start.ps1 -Port 8080

# 强制重装依赖
.\start.ps1 -Force
```

### 手动安装

#### 步骤 1: 克隆项目

```bash
git clone <your-repo-url>
cd douyin-agent
```

#### 步骤 2: 创建虚拟环境 (可选但推荐)

```bash
python -m venv venv

# Windows激活
venv\Scripts\activate

# Linux/Mac激活
source venv/bin/activate
```

#### 步骤 3: 安装依赖

```bash
pip install -r requirements.txt

# 如果网络慢，使用国内镜像源:
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 步骤 4: 配置环境

```bash
# 复制模板文件
copy secrets.env.example secrets.env

# 编辑配置
notepad .env
notepad secrets.env
```

#### 步骤 5: 启动服务

```bash
python web/server.py --port 5001
```

#### 步骤 6: 访问界面

打开浏览器访问: **http://localhost:5001**

---

## ⚙️ 配置说明

### 项目结构

```
douyin-agent/
├── main.py              # 主程序入口
├── config.py            # 配置管理模块
├── screen_monitor.py    # 屏幕监控核心
├── intent.py            # 意图识别引擎
├── reply.py             # 回复文本生成
├── risk_control.py      # 风控机制
│
├── .env                 # 公开配置 (可提交Git)
├── secrets.env          # 🔒 敏感配置 (不可提交!)
├── secrets.env.example  # 敏感配置模板
├── .gitignore           # Git忽略规则
├── requirements.txt     # Python依赖
│
├── start.ps1            # PowerShell启动脚本
├── start.bat            # 批处理启动脚本
├── quick_start.bat      # 快速启动脚本
│
├── web/
│   ├── server.py        # Flask服务器
│   ├── templates/
│   │   ├── index.html   # 主控制面板
│   │   └── config.html  # 配置管理页面
│   └── static/
│       ├── style.css    # 主样式表
│       ├── config.css   # 配置页样式
│       ├── app.js       # 主交互逻辑
│       └── config.js    # 配置页逻辑
│
├── logs/                # 日志目录 (运行时生成)
└── data/                # 数据目录 (运行时生成)
```

### 公开配置 (.env)

```ini
# ============================================
# 抖音陪玩Agent - 公开配置
# ============================================

# 目标直播间ID (可选)
ROOM_ID=你的目标直播间ID

# ============================================
# 意图识别配置
# ============================================
# 选项: local(推荐) / keyword / regex / llm
INTENT_MODE=local

# LLM配置 (仅llm模式需要, API Key在secrets.env设置)
LLM_API_URL=https://api.deepseek.com/v1/chat/completions
LLM_MODEL=deepseek-chat

# ============================================
# 风控配置
# ============================================
MIN_DELAY=2               # 最小延迟(秒)
MAX_DELAY=5               # 最大延迟(秒)
MAX_REPLIES_PER_HOUR=5    # 每小时最大回复数
MAX_COMMENTS_PER_HOUR=10  # 每小时最大评论数
MAX_COMMENTS_PER_VIDEO=20 # 每视频最多读取评论数

# ============================================
# 视频扫描配置
# ============================================
SCAN_MODE=search          # live/search/user
SEARCH_KEYWORDS=三角洲行动 # 搜索关键词(逗号分隔)
MAX_VIDEOS=1              # 最大扫描数
SORT_TYPE=0               # 0综合/1点赞/2最新

# ============================================
# 屏幕监控配置
# ============================================
MONITOR_REGION=           # 监控区域(x,y,w,h),留空全屏
INPUT_BOX_POS=            # 输入框位置(x,y)
CAPTURE_INTERVAL=1        # 截屏间隔(秒)
OCR_CONFIDENCE_THRESHOLD=0.5  # OCR置信度阈值
USE_GPU=false             # GPU加速(需CUDA)

# ============================================
# 日志配置
# ============================================
LOG_LEVEL=INFO            # DEBUG/INFO/WARNING/ERROR
LOG_FILE=logs/agent.log
```

### 敏感配置 (secrets.env) ⚠️

```ini
# ============================================
# 敏感信息 - 请勿提交到Git!
# ============================================

# LLM API Key (DeepSeek/OpenAI)
LLM_API_KEY=sk-your_api_key_here
LLM_API_URL=https://api.deepseek.com/v1/chat/completions
LLM_MODEL=deepseek-chat

# 抖音Cookie (如需要)
DOUYIN_COOKIE=your_cookie_here
LIVE_COOKIE=your_live_cookie_here
```

### 配置优先级

```
系统环境变量 > secrets.env > .env > 默认值
```

后加载的会覆盖先加载的同名变量。

---

## 📖 使用指南

### 主控制面板 (/)

访问地址: http://localhost:5001

#### 界面布局

```
┌─────────────────────────────────────────────────────┐
│ ● 抖音陪玩Agent                        ● 已连接      │
├──────────────────┬──────────────────────────────────┤
│                  │                                  │
│  📷 屏幕监控      │  📋 匹配目标清单                  │
│                  │  (实时更新 + 导出)                │
│  [窗口选择▼]     ├──────────────────────────────────┤
│  [意图模式▼]     │  📝 实时日志                       │
│                  │  (分级过滤 + 自动滚动)             │
│  [▶ 开始监控]    │                                  │
│                  │                                  │
│  📊 实时状态     │                                  │
│  ┌────┬────┐   │                                  │
│  │ 0  │ 0  │   │                                  │
│  │截屏│文本│   │                                  │
│  ├────┼────┤   │                                  │
│  │ 0  │ 0  │   │                                  │
│  │匹配│回复│   │                                  │
│  └────┴────┘   │                                  │
│                  │                                  │
│  📈 数据分析     │                                  │
│  [关键指标]      │                                  │
│  [趋势图]        │                                  │
│                  │                                  │
│  ⚙ 参数配置     │                                  │
│  [截屏间隔]      │                                  │
│  [🔧 完整配置]   │                                  │
│                  │                                  │
└──────────────────┴──────────────────────────────────┘
```

#### 操作步骤

1. **选择监控窗口**
   - 点击下拉框选择要监控的浏览器窗口
   - 或点击刷新按钮重新检测

2. **选择识别模式**
   - `本地模型` (推荐): 离线、快速、准确率高
   - `关键词`: 简单词汇匹配
   - `大模型`: 需要API Key

3. **开始监控**
   - 点击 "▶ 开始监控" 按钮
   - 右侧实时显示匹配目标和日志

4. **查看统计**
   - 左侧下方查看数据分析看板
   - 包含: 匹配率、平均间隔、趋势图

5. **导出数据**
   - 点击匹配清单右上角 "📥 导出" 按钮
   - 保存为CSV格式

### 配置管理中心 (/config)

访问地址: http://localhost:5001/config

或从主页顶部导航栏点击 `⚙ 配置` 按钮。

#### 功能概览

| 功能 | 说明 |
|------|------|
| **可视化编辑** | 卡片式展示每个配置项 |
| **双标签切换** | 公开配置 ↔ 敏感配置 |
| **分组导航** | 7个配置分组快速定位 |
| **修改追踪** | 高亮已修改字段，计数统计 |
| **密码保护** | 默认隐藏敏感信息 |
| **导入/导出** | JSON格式备份恢复 |

#### 配置分组

| 分组图标 | 分组名 | 配置项数 | 说明 |
|----------|--------|---------|------|
| 🎯 | 意图识别 | 1 | INTENT_MODE |
| 📺 | 屏幕监控 | 5 | 截屏/OCR/GPU等 |
| ⚠️ | 风控设置 | 4 | 延迟/频率限制 |
| 🔍 | 视频扫描 | 3 | 搜索/排序 |
| 🤖 | LLM配置 | 3 | API Key/URL/Model |
| 🍪 | 凭证管理 | 2 | Cookie |
| ⚙️ | 系统设置 | 1 | 日志级别 |

### 监控流程详解

```
启动监控
    ↓
① 选择目标窗口
    ↓
② 循环执行 (每N秒):
    │
    ├─► mss截取窗口画面 (<50ms)
    │       ↓
    ├─► EasyOCR识别文字 (~200ms)
    │       ↓
    ├─► 过滤低置信度结果 (>0.5)
    │       ↓
    ├─► 去重 (500条缓存)
    │       ↓
    ├─► 本地意图识别 (<10ms)
    │       ↓
    │   ┌─── 匹配成功? ──┐
    │   │ Yes            │ No
    │   ▼                ▼
    │ 记录到清单      忽略
    │ 更新统计
    │ WebSocket推送
    │
    └─► 随机等待 (2~5秒)
        ↓
    回到②循环
```

---

## 🔧 核心模块

### 本地意图识别模型

**文件**: [`intent.py`](intent.py)

#### 模型架构

```
输入文本 → TF-IDF向量化 → MultinomialNB分类 → 输出概率
```

#### 训练数据

| 类别 | 样本数 | 示例 |
|------|--------|------|
| **正样本 (有需求)** | 250+ | "三角洲行动陪玩滴滴", "有没有人一起上分" |
| **负样本 (无需求)** | 150+ | "这个视频真好看", "哈哈哈笑死我了" |

#### 特征工程

```python
TfidfVectorizer(
    ngram_range=(1, 2),      # unigram + bigram
    max_features=5000,       # 最大特征数
    sublinear_tf=True,       # TF对数缩放
)
```

#### 使用示例

```python
from intent import match_intent

result = match_intent("三角洲行动缺队友滴滴")
# result = {
#     'matched': True,
#     'confidence': 0.87,
#     'method': 'local',
#     'keywords': ['三角洲行动', '缺队友', '滴滴']
# }
```

### 屏幕监控系统

**文件**: [`screen_monitor.py`](screen_monitor.py)

#### 核心类: ScreenMonitor

```python
monitor = ScreenMonitor()

# 窗口模式 (推荐)
monitor.run_window_mode(
    hwnd_int=123456,        # 窗口句柄
    window_title="Chrome",  # 窗口标题
    interval=3.0            # 截屏间隔
)
```

#### OCR配置

```python
# 初始化OCR (首次较慢, 后续复用)
reader = easyocr.Reader(['ch_sim', 'ch_tr'], gpu=False)

# 识别图片
results = reader.readtext(image_path)
for (bbox, text, confidence) in results:
    if confidence > 0.5:
        print(f"[{confidence:.2f}] {text}")
```

#### 性能指标

| 操作 | 耗时 | 说明 |
|------|------|------|
| 截屏 | ~30ms | mss库 |
| OCR识别 | ~150-300ms | 取决于文本量 |
| 意图匹配 | ~5-10ms | 本地模型 |
| **总耗时/轮** | **~200-400ms** | 不含等待时间 |

### Web控制面板

**文件**: [`web/server.py`](web/server.py)

#### 启动参数

```bash
python web/server.py --port 5001 --debug
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--port` | 5001 | 服务端口 |
| `--debug` | False | 调试模式 |

#### 主要API端点

详见 [API文档](#api文档) 章节。

---

## 📡 API文档

### RESTful API

#### 1. 获取配置

```http
GET /api/config
```

**响应**:
```json
{
  "success": true,
  "data": {
    "env": { "INTENT_MODE": "local", ... },
    "secrets": { "LLM_API_KEY": "sk-xxx...xxxx", ... },
    "files": { "env_exists": true, "secrets_exists": true }
  }
}
```

#### 2. 更新配置

```http
POST /api/config
Content-Type: application/json

{
  "env": { "CAPTURE_INTERVAL": "3" },
  "secrets": { "LLM_API_KEY": "sk-new-key" }
}
```

#### 3. 获取配置Schema

```http
GET /api/config/schema
```

返回所有配置项的元数据（类型、标签、选项、分组等）。

#### 4. 获取窗口列表

```http
GET /api/windows
```

**响应**:
```json
{
  "success": true,
  "windows": [
    {
      "id": 123456,
      "title": "Chrome - 抖音",
      "hwnd": "0x000A1234",
      "rect": {"x": 0, "y": 45, "width": 1920, "height": 1080}
    }
  ]
}
```

#### 5. 启动监控

```http
POST /api/start
Content-Type: application/json

{
  "window_hwnd": 123456,
  "window_title": "Chrome",
  "mode": "screen"
}
```

#### 6. 停止监控

```http
POST /api/stop
```

#### 7. 获取状态

```http
GET /api/status
```

### WebSocket事件

客户端监听的事件:

| 事件名称 | 数据 | 说明 |
|----------|------|------|
| `status_changed` | `{running: bool}` | 监控状态变化 |
| `log` | `{level, time, msg}` | 新日志消息 |
| `matched_target` | `{id, comment, username, reply}` | 匹配到新目标 |
| `config_updated` | `{...}` | 配置已更新 |

---

## ❓ 常见问题

### Q1: 启动时报错 "ModuleNotFoundError"

**解决方案**:
```bash
pip install -r requirements.txt
```

如果仍然失败，尝试升级pip:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Q2: OCR识别速度很慢

**可能原因及解决**:

1. **首次运行**: EasyOCR需要下载模型文件（约20MB），请耐心等待
2. **CPU性能**: OCR是CPU密集型任务，建议关闭其他占用CPU的程序
3. **启用GPU**: 如果有NVIDIA显卡，设置 `USE_GPU=true`

```ini
# 在.env中修改
USE_GPU=true
```

### Q3: 窗口列表为空

**排查步骤**:

1. 确保浏览器已打开并显示抖音页面
2. 点击 "🔄 刷新" 按钮重新检测
3. 尝试以管理员身份运行脚本
4. 检查是否有杀毒软件拦截窗口枚举

### Q4: 匹配率太低/太高

**调整方法**:

1. **降低阈值**: 修改 `INTENT_MODE=keyword` 使用简单关键词
2. **自定义关键词**: 编辑 [`intent.py`](intent.py) 的 `_KEYWORDS` 列表
3. **训练模型**: 添加更多训练数据到 `_TRAIN_DATA`

### Q5: 如何添加新的识别词汇?

编辑 [`intent.py`](intent.py):

```python
# 在 _KEYWORDS 字典中添加
_KEYWORDS = {
    "positive": [
        "你的新词汇",
        # ...
    ],
}

# 或在 _TRAIN_DATA 中添加训练样本
_TRAIN_DATA = {
    "positive": [
        "包含新词汇的句子",
        # ...
    ],
}
```

### Q6: 日志中出现乱码

**确保以下设置**:

1. 系统编码: UTF-8
2. 终端代码页: `chcp 65001`
3. 环境变量: `PYTHONIOENCODING=utf-8`

启动脚本已自动处理这些问题。

### Q7: 如何部署到生产环境?

建议:

1. **使用Gunicorn替代开发服务器**:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 web.server:app
```

2. **使用Nginx反向代理**
3. **配置systemd服务实现开机自启**
4. **使用环境变量而非文件存储密钥**

---

## 🗺️ 开发计划

### v1.1 (进行中)

- [ ] 支持多窗口同时监控
- [ ] 增加更多游戏关键词库
- [ ] 添加定时任务调度
- [ ] 移动端适配优化

### v1.2 (规划中)

- [ ] Docker容器化部署
- [ ] PostgreSQL数据持久化
- [ ] 用户认证与权限管理
- [ ] 多语言支持 (英文/日文)

### v2.0 (远期)

- [ ] 分布式监控集群
- [ ] 机器学习模型在线更新
- [ ] 数据分析与报表
- [ ] 微信/钉钉通知集成

---

## 🤝 贡献指南

欢迎提交Issue和Pull Request!

### 开发流程

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 提交Pull Request

### 代码规范

- Python遵循PEP 8
- JavaScript使用ES6+语法
- CSS使用BEM命名规范
- 提交信息使用Conventional Commits

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 🙏 致谢

- [mss](https://github.com/nickoala/mss) - 超快屏幕截图库
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) - 强大的OCR引擎
- [scikit-learn](https://scikit-learn.org/) - 机器学习框架
- [Flask](https://flask.palletsprojects.com/) - 轻量级Web框架
- [Socket.IO](https://socket.io/) - 实时双向通信

---

## 📞 联系方式

- **问题反馈**: 请发送邮件至 yue644047@gmail
- **功能建议**: 请发送邮件至 yue644047@gmail
- **商业合作**: 请发送邮件至 yue644047@gmail

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐ Star 支持！**

Made with ❤️ by [Your Name]

</div>
