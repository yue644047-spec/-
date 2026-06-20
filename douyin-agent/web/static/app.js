/* ============================================
   抖音陪玩Agent - 前端控制逻辑 v5 (修复版)
   ============================================ */

// ---- 全局状态 ----
let socket = null;
let isRunning = false;
let timerInterval = null;
let startTime = null;
let currentMode = 'local';
let logFilter = 'all';
let matchedTargets = [];
let selectedWindow = null;

// ---- 安全的DOM获取函数 ----
function $(id) {
    return document.getElementById(id);
}

function safeUpdate(id, callback) {
    const el = $(id);
    if (el) callback(el);
}

// ---- 初始化 ----
document.addEventListener('DOMContentLoaded', () => {
    console.log('[前端] DOM加载完成，开始初始化...');
    initSocket();
    refreshWindows();
});

// ====== 全局错误处理 ======
window.onerror = function(msg, url, line, col, error) {
    console.error('[全局错误]', msg, '\n位置:', url, '行:', line);
    return false;
};

// ====== Socket.IO 连接 ======
function initSocket() {
    try {
        socket = io({
            transports: ['websocket'],
            reconnection: true,
            reconnectionAttempts: 10,
            reconnectionDelay: 1000,
        });

        socket.on('connect', () => {
            console.log('[Socket] 已连接到服务器, ID:', socket.id);
            safeUpdate('connection-dot', el => {
                el.className = 'status-dot connected';
            });
            safeUpdate('connection-text', el => {
                el.textContent = '已连接';
            });
            showToast('已连接到服务器', 'success');
        });

        socket.on('disconnect', (reason) => {
            console.log('[Socket] 连接断开:', reason);
            safeUpdate('connection-dot', el => {
                el.className = 'status-dot disconnected';
            });
            safeUpdate('connection-text', el => {
                el.textContent = '未连接';
            });
            showToast('连接断开: ' + reason, 'error');
        });

        socket.on('connect_error', (err) => {
            console.error('[Socket] 连接错误:', err.message);
            showToast('连接失败: ' + err.message, 'error');
        });

        socket.on('connected', () => {
            safeUpdate('connection-dot', el => {
                el.className = 'status-dot connected';
            });
            safeUpdate('connection-text', el => {
                el.textContent = '已连接';
            });
        });

        socket.on('status_changed', (data) => {
            console.log('[Socket] 状态变更:', data);
            isRunning = data.running;
            updateButtons();
            if (isRunning) {
                startTimer();
                safeUpdate('running-status-bar', el => el.classList.add('active'));
                safeUpdate('running-status-text', el => { el.textContent = '监控中...'; });
            } else {
                stopTimer();
                safeUpdate('running-status-bar', el => el.classList.remove('active'));
                safeUpdate('running-status-text', el => { el.textContent = '待机中'; });
            }
        });

        socket.on('log', (data) => appendLog(data));

        socket.on('matched_target', (data) => {
            appendMatchedTarget(data);
            // 更新统计看板
            addMatchRecord(data);
            updateDashboard();
        });

        socket.on('matched_cleared', () => {
            const list = $('matched-list');
            if (list) {
                list.innerHTML = `
                    <div class="empty-state" id="matched-empty">
                        <div class="empty-icon">&#128270;</div>
                        <p>暂无匹配目标</p>
                        <p class="sub">启动监控后，匹配到的评论将在此显示</p>
                    </div>`;
            }
            matchedTargets = [];
            safeUpdate('matched-count-badge', el => { el.textContent = '0 条'; });
            safeUpdate('stat-matches', el => { el.textContent = '0'; });
        });

        socket.on('config_updated', (data) => {
            console.log('[Socket] 配置已更新:', data);
            showToast('配置已同步更新', 'info');
        });

    } catch (e) {
        console.error('[Socket] 初始化失败:', e);
        showToast('Socket初始化失败: ' + e.message, 'error');
    }
}

// ====== 窗口选择 ======
let allWindows = [];  // 存储所有窗口数据
let recommendedWindow = null;  // 推荐的窗口

async function refreshWindows() {
    try {
        const res = await fetch('/api/windows');
        const data = await res.json();

        console.log('[窗口] API返回:', JSON.stringify(data).substring(0, 300));

        // 兼容两种格式: {success, windows} 或 {success, data}
        let windows = [];
        if (data.success) {
            windows = data.windows || data.data || [];
        } else {
            throw new Error(data.message || '获取窗口列表失败');
        }

        if (!Array.isArray(windows)) {
            throw new Error('窗口数据格式错误');
        }

        allWindows = windows;

        const sel = $('window-select');
        if (!sel) {
            console.error('[窗口] 找不到 window-select 元素');
            return;
        }

        // 更新计数标签
        safeUpdate('window-count', el => {
            el.textContent = `(共 ${windows.length} 个)`;
        });

        // 填充下拉列表
        sel.innerHTML = '<option value="">-- 全屏监控 --</option>';

        windows.forEach((w, index) => {
            const opt = document.createElement('option');
            opt.value = w.id || w.hwnd || '';
            opt.textContent = `${w.title || '未知窗口'} (${w.width || 0}×${w.height || 0})`;
            opt.dataset.index = index;
            sel.appendChild(opt);
        });

        // 智能推荐：自动检测浏览器窗口
        recommendedWindow = null;
        const browserKeywords = ['chrome', 'edge', 'firefox', '浏览器', 'douyin', '抖音', 'microsoft edge'];
        const browserWin = windows.find(w =>
            browserKeywords.some(kw => (w.title || '').toLowerCase().includes(kw))
        );

        if (browserWin) {
            recommendedWindow = browserWin;
            console.log('[窗口] 推荐窗口:', browserWin.title);

            // 显示推荐提示
            const recommendEl = $('auto-recommend');
            if (recommendEl) {
                recommendEl.style.display = 'flex';
            }
        } else {
            const recommendEl = $('auto-recommend');
            if (recommendEl) {
                recommendEl.style.display = 'none';
            }
        }

        showToast(`已加载 ${windows.length} 个窗口`, 'info');

    } catch (e) {
        console.error('[窗口] 加载失败:', e);
        showToast('加载窗口失败: ' + e.message, 'error');

        // 更新计数显示错误状态
        safeUpdate('window-count', el => {
            el.textContent = '(加载失败)';
            el.style.color = 'var(--danger)';
        });
    }
}

function onWindowSelect() {
    const sel = $('window-select');
    if (!sel) return;

    const selectedIndex = sel.options[sel.selectedIndex]?.dataset.index;
    const windowData = selectedIndex !== undefined ? allWindows[parseInt(selectedIndex)] : null;

    const detailCard = $('window-detail');
    const recommendEl = $('auto-recommend');

    if (windowData && sel.value) {
        // 显示详细信息卡片
        if (detailCard) {
            detailCard.style.display = 'block';

            // 填充详细数据
            safeUpdate('detail-title', el => {
                el.textContent = windowData.title || '未知窗口';
            });

            safeUpdate('detail-position', el => {
                el.textContent = `(${windowData.x || 0}, ${windowData.y || 0})`;
            });

            safeUpdate('detail-size', el => {
                el.textContent = `${windowData.width || 0} × ${windowData.height || 0}`;
            });

            safeUpdate('detail-handle', el => {
                el.textContent = windowData.id || windowData.hwnd || '-';
            });
        }

        // 隐藏推荐（如果用户手动选择了）
        if (recommendEl && !recommendedWindow) {
            recommendEl.style.display = 'none';
        }

        selectedWindow = windowData;
        console.log('[窗口] 已选择:', windowData.title);

    } else {
        // 隐藏详细信息
        if (detailCard) {
            detailCard.style.display = 'none';
        }

        selectedWindow = null;
    }
}

// 使用推荐窗口
function useRecommendedWindow() {
    if (!recommendedWindow) {
        showToast('没有可用的推荐窗口', 'warning');
        return;
    }

    const sel = $('window-select');
    if (sel) {
        sel.value = recommendedWindow.id || recommendedWindow.hwnd;
        onWindowSelect();

        // 隐藏推荐提示
        const recommendEl = $('auto-recommend');
        if (recommendEl) {
            recommendEl.style.display = 'none';
        }

        showToast(`已使用推荐窗口: ${recommendedWindow.title}`, 'success');
    }
}

// ====== 统计看板 ======
let statsHistory = {
    screenshots: [],  // 截屏历史 [timestamp, count]
    texts: [],        // 文本识别历史
    matches: [],      // 匹配历史
};
let matchRecords = [];  // 匹配记录列表
let trendDataPoints = 10;  // 趋势图显示点数

// 更新统计看板
function updateDashboard() {
    updateMetrics();
    updateTrendChart();
}

// 更新关键指标
function updateMetrics() {
    const screenshots = parseInt($('stat-screenshots')?.textContent) || 0;
    const texts = parseInt($('stat-texts')?.textContent) || 0;
    const matches = parseInt($('stat-matches')?.textContent) || 0;

    // 匹配率
    const matchRate = screenshots > 0 ? ((matches / screenshots) * 100).toFixed(1) : 0;
    safeUpdate('metric-match-rate', el => { el.textContent = matchRate + '%'; });
    safeUpdate('bar-match-rate', el => { el.style.width = Math.min(matchRate, 100) + '%'; });

    // 平均间隔 (基于运行时间)
    const timerText = $('stat-timer')?.textContent || '--:--';
    if (timerText !== '--:--' && startTime) {
        const elapsed = (Date.now() - startTime) / 1000; // 秒
        const avgTime = screenshots > 0 ? (elapsed / screenshots).toFixed(1) : '--';
        safeUpdate('metric-avg-time', el => { el.textContent = avgTime + 's'; });
    }

    // 总评论数 (等于识别文本数)
    safeUpdate('metric-total-comments', el => { el.textContent = texts; });
}

// 更新趋势图
function updateTrendChart() {
    const chartEl = $('trend-chart');
    if (!chartEl) return;

    // 记录当前数据到历史
    const now = Date.now();
    const snapshots = parseInt($('stat-screenshots')?.textContent) || 0;
    const textCount = parseInt($('stat-texts')?.textContent) || 0;
    const matchCount = parseInt($('stat-matches')?.textContent) || 0;

    statsHistory.screenshots.push([now, snapshots]);
    statsHistory.texts.push([now, textCount]);
    statsHistory.matches.push([now, matchCount]);

    // 保持最近N个数据点
    const maxPoints = 20;
    if (statsHistory.screenshots.length > maxPoints) {
        statsHistory.screenshots.shift();
        statsHistory.texts.shift();
        statsHistory.matches.shift();
    }

    // 生成柱状图 (取最近trendDataPoints个)
    const displayPoints = Math.min(statsHistory.screenshots.length, trendDataPoints);
    const startIdx = Math.max(0, statsHistory.screenshots.length - displayPoints);

    let html = '';
    for (let i = startIdx; i < statsHistory.screenshots.length; i++) {
        const snapVal = statsHistory.screenshots[i][1] || 0;
        const textVal = statsHistory.texts[i] || [now, 0];
        const textCountVal = textVal[1] || 0;
        const matchVal = statsHistory.matches[i] || [now, 0];
        const matchCountVal = matchVal[1] || 0;

        // 计算相对高度 (基于最大值归一化)
        const maxVal = Math.max(snapVal, 10);  // 最小基准值10

        const snapHeight = Math.max((snapVal / maxVal) * 100, 2);
        const textHeight = Math.max((textCountVal / maxVal) * 100, 2);
        const matchHeight = Math.max((matchCountVal / maxVal) * 100, 2);

        html += `
            <div class="trend-bar-group">
                <div class="trend-bar trend-bar-blue" style="height: ${snapHeight}%" title="截屏: ${snapVal}"></div>
                <div class="trend-bar trend-bar-green" style="height: ${textHeight}%" title="文本: ${textCountVal}"></div>
                <div class="trend-bar trend-bar-yellow" style="height: ${matchHeight}%" title="匹配: ${matchCountVal}"></div>
            </div>
        `;
    }

    chartEl.innerHTML = html;

    // 更新时间戳
    safeUpdate('trend-update-time', el => {
        const timeStr = new Date().toLocaleTimeString('zh-CN', { hour12: false });
        el.textContent = timeStr + ' 更新';
    });
}

// 添加匹配记录到看板
function addMatchRecord(target) {
    matchRecords.unshift({
        id: target.id,
        comment: target.comment,
        time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    });

    // 只保留最近20条
    if (matchRecords.length > 20) {
        matchRecords.pop();
    }

    renderMatchRecords();
}

// 渲染匹配记录列表
function renderMatchRecords() {
    const listEl = $('matches-list');
    const emptyEl = $('empty-matches');
    if (!listEl) return;

    if (matchRecords.length === 0) {
        listEl.innerHTML = `
            <div class="empty-matches" id="empty-matches">
                <span class="empty-icon">&#128270;</span>
                <p>暂无匹配记录</p>
            </div>
        `;
        return;
    }

    let html = '';
    matchRecords.forEach(record => {
        html += `
            <div class="match-record">
                <span class="match-id-badge">#${record.id}</span>
                <div class="match-content">
                    <div class="match-text">${escapeHtml(record.comment)}</div>
                </div>
                <span class="match-time-text">${record.time}</span>
            </div>
        `;
    });

    listEl.innerHTML = html;
}

// 清空匹配历史
function clearMatchHistory() {
    matchRecords = [];
    renderMatchRecords();
    showToast('匹配记录已清空', 'info');
}

// ====== 配置管理 ======
let configSchema = null;       // 配置元数据
let currentConfig = null;      // 当前配置值
let originalConfig = null;     // 原始配置值 (用于比较)
let currentConfigTab = 'env';  // 当前标签页
let currentGroup = 'intent';   // 当前分组

// 打开配置模态框
async function openConfigModal() {
    const modal = $('config-modal');
    if (!modal) return;

    modal.classList.add('active');

    // 加载配置数据
    try {
        const [configRes, schemaRes] = await Promise.all([
            fetch('/api/config').then(r => r.json()),
            fetch('/api/config/schema').then(r => r.json()),
        ]);

        if (configRes.success && schemaRes.success) {
            configSchema = schemaRes;
            currentConfig = configRes.data;
            originalConfig = JSON.parse(JSON.stringify(configRes.data)); // 深拷贝

            renderConfigTabs();
            renderGroupsNav();
            renderConfigFields();

            updateSecretsBadge();
        } else {
            showToast('加载配置失败', 'error');
        }
    } catch (e) {
        console.error('[配置] 加载失败:', e);
        showToast('加载配置失败: ' + e.message, 'error');
    }
}

// 关闭配置模态框
function closeConfigModal(event) {
    if (event && event.target !== event.currentTarget) return;

    const modal = $('config-modal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// 切换标签页 (公开/敏感)
function switchConfigTab(tab) {
    currentConfigTab = tab;

    // 更新标签按钮状态
    document.querySelectorAll('.config-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });

    renderGroupsNav();
    renderConfigFields();
}

// 渲染标签页
function renderConfigTabs() {
    // 标签已在HTML中定义，无需动态生成
}

// 渲染分组导航
function renderGroupsNav() {
    const navEl = $('config-groups-nav');
    if (!navEl || !configSchema) return;

    const groups = configSchema.groups || {};
    const fields = configSchema[currentConfigTab] || {};

    // 收集当前标签页使用的分组
    let usedGroups = new Set();
    Object.values(fields).forEach(field => {
        if (field.group) usedGroups.add(field.group);
    });

    let html = '';
    let isFirst = true;
    for (const [groupId, groupInfo] of Object.entries(groups)) {
        if (!usedGroups.has(groupId)) continue;

        html += `<button class="group-btn ${isFirst ? 'active' : ''}" data-group="${groupId}" onclick="switchGroup('${groupId}')">
            ${groupInfo.icon} ${groupInfo.name}
        </button>`;
        isFirst = false;
    }

    navEl.innerHTML = html || '<span style="color:var(--text-muted);font-size:12px;">无可用分组</span>';

    // 默认选中第一个分组
    if (usedGroups.size > 0) {
        currentGroup = Array.from(usedGroups)[0];
    }
}

// 切换分组
function switchGroup(groupId) {
    currentGroup = groupId;

    document.querySelectorAll('.group-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.group === groupId);
    });

    renderConfigFields();
}

// 渲染配置字段
function renderConfigFields() {
    const container = $('config-fields-container');
    if (!container || !configSchema || !currentConfig) return;

    const fields = configSchema[currentConfigTab] || {};
    const values = currentConfig[currentConfigTab] || {};

    // 按分组过滤
    let groupFields = [];
    for (const [key, meta] of Object.entries(fields)) {
        if (meta.group === currentGroup) {
            groupFields.push({ key, ...meta, value: values[key] });
        }
    }

    if (groupFields.length === 0) {
        container.innerHTML = `<div class="loading-state">此分组暂无配置项</div>`;
        return;
    }

    // 获取分组信息
    const groups = configSchema.groups || {};
    const groupInfo = groups[currentGroup] || { name: currentGroup };

    let html = `<div class="config-group-section">`;
    html += `<h3 class="config-group-title">${groupInfo.icon || ''} ${groupInfo.name}</h3>`;

    for (const field of groupFields) {
        html += renderSingleField(field);
    }

    html += '</div>';
    container.innerHTML = html;
}

// 渲染单个配置字段
function renderSingleField(field) {
    const isPassword = field.type === 'password' || field.type === 'textarea';
    const showPasswords = $('show-passwords')?.checked;
    const inputType = (isPassword && !showPasswords) ? 'password' : field.type;

    let inputHtml = '';
    const value = field.value ?? '';

    switch (field.type) {
        case 'select':
            inputHtml = `<select id="cfg-${field.key}" data-key="${field.key}">
                ${(field.options || []).map(opt =>
                    `<option value="${opt.value}" ${value === opt.value ? 'selected' : ''}>${opt.label}</option>`
                ).join('')}
            </select>`;
            break;

        case 'textarea':
            inputHtml = `<textarea id="cfg-${field.key}" data-key="${field.key}" placeholder="${field.placeholder || ''}">${escapeHtml(value)}</textarea>`;
            break;

        case 'number':
            inputHtml = `<input type="number" id="cfg-${field.key}" data-key="${field.key}"
                value="${value}" min="${field.min || ''}" max="${field.max || ''}" step="${field.step || 'any'}"
                placeholder="${field.placeholder || ''}">`;
            break;

        case 'password':
        default:
            inputHtml = `<input type="${inputType}" id="cfg-${field.key}" data-key="${field.key}"
                value="${value}" placeholder="${field.placeholder || ''}">`;
    }

    return `
        <div class="config-field" data-field="${field.key}">
            <label>${field.label}</label>
            <div style="position:relative;">
                ${inputHtml}
                ${field.description ? `<div class="field-desc">${field.description}</div>` : ''}
            </div>
        </div>
    `;
}

// 更新敏感配置徽章状态
function updateSecretsBadge() {
    const badge = document.querySelector('.secrets-badge');
    if (!badge || !currentConfig) return;

    const secrets = currentConfig.secrets || {};
    const hasContent = Object.values(secrets).some(v => v && v !== '' && v !== '***');

    badge.textContent = hasContent ? '已配置' : '未设置';
    badge.classList.toggle('set', hasContent);
}

// 监听显示密码复选框
document.addEventListener('DOMContentLoaded', () => {
    const cb = $('show-passwords');
    if (cb) {
        cb.addEventListener('change', () => {
            renderConfigFields(); // 重新渲染以更新密码可见性
        });
    }
});

// 保存完整配置
async function saveFullConfig() {
    const btn = $('btn-save-config');
    if (!btn) return;

    try {
        btn.disabled = true;
        btn.innerHTML = '&#9203; 保存中...';

        // 收集表单数据
        const envData = {};
        const secretsData = {};

        document.querySelectorAll('#config-form .config-field').forEach(el => {
            const key = el.dataset.field;
            const input = el.querySelector('input, select, textarea');
            if (!key || !input) return;

            const value = input.value.trim();

            // 根据当前标签页分类
            if (currentConfigTab === 'env') {
                envData[key] = value;
            } else {
                secretsData[key] = value;
            }
        });

        // 构建请求数据
        const payload = {};
        if (Object.keys(envData).length > 0) payload.env = envData;
        if (Object.keys(secretsData).length > 0) payload.secrets = secretsData;

        console.log('[配置] 保存数据:', payload);

        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        const result = await response.json();

        if (result.success) {
            showToast('配置已保存成功!', 'success');

            // 更新本地缓存
            if (payload.env) {
                currentConfig.env = { ...currentConfig.env, ...payload.env };
            }
            if (payload.secrets) {
                currentConfig.secrets = { ...currentConfig.secrets, ...payload.secrets };
            }
            originalConfig = JSON.parse(JSON.stringify(currentConfig));

            // 同步快速配置面板
            syncQuickConfigPanel();

            // 2秒后关闭模态框
            setTimeout(() => closeConfigModal(), 1500);
        } else {
            showToast('保存失败: ' + result.message, 'error');
        }
    } catch (e) {
        console.error('[配置] 保存错误:', e);
        showToast('保存失败: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '&#128190; 保存配置';
    }
}

// 同步快速配置面板的值
function syncQuickConfigPanel() {
    if (!currentConfig?.env) return;

    const intervalEl = $('cfg-interval');
    const ocrEl = $('cfg-ocr-threshold');

    if (intervalEl && currentConfig.env.CAPTURE_INTERVAL) {
        intervalEl.value = currentConfig.env.CAPTURE_INTERVAL;
    }
    if (ocrEl && currentConfig.env.OCR_CONFIDENCE_THRESHOLD) {
        ocrEl.value = currentConfig.env.OCR_CONFIDENCE_THRESHOLD;
    }
}

// 快速保存 (参数配置区域)
async function saveQuickConfig() {
    const intervalEl = $('cfg-interval');
    const ocrEl = $('cfg-ocr-threshold');

    if (!intervalEl || !ocrEl) return;

    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                env: {
                    CAPTURE_INTERVAL: intervalEl.value,
                    OCR_CONFIDENCE_THRESHOLD: ocrEl.value,
                }
            }),
        });

        const result = await response.json();
        if (result.success) {
            showToast('配置已保存', 'success');
        } else {
            showToast('保存失败: ' + result.message, 'error');
        }
    } catch (e) {
        showToast('保存失败: ' + e.message, 'error');
    }
}

// ====== 意图识别模式 ======
function setMode(mode) {
    currentMode = mode;
    const selectEl = $('cfg-intent-mode');
    if (selectEl) {
        selectEl.value = mode;
    }
    console.log('[意图模式] 切换至:', mode);
}

// ====== 监控控制 ======
async function startMonitor() {
    try {
        const intervalInput = $('cfg-interval');
        const interval = intervalInput ? intervalInput.value : 3;
        const windowSel = $('window-select');
        const hwnd = windowSel ? windowSel.value : '';
        const title = selectedWindow ? selectedWindow.text : '';
        const intentModeSelect = $('cfg-intent-mode');
        const intentMode = intentModeSelect ? intentModeSelect.value : 'local';

        console.log('[启动] 意图模式:', intentMode, '窗口:', hwnd || '全屏', '间隔:', interval);

        const res = await fetch('/api/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                mode: 'screen',
                intent_mode: intentMode,
                window_hwnd: hwnd,
                window_title: title,
                interval: parseFloat(interval),
            }),
        });

        const data = await res.json();
        if (data.success) {
            isRunning = true;
            updateButtons();
            startTimer();
            safeUpdate('running-status-bar', el => el.classList.add('active'));
            safeUpdate('running-status-text', el => { el.textContent = '监控中...'; });
            showToast(`监控已启动 (${currentMode})`, 'success');
        } else {
            throw new Error(data.message || '启动失败');
        }
    } catch (e) {
        console.error('[启动] 失败:', e);
        showToast('启动失败: ' + e.message, 'error');
    }
}

async function stopMonitor() {
    try {
        const res = await fetch('/api/stop', {method: 'POST'});
        const data = await res.json();

        if (data.success) {
            isRunning = false;
            updateButtons();
            stopTimer();
            safeUpdate('running-status-bar', el => el.classList.remove('active'));
            safeUpdate('running-status-text', el => { el.textContent = '已停止'; });
            showToast('监控已停止', 'info');
        } else {
            throw new Error(data.message || '停止失败');
        }
    } catch (e) {
        console.error('[停止] 失败:', e);
        showToast('停止失败: ' + e.message, 'error');
    }
}

async function diagnoseCapture() {
    try {
        const windowSel = $('window-select');
        const hwnd = windowSel ? windowSel.value : '';

        const res = await fetch('/api/diagnose', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({window_hwnd: hwnd}),
        });

        const data = await res.json();
        if (data.success) {
            showToast('截屏诊断完成，查看日志', 'success');
        } else {
            throw new Error(data.message || '诊断失败');
        }
    } catch (e) {
        console.error('[诊断] 失败:', e);
        showToast('诊断失败: ' + e.message, 'error');
    }
}

function updateButtons() {
    safeUpdate('btn-start', el => { el.disabled = isRunning; });
    safeUpdate('btn-stop', el => { el.disabled = !isRunning; });
}

// ====== 配置保存 ======
async function saveConfig() {
    try {
        const intervalInput = $('cfg-interval');
        const ocrInput = $('cfg-ocr-threshold');
        const intentModeSelect = $('cfg-intent-mode');

        const interval = intervalInput ? intervalInput.value : '3';
        const ocrThreshold = ocrInput ? ocrInput.value : '0.5';
        const intentMode = intentModeSelect ? intentModeSelect.value : 'local';

        const res = await fetch('/api/config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                CAPTURE_INTERVAL: interval,
                OCR_CONFIDENCE_THRESHOLD: ocrThreshold,
                INTENT_MODE: intentMode,
            }),
        });

        const data = await res.json();
        showToast(data.success ? '配置已保存' : '保存失败: ' + (data.message || '未知错误'),
                   data.success ? 'success' : 'error');
    } catch (e) {
        console.error('[配置] 保存失败:', e);
        showToast('保存失败: ' + e.message, 'error');
    }
}

// ====== 计时器 ======
function startTimer() {
    if (timerInterval) return;
    startTime = Date.now();
    timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const h = String(Math.floor(elapsed / 3600)).padStart(2, '0');
        const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
        const s = String(elapsed % 60).padStart(2, '0');
        safeUpdate('stat-timer', el => { el.textContent = h + ':' + m + ':' + s; });

        // 每5秒更新一次统计看板
        if (elapsed % 5 === 0) {
            updateDashboard();
        }
    }, 1000);

    // 初始化趋势图
    updateTrendChart();
}

function stopTimer() {
    clearInterval(timerInterval);
    timerInterval = null;
    startTime = null;
    safeUpdate('stat-timer', el => { el.textContent = '--:--:--'; });
}

// ====== 日志系统 ======
function appendLog(entry) {
    if (!entry) return;

    const text = entry.text || '';
    const level = entry.level || 'INFO';

    // 更新统计
    if (text.includes('截屏') && (text.includes('#') || text.includes('成功'))) {
        safeUpdate('stat-screenshots', el => {
            el.textContent = parseInt(el.textContent || '0') + 1;
        });
    }

    // 日志过滤
    if (logFilter !== 'all' && level !== logFilter) return;

    const list = $('log-list');
    if (!list) {
        console.warn('[日志] 找不到 log-list 元素');
        return;
    }

    const div = document.createElement('div');
    div.className = 'log-entry';
    div.innerHTML =
        '<span class="log-time">' + escapeHtml(entry.time || '') + '</span>' +
        '<span class="log-level log-level-' + level + '">' + level + '</span>' +
        '<span class="log-msg">' + escapeHtml(text) + '</span>';

    list.appendChild(div);

    // 自动滚动到底部
    list.scrollTop = list.scrollHeight;

    // 限制日志数量（保留最新500条）
    while (list.children.length > 500) {
        list.removeChild(list.firstChild);
    }
}

function setLogFilter(filter) {
    logFilter = filter;
    document.querySelectorAll('.filter-chips .chip').forEach(c => {
        c.classList.toggle('active', c.dataset.filter === filter);
    });
    console.log('[日志] 过滤器切换至:', filter);
}

function clearLogs() {
    const list = $('log-list');
    if (list) {
        list.innerHTML = '';
    }
    showToast('日志已清空', 'info');
}

// ====== 匹配目标清单 ======
function appendMatchedTarget(target) {
    if (!target) return;

    console.log('[清单] 新匹配目标:', target);

    matchedTargets.push(target);

    // 移除空状态提示
    const emptyEl = $('matched-empty');
    if (emptyEl) emptyEl.remove();

    const list = $('matched-list');
    if (!list) {
        console.warn('[清单] 找不到 matched-list 元素');
        return;
    }

    // 创建卡片
    const item = document.createElement('div');
    item.className = 'matched-item';
    item.id = 'matched-' + target.id;

    item.innerHTML =
        '<div class="matched-id">' + target.id + '</div>' +
        '<div class="matched-body">' +
        '  <div class="matched-user">' + escapeHtml(target.username || '未知用户') + '</div>' +
        '  <div class="matched-comment">"' + escapeHtml(target.comment || '') + '"</div>' +
        '  <div class="matched-reply">&#9993; 建议回复: ' + escapeHtml(target.reply || '') + '</div>' +
        '</div>' +
        '<div class="matched-meta">' +
        '  <div class="matched-time">' + (target.time || '') + '</div>' +
        '</div>';

    // 插入到列表顶部
    list.insertBefore(item, list.firstChild);

    // 更新计数
    safeUpdate('matched-count-badge', el => {
        el.textContent = matchedTargets.length + ' 条';
    });
    safeUpdate('stat-matches', el => {
        el.textContent = matchedTargets.length;
    });

    // 限制显示数量（保留最新50条）
    while (list.children.length > 50) {
        list.lastChild.remove();
    }
}

async function clearMatchedList() {
    try {
        const res = await fetch('/api/clear-matched', {method: 'POST'});
        const data = await res.json();

        if (data.success) {
            matchedTargets = [];
            safeUpdate('stat-matches', el => { el.textContent = '0'; });
            showToast('清单已清空', 'info');
        } else {
            throw new Error(data.message || '清空失败');
        }
    } catch (e) {
        console.error('[清单] 清空失败:', e);
        showToast('清空失败: ' + e.message, 'error');
    }
}

async function exportMatchedList() {
    try {
        if (matchedTargets.length === 0) {
            showToast('暂无数据可导出', 'warning');
            return;
        }

        // 生成 CSV 内容（带 BOM 以支持 Excel 中文）
        let csv = '\uFEFF序号,用户名,评论内容,建议回复,时间\n';
        matchedTargets.forEach(t => {
            const row = [
                t.id,
                (t.username || '').replace(/"/g, '""'),
                (t.comment || '').replace(/"/g, '""'),
                (t.reply || '').replace(/"/g, '""'),
                t.time || ''
            ].map(field => `"${field}"`).join(',');
            csv += row + '\n';
        });

        // 创建下载链接
        const blob = new Blob([csv], {type: 'text/csv;charset=utf-8'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'matched_targets_' + new Date().toISOString().slice(0, 10) + '.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showToast(`已导出 ${matchedTargets.length} 条记录`, 'success');

    } catch (e) {
        console.error('[导出] 失败:', e);
        showToast('导出失败: ' + e.message, 'error');
    }
}

// ====== 工具函数 ======
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function showToast(msg, type) {
    type = type || 'info';
    console.log('[Toast]', type.toUpperCase(), ':', msg);

    const container = $('toast-container');
    if (!container) {
        console.warn('[Toast] 找不到 toast-container 元素');
        alert(msg);  // 降级处理
        return;
    }

    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.textContent = msg;

    container.appendChild(toast);

    // 3秒后自动移除
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 3000);
}
