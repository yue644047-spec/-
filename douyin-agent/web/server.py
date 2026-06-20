"""
抖音陪玩Agent - Web控制面板后端 (纯屏幕监控)
REST API + WebSocket实时日志
"""
import os
import sys
import json
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from config import config

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'douyin-agent-screen'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # 禁用静态文件缓存
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


@app.after_request
def add_no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


agent_state = {"running": False, "pid": None, "started_at": None, "logs": [], "matched_targets": []}


# ============================================
# 窗口列表API
# ============================================

@app.route('/api/windows')
def api_windows():
    """获取系统中所有可见窗口列表"""
    try:
        windows = _get_windows_list()
        return jsonify({"success": True, "windows": windows})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


def _get_windows_list():
    """获取Windows系统中的所有可见窗口"""
    import traceback
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32

        EnumWindows = user32.EnumWindows
        GetWindowTextW = user32.GetWindowTextW
        GetWindowRect = user32.GetWindowRect
        IsWindowVisible = user32.IsWindowVisible
        IsIconic = user32.IsIconic
        GetWindowTextLengthW = user32.GetWindowTextLengthW

        WNDENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            wintypes.HWND,
            wintypes.LPARAM,
        )

        results = []

        def cb(hwnd, lp):
            try:
                if not IsWindowVisible(hwnd):
                    return True
                if IsIconic(hwnd):
                    return True
                length = GetWindowTextLengthW(hwnd)
                if length == 0 or length > 500:
                    return True
                buf = ctypes.create_unicode_buffer(length + 1)
                GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value.strip()
                if not title:
                    return True
                rect = ctypes.wintypes.RECT()
                GetWindowRect(hwnd, ctypes.byref(rect))
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if w < 50 or h < 30:  # 过滤太小的窗口
                    return True
                results.append({
                    "hwnd": hwnd,
                    "title": title,
                    "x": rect.left,
                    "y": rect.top,
                    "width": w,
                    "height": h,
                })
            except Exception as e:
                pass  # 忽略单个窗口的错误
            return True

        EnumWindows(WNDENUMPROC(cb), 0)

        # 按标题排序，常用窗口靠前
        keywords = ['chrome', 'edge', 'firefox', '浏览器', 'douyin', '抖音', 'live']
        def sort_key(w):
            t = w['title'].lower()
            for i, kw in enumerate(keywords):
                if kw in t:
                    return i
            return 99
        results.sort(key=sort_key)

        print(f"[API] 成功获取 {len(results)} 个窗口")
        # 只返回必要字段（hwnd转字符串）
        return [
            {
                "id": str(w["hwnd"]),
                "title": w["title"],
                "x": w["x"],
                "y": w["y"],
                "width": w["width"],
                "height": w["height"],
            }
            for w in results[:100]  # 最多返回100个
        ]
    except ImportError:
        print("[API] 非Windows系统")
        return []
    except Exception as e:
        print(f"[API] 窗口列表获取失败: {e}")
        traceback.print_exc()
        return []


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/config')
def config_page():
    """配置管理独立页面"""
    return render_template('config.html')


@app.route('/api/status')
def api_status():
    return jsonify({"success": True, "data": {
        "running": agent_state["running"],
        "started_at": agent_state["started_at"],
        "config": {
            "CAPTURE_INTERVAL": config.CAPTURE_INTERVAL,
            "INTENT_MODE": config.INTENT_MODE,
            "MAX_COMMENTS_PER_HOUR": config.MAX_COMMENTS_PER_HOUR,
            "MONITOR_REGION": config.MONITOR_REGION or "",
        }
    }})


@app.route('/api/diagnose', methods=['POST'])
def api_diagnose():
    """一次性截屏+OCR诊断，返回原始识别结果"""
    try:
        data = request.json or {}
        hwnd = data.get('window_hwnd')

        from screen_monitor import ScreenMonitor
        monitor = ScreenMonitor()

        # 截屏
        if hwnd:
            img = monitor.capture_window(hwnd_int=int(hwnd))
        else:
            img = monitor.capture_fullscreen()

        # OCR识别
        import io, base64
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        raw_texts = monitor.ocr_image(img)
        comments = monitor.filter_comments(raw_texts)

        # 对每条文本做意图识别
        results = []
        for item in raw_texts:
            from intent import match_intent
            matched = match_intent(item['text'])
            results.append({
                "text": item['text'],
                "confidence": round(item['confidence'], 3),
                "is_comment": item in comments,
                "matched_intent": matched,
            })

        return jsonify({
            "success": True,
            "data": {
                "image_preview": f"data:image/png;base64,{img_b64}",
                "total_raw": len(raw_texts),
                "after_filter": len(comments),
                "results": results[:50],  # 最多返回50条
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """获取或更新配置"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base_dir, '.env')
    secrets_path = os.path.join(base_dir, 'secrets.env')

    if request.method == 'POST':
        data = request.json or {}
        try:
            # 更新 .env (公开配置)
            _update_env_file(env_path, data.get('env', {}))

            # 更新 secrets.env (敏感配置)
            if data.get('secrets'):
                _update_env_file(secrets_path, data['secrets'])

            # 重新加载配置
            from dotenv import load_dotenv
            load_dotenv(env_path, override=False)
            if os.path.exists(secrets_path):
                load_dotenv(secrets_path, override=True)

            socketio.emit('config_updated', data)
            return jsonify({"success": True, "message": "配置已保存"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    # GET: 返回完整配置
    return jsonify({"success": True, "data": {
        "env": {
            "INTENT_MODE": config.INTENT_MODE,
            "CAPTURE_INTERVAL": config.CAPTURE_INTERVAL,
            "OCR_CONFIDENCE_THRESHOLD": config.OCR_CONFIDENCE_THRESHOLD,
            "MIN_DELAY": config.MIN_DELAY,
            "MAX_DELAY": config.MAX_DELAY,
            "MAX_REPLIES_PER_HOUR": config.MAX_REPLIES_PER_HOUR,
            "MAX_COMMENTS_PER_HOUR": config.MAX_COMMENTS_PER_HOUR,
            "SCAN_MODE": config.SCAN_MODE,
            "SEARCH_KEYWORDS": config.SEARCH_KEYWORDS,
            "MAX_VIDEOS": config.MAX_VIDEOS,
            "SORT_TYPE": config.SORT_TYPE,
            "MONITOR_REGION": config.MONITOR_REGION or "",
            "INPUT_BOX_POS": config.INPUT_BOX_POS or "",
            "USE_GPU": str(config.USE_GPU).lower(),
            "LOG_LEVEL": config.LOG_LEVEL,
        },
        "secrets": {
            "LLM_API_KEY": _mask_key(config.LLM_API_KEY),
            "LLM_API_URL": config.LLM_API_URL,
            "LLM_MODEL": config.LLM_MODEL,
            "DOUYIN_COOKIE": _mask_cookie(config.DOUYIN_COOKIE),
            "LIVE_COOKIE": _mask_cookie(config.LIVE_COOKIE),
        },
        "files": {
            "env_exists": os.path.exists(env_path),
            "secrets_exists": os.path.exists(secrets_path),
        }
    }})


@app.route('/api/config/schema')
def api_config_schema():
    """返回配置项的元数据(用于前端渲染)"""
    schema = {
        "env": {
            "INTENT_MODE": {
                "label": "意图识别模式",
                "type": "select",
                "options": [
                    {"value": "local", "label": "本地模型 (推荐)"},
                    {"value": "keyword", "label": "关键词匹配"},
                    {"value": "regex", "label": "正则表达式"},
                    {"value": "llm", "label": "大模型 API"},
                ],
                "group": "intent",
                "description": "选择意图识别算法"
            },
            "CAPTURE_INTERVAL": {
                "label": "截屏间隔 (秒)",
                "type": "number",
                "min": 0.5, "max": 30, "step": 0.5,
                "group": "monitor",
                "description": "两次截屏之间的等待时间"
            },
            "OCR_CONFIDENCE_THRESHOLD": {
                "label": "OCR 置信度阈值",
                "type": "number", "min": 0, "max": 1, "step": 0.05,
                "group": "monitor",
                "description": "低于此值的识别结果将被过滤"
            },
            "MIN_DELAY": {
                "label": "最小延迟 (秒)",
                "type": "number", "min": 0, "max": 30, "step": 0.5,
                "group": "risk",
                "description": "操作前的最小随机延迟"
            },
            "MAX_DELAY": {
                "label": "最大延迟 (秒)",
                "type": "number", "min": 1, "max": 60, "step": 0.5,
                "group": "risk",
                "description": "操作前的最大随机延迟"
            },
            "MAX_REPLIES_PER_HOUR": {
                "label": "每小时最大回复数",
                "type": "number", "min": 0, "max": 100, "step": 1,
                "group": "risk",
                "description": "直播间弹幕回复上限"
            },
            "MAX_COMMENTS_PER_HOUR": {
                "label": "每小时最大评论数",
                "type": "number", "min": 0, "max": 100, "step": 1,
                "group": "risk",
                "description": "视频评论回复上限"
            },
            "SEARCH_KEYWORDS": {
                "label": "搜索关键词",
                "type": "text",
                "group": "search",
                "description": "多个关键词用逗号分隔"
            },
            "MAX_VIDEOS": {
                "label": "最大扫描视频数",
                "type": "number", "min": 1, "max": 50, "step": 1,
                "group": "search",
                "description": "每次搜索处理的视频数量"
            },
            "SORT_TYPE": {
                "label": "排序方式",
                "type": "select",
                "options": [
                    {"value": "0", "label": "综合排序"},
                    {"value": "1", "label": "最多点赞"},
                    {"value": "2", "label": "最新发布"},
                ],
                "group": "search",
            },
            "MONITOR_REGION": {
                "label": "监控区域坐标",
                "type": "text",
                "group": "monitor",
                "placeholder": "x,y,width,height 或留空全屏",
            },
            "INPUT_BOX_POS": {
                "label": "输入框位置",
                "type": "text",
                "group": "monitor",
                "placeholder": "x,y",
            },
            "USE_GPU": {
                "label": "GPU 加速 OCR",
                "type": "select",
                "options": [
                    {"value": "true", "label": "启用 (需要 CUDA)"},
                    {"value": "false", "label": "禁用 (CPU)"},
                ],
                "group": "monitor",
            },
            "LOG_LEVEL": {
                "label": "日志级别",
                "type": "select",
                "options": [
                    {"value": "DEBUG", "label": "DEBUG (详细)"},
                    {"value": "INFO", "label": "INFO (标准)"},
                    {"value": "WARNING", "label": "WARNING (警告)"},
                    {"value": "ERROR", "label": "ERROR (仅错误)"},
                ],
                "group": "system",
            },
        },
        "secrets": {
            "LLM_API_KEY": {
                "label": "LLM API Key",
                "type": "password",
                "group": "llm",
                "description": "DeepSeek / OpenAI API 密钥"
            },
            "LLM_API_URL": {
                "label": "LLM API 地址",
                "type": "text",
                "group": "llm",
            },
            "LLM_MODEL": {
                "label": "LLM 模型名称",
                "type": "text",
                "group": "llm",
            },
            "DOUYIN_COOKIE": {
                "label": "抖音 Cookie",
                "type": "textarea",
                "group": "cookie",
                "description": "www.douyin.com 的 Cookie 值"
            },
            "LIVE_COOKIE": {
                "label": "直播 Cookie",
                "type": "textarea",
                "group": "cookie",
                "description": "live.douyin.com 的 Cookie 值"
            },
        },
        "groups": {
            "intent": {"name": "🎯 意图识别", "icon": "🎯"},
            "monitor": {"name": "📺 屏幕监控", "icon": "📺"},
            "risk": {"name": "⚠️ 风控设置", "icon": "⚠️"},
            "search": {"name": "🔍 视频扫描", "icon": "🔍"},
            "llm": {"name": "🤖 LLM 配置", "icon": "🤖"},
            "cookie": {"name": "🍪 凭证管理", "icon": "🍪"},
            "system": {"name": "⚙️ 系统设置", "icon": "⚙️"},
        }
    }
    return jsonify({"success": True, "data": schema})


def _update_env_file(file_path, updates):
    """更新 .env 文件中的配置项"""
    lines = []
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

    new_lines = []
    updated = set()

    for line in lines:
        s = line.strip()
        if not s or s.startswith('#'):
            new_lines.append(line)
            continue
        if '=' in s:
            key = s.split('=')[0].strip()
            if key in updates and updates[key] is not None:
                val = updates[key]
                # 多行值特殊处理
                if isinstance(val, list) or '\n' in str(val):
                    new_lines.append(f"{key}={val}\n")
                else:
                    new_lines.append(f"{key}={val}\n")
                updated.add(key)
                continue
        new_lines.append(line)

    # 添加新配置项
    for key, val in updates.items():
        if key not in updated and val is not None and val != '':
            new_lines.append(f"{key}={val}\n")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)


def _mask_key(key):
    """脱敏显示 API Key"""
    if not key:
        return ""
    if len(key) <= 10:
        return "***" + key[-4:]
    return key[:6] + "..." + key[-4:]


def _mask_cookie(cookie):
    """脱敏显示 Cookie"""
    if not cookie:
        return ""
    if len(cookie) <= 20:
        return "***"
    return cookie[:15] + "...(共" + str(len(cookie)) + "字符)"


@app.route('/api/start', methods=['POST'])
def api_start():
    if agent_state["running"]:
        return jsonify({"success": False, "message": "监控已在运行中"})
    try:
        data = request.json or {}
        window_hwnd = data.get('window_hwnd')
        window_title = data.get('window_title', '')
        mode = data.get('mode', 'screen')  # 默认使用屏幕模式

        cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 构建命令参数
        cmd = ['python', 'main.py']
        cmd.extend(['--mode', mode])  # 添加模式参数
        if window_hwnd:
            cmd.extend(['--window-hwnd', str(window_hwnd)])
            if window_title:
                cmd.extend(['--window-title', window_title])

        proc = subprocess.Popen(
            cmd,
            cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        )
        agent_state["running"] = True
        agent_state["pid"] = proc.pid
        agent_state["started_at"] = datetime.now().isoformat()

        def read_output():
            for line in iter(proc.stdout.readline, ''):
                if line.strip():
                    entry = {"time": datetime.now().strftime('%H:%M:%S'), "text": line.strip(), "level": "INFO"}
                    if any(k in line for k in ['ERROR', 'error']):
                        entry["level"] = "ERROR"
                    elif any(k in line for k in ['WARNING', 'warning']):
                        entry["level"] = "WARNING"
                    elif '匹配' in line and ('成功' in line or '!' in line):
                        entry["level"] = "MATCH"
                    elif '已发送' in line or '回复' in line:
                        entry["level"] = "REPLY"
                    agent_state["logs"].append(entry)
                    if len(agent_state["logs"]) > 200:
                        agent_state["logs"].pop(0)
                    socketio.emit('log', entry)

                    # 解析 [清单] 行，提取匹配目标
                    if '[清单]' in line:
                        target = _parse_matched_target(line)
                        if target:
                            agent_state["matched_targets"].append(target)
                            # 保留最近100条
                            if len(agent_state["matched_targets"]) > 100:
                                agent_state["matched_targets"].pop(0)
                            socketio.emit('matched_target', target)

                if proc.poll() is not None: break
            agent_state["running"] = False
            socketio.emit('status_changed', {"running": False})

        import threading
        threading.Thread(target=read_output, daemon=True).start()
        socketio.emit('status_changed', {"running": True})
        return jsonify({"success": True, "message": "屏幕监控已启动", "pid": proc.pid})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/stop', methods=['POST'])
def api_stop():
    if not agent_state["running"]:
        return jsonify({"success": False, "message": "监控未在运行"})
    try:
        if agent_state["pid"]:
            try: os.kill(agent_state["pid"], 15)
            except: pass
        agent_state["running"] = False
        socketio.emit('status_changed', {"running": False})
        return jsonify({"success": True, "message": "已停止"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ============================================
# 匹配目标清单 API
# ============================================

def _parse_matched_target(log_line):
    """从 [清单] 日志行中解析匹配目标数据"""
    # 格式: [清单] #1 | 用户: xxx | 评论: "yyy" | 回复: zzz | 状态: 已发送/风控拦截
    try:
        import re
        m = re.search(
            r'\[清单\]\s*#(\d+)\s*\|\s*用户:\s*(.+?)\s*\|\s*评论:\s*"(.+?)"\s*\|\s*回复:\s*"(.+?)"\s*\|\s*状态:\s*(.+)',
            log_line
        )
        if m:
            return {
                "id": int(m.group(1)),
                "username": m.group(2).strip(),
                "comment": m.group(3).strip(),
                "reply": m.group(4).strip(),
                "status": m.group(5).strip(),
                "time": datetime.now().strftime('%H:%M:%S'),
            }
    except Exception:
        pass
    return None


@app.route('/api/matched-list')
def api_matched_list():
    """获取匹配目标清单"""
    return jsonify({
        "success": True,
        "data": {
            "total": len(agent_state["matched_targets"]),
            "targets": agent_state["matched_targets"],
        }
    })


@app.route('/api/clear-matched', methods=['POST'])
def api_clear_matched():
    """清空匹配清单"""
    agent_state["matched_targets"] = []
    socketio.emit('matched_cleared')
    return jsonify({"success": True, "message": "清单已清空"})


@socketio.on('connect')
def handle_connect():
    emit('connected', {})
    emit('status_changed', {"running": agent_state["running"]})
    for log in agent_state["logs"][-20:]:
        emit('log', log)
    # 推送已有的匹配目标
    for target in agent_state["matched_targets"]:
        emit('matched_target', target)

if __name__ == '__main__':
    print("  抖音陪玩Agent - 屏幕监控控制面板")
    print("  http://localhost:5001")
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)
