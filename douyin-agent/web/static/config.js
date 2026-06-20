/* ============================================
   配置管理页面 - JavaScript
   ============================================ */

// ====== 全局状态 ======
let configData = null;          // 完整配置数据
let schemaData = null;          // 配置Schema
let originalValues = {};         // 原始值 (用于检测修改)
let currentTab = 'env';         // 当前标签页
let currentGroup = 'intent';    // 当前分组
let modifiedFields = new Set(); // 已修改字段集合

// ====== 初始化 ======
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    setupEventListeners();
});

// ====== 事件监听 ======
function setupEventListeners() {
    // 显示密码切换
    $('show-passwords-toggle')?.addEventListener('change', () => renderFields());

    // 仅显示已修改
    $('show-modified-only')?.addEventListener('change', () => renderFields());

    // 拖拽上传
    const uploadArea = document.getElementById('upload-area');
    if (uploadArea) {
        uploadArea.addEventListener('dragover', e => { e.preventDefault(); uploadArea.classList.add('dragover'); });
        uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
        uploadArea.addEventListener('drop', handleFileDrop);
    }

    // ESC关闭导入框
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') closeImportModal();
    });
}

// ====== 加载配置 ======
async function loadConfig() {
    updateStatus('loading');

    try {
        const [configRes, schemaRes] = await Promise.all([
            fetch('/api/config').then(r => r.json()),
            fetch('/api/config/schema').then(r => r.json()),
        ]);

        if (!configRes.success || !schemaRes.success) {
            throw new Error(configRes.message || schemaRes.message || '加载失败');
        }

        configData = configRes.data;
        schemaData = schemaRes.data;  // schema现在也包装在data中

        // 保存原始值用于比较
        saveOriginalValues();

        // 渲染界面
        renderFileStatus();
        renderTabsCount();
        renderGroupsTabs();
        renderFields();

        updateStatus('ready');
        showToast('配置加载成功', 'success');
    } catch (e) {
        console.error('[配置] 加载失败:', e);
        updateStatus('error');
        showToast('加载失败: ' + e.message, 'error');
    }
}

// ====== 状态更新 ======
function updateStatus(state) {
    const dot = $('status-dot-config');
    const text = $('status-text-config');

    if (!dot || !text) return;

    switch (state) {
        case 'loading':
            dot.className = 'status-dot loading';
            text.textContent = '加载中...';
            break;
        case 'ready':
            dot.className = 'status-dot connected';
            text.textContent = '就绪';
            break;
        case 'saving':
            dot.className = 'status-dot loading';
            text.textContent = '保存中...';
            break;
        case 'saved':
            dot.className = 'status-dot connected';
            text.textContent = '已保存';
            setTimeout(() => { if ($('status-text-config')) $('status-text-config').textContent = '就绪'; }, 2000);
            break;
        case 'error':
            dot.className = 'status-dot disconnected';
            text.textContent = '错误';
            break;
    }
}

// ====== 渲染文件状态 ======
function renderFileStatus() {
    const container = $('file-status-list');
    if (!container || !configData?.files) return;

    const files = configData.files;

    container.innerHTML = `
        <div class="file-item ${files.env_exists ? 'exists' : 'missing'}">
            <span class="file-name">.env</span>
            <span class="file-status-badge ${files.env_exists ? 'badge-exists' : 'badge-missing'}">
                ${files.env_exists ? '存在' : '缺失'}
            </span>
        </div>
        <div class="file-item ${files.secrets_exists ? 'exists' : 'missing'}">
            <span class="file-name">secrets.env</span>
            <span class="file-status-badge ${files.secrets_exists ? 'badge-exists' : 'badge-missing'}">
                ${files.secrets_exists ? '存在' : '缺失'}
            </span>
        </div>
    `;
}

// ====== 渲染标签计数 ======
function renderTabsCount() {
    if (!schemaData) return;

    const envCount = Object.keys(schemaData.env || {}).length;
    const secretsCount = Object.keys(schemaData.secrets || {}).length;

    safeUpdate('count-env', el => { el.textContent = envCount + '项'; });
    safeUpdate('count-secrets', el => { el.textContent = secretsCount + '项'; });
}

// ====== 保存原始值 ======
function saveOriginalValues() {
    originalValues = {};

    if (!configData) return;

    ['env', 'secrets'].forEach(section => {
        if (configData[section]) {
            originalValues[section] = JSON.parse(JSON.stringify(configData[section]));
        }
    });
}

// ====== 切换标签页 ======
function switchTab(tab) {
    currentTab = tab;

    // 更新按钮状态
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });

    // 重置到第一个可用分组
    resetToFirstGroup();

    renderGroupsTabs();
    renderFields();
}

// ====== 重置到第一个分组 ======
function resetToFirstGroup() {
    if (!schemaData) return;

    const fields = schemaData[currentTab] || {};
    let firstGroup = null;

    for (const [key, meta] of Object.entries(fields)) {
        if (meta.group && !firstGroup) {
            firstGroup = meta.group;
            break;
        }
    }

    currentGroup = firstGroup || 'intent';
}

// ====== 渲染分组标签 ======
function renderGroupsTabs() {
    const container = $('groups-tabs-container');
    if (!container || !schemaData) return;

    const groups = schemaData.groups || {};
    const fields = schemaData[currentTab] || {};

    // 收集当前标签使用的分组
    let usedGroups = new Set();
    Object.values(fields).forEach(f => { if (f.group) usedGroups.add(f.group); });

    let html = '';
    let isFirst = true;

    for (const [gid, ginfo] of Object.entries(groups)) {
        if (!usedGroups.has(gid)) continue;

        html += `<button class="group-tab-btn ${isFirst ? 'active' : ''}"
                      data-group="${gid}" onclick="switchGroup('${gid}')">
                    ${ginfo.icon} ${ginfo.name}
                </button>`;
        isFirst = false;
    }

    container.innerHTML = html || '<span style="color:#6b7280;padding:8px;font-size:12px;">无分组</span>';
}

// ====== 切换分组 ======
function switchGroup(groupId) {
    currentGroup = groupId;

    document.querySelectorAll('.group-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.group === groupId);
    });

    renderFields();
}

// ====== 渲染字段 ======
function renderFields() {
    const container = $('fields-container');
    if (!container || !schemaData || !configData) return;

    const fields = schemaData[currentTab] || {};
    const values = configData[currentTab] || {};
    const showModifiedOnly = $('show-modified-only')?.checked;

    // 过滤当前分组的字段
    let groupFields = [];
    for (const [key, meta] of Object.entries(fields)) {
        if (meta.group !== currentGroup) continue;

        const isModified = checkIfModified(key);

        if (showModifiedOnly && !isModified) continue;

        groupFields.push({ key, ...meta, value: values[key], modified: isModified });
    }

    if (groupFields.length === 0) {
        container.innerHTML = `
            <div class="loading-placeholder">
                <p style="font-size:14px;">${showModifiedOnly ? '暂无已修改的配置项' : '此分组暂无配置项'}</p>
            </div>`;
        return;
    }

    let html = '';
    for (const field of groupFields) {
        html += renderFieldCard(field);
    }

    container.innerHTML = html;
    updateModifiedCounter();

    // 绑定输入事件
    bindFieldEvents();
}

// ====== 渲染单个字段卡片 ======
function renderFieldCard(field) {
    const isPassword = field.type === 'password' || field.type === 'textarea';
    const showPasswords = $('show-passwords-toggle')?.checked;
    const inputType = (isPassword && !showPasswords) ? 'password' : (field.type || 'text');

    const value = field.value ?? '';

    // 根据类型生成输入控件
    let inputHtml = '';

    switch (field.type) {
        case 'select':
            inputHtml = `<select id="field-${field.key}">
                ${(field.options || []).map(opt =>
                    `<option value="${opt.value}" ${value === opt.value ? 'selected' : ''}>${opt.label}</option>`
                ).join('')}
            </select>`;
            break;

        case 'textarea':
            inputHtml = `<textarea id="field-${field.key}" placeholder="${field.placeholder || ''}">${escapeHtml(value)}</textarea>`;
            break;

        case 'number':
            inputHtml = `<input type="number" id="field-${field.key}"
                value="${value}" min="${field.min ?? ''}" max="${field.max ?? ''}" step="${field.step ?? 'any'}"
                placeholder="${field.placeholder || ''}">`;
            break;

        default:
            inputHtml = `<input type="${inputType}" id="field-${field.key}"
                value="${value}" placeholder="${field.placeholder || ''}">`;
    }

    return `
        <div class="field-card ${field.modified ? 'modified' : ''}" data-field-key="${field.key}">
            <div class="field-header">
                <label class="field-label" for="field-${field.key}">${field.label}</label>
                <span class="field-key">${field.key}</span>
            </div>
            <div class="field-input-wrap">${inputHtml}</div>
            ${field.description ? `<p class="field-desc">${field.description}</p>` : ''}
        </div>
    `;
}

// ====== 绑定字段事件 ======
function bindFieldEvents() {
    document.querySelectorAll('#fields-container .field-card').forEach(card => {
        const key = card.dataset.fieldKey;
        const input = card.querySelector('input, select, textarea');
        if (!input) return;

        input.addEventListener('input', () => onFieldChange(key, input));
        input.addEventListener('focus', () => onFocusField(key));
        input.addEventListener('blur', () => onBlurField());
    });
}

// ====== 字段值变化 ======
function onFieldChange(key, input) {
    const newValue = input.value.trim();

    // 检测是否与原始值不同
    const oldValue = getOriginalValue(currentTab, key);
    const isChanged = String(newValue) !== String(oldValue);

    if (isChanged) {
        modifiedFields.add(`${currentTab}.${key}`);
    } else {
        modifiedFields.delete(`${currentTab}.${key}`);
    }

    // 更新卡片样式
    const card = document.querySelector(`[data-field-key="${key}"]`);
    if (card) card.classList.toggle('modified', isChanged);

    updateModifiedCounter();
}

// ====== 获取原始值 ======
function getOriginalValue(section, key) {
    return originalValues[section]?.[key] ?? '';
}

// ====== 检查是否修改 ======
function checkIfModified(key) {
    return modifiedFields.has(`${currentTab}.${key}`);
}

// ====== 更新修改计数器 ======
function updateModifiedCounter() {
    const counter = $('modified-counter');
    if (counter) {
        const count = modifiedFields.size;
        counter.textContent = count > 0 ? `${count} 项已修改` : '';
        counter.style.display = count > 0 ? 'inline' : 'none';
    }
}

// ====== 字段焦点信息 ======
function onFocusField(key) {
    const infoEl = $('field-focus-info');
    if (infoEl) {
        infoEl.textContent = `编辑: ${key}`;
    }
}
function onBlurField() {
    const infoEl = $('field-focus-info');
    if (infoEl) infoEl.textContent = '';
}

// ====== 保存所有配置 ======
async function saveAllConfig() {
    if (modifiedFields.size === 0) {
        showToast('没有需要保存的更改', 'info');
        return;
    }

    const btn = $('btn-save-all');
    try {
        btn.disabled = true;
        btn.innerHTML = '&#9203; 保存中...';
        updateStatus('saving');

        // 收集所有字段的值
        const envData = {};
        const secretsData = {};

        document.querySelectorAll('#fields-container .field-card').forEach(card => {
            const key = card.dataset.fieldKey;
            const input = card.querySelector('input, select, textarea');
            if (!key || !input) return;

            const val = input.value.trim();

            if (currentTab === 'env') {
                envData[key] = val;
            } else {
                secretsData[key] = val;
            }
        });

        // 构建请求体
        const payload = {};
        if (Object.keys(envData).length > 0) payload.env = envData;
        if (Object.keys(secretsData).length > 0) payload.secrets = secretsData;

        console.log('[配置] 保存:', payload);

        const res = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        const result = await res.json();

        if (result.success) {
            showToast(`成功保存 ${modifiedFields.size} 项配置!`, 'success');

            // 更新本地缓存
            if (payload.env) {
                configData.env = { ...configData.env, ...payload.env };
            }
            if (payload.secrets) {
                configData.secrets = { ...configData.secrets, ...payload.secrets };
            }

            saveOriginalValues();
            modifiedFields.clear();

            // 更新时间
            safeUpdate('last-saved-time', el => {
                el.textContent = `最后保存: ${new Date().toLocaleTimeString('zh-CN', {hour12:false})}`;
            });

            renderFields();
            updateStatus('saved');
        } else {
            throw new Error(result.message);
        }
    } catch (e) {
        console.error('[配置] 保存失败:', e);
        showToast('保存失败: ' + e.message, 'error');
        updateStatus('error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '&#128190; 保存所有更改';
    }
}

// ====== 重新加载 ======
function reloadConfig() {
    loadConfig();
}

// ====== 导出配置 ======
function exportConfig() {
    if (!configData) {
        showToast('暂无配置可导出', 'warning');
        return;
    }

    const exportObj = {
        exported_at: new Date().toISOString(),
        version: "1.0",
        env: configData.env,
        secrets: configData.secrets,
    };

    const blob = new Blob([JSON.stringify(exportObj, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `douyin-agent-config-${new Date().toISOString().slice(0,10)}.json`;
    a.click();
    URL.revokeObjectURL(url);

    showToast('配置已导出', 'success');
}

// ====== 导入对话框 ======
function showImportDialog() {
    $('import-modal')?.classList.add('active');
}
function closeImportModal(event) {
    if (event && event.target !== event.currentTarget) return;
    $('import-modal')?.classList.remove('active');
    // 清空文件输入
    const fileInput = $('import-file-input');
    if (fileInput) fileInput.value = '';
    $('btn-do-import').disabled = true;
}

// 文件选择
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) enableImportBtn(file);
}
function handleFileDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('dragover');
    const file = event.dataTransfer.files[0];
    if (file) enableImportBtn(file);
}
let importFileData = null;
function enableImportBtn(file) {
    importFileData = file;
    const btn = $('btn-do-import');
    if (btn) btn.disabled = false;
    showToast(`已选择文件: ${file.name}`, 'info');
}

// 执行导入
async function executeImport() {
    if (!importFileData) return;

    const importType = document.querySelector('input[name="import-type"]:checked')?.value || 'all';

    try {
        const text = await importFileData.text();
        let data;

        // 尝试解析JSON
        try {
            data = JSON.parse(text);
        } catch {
            // 如果不是JSON，尝试解析为.env格式
            data = parseEnvFormat(text);
        }

        // 构建请求
        let payload = {};
        if (importType === 'all' || importType === 'env') payload.env = data.env || data;
        if (importType === 'all' || importType === 'secrets') payload.secrets = data.secrets || {};

        const res = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        const result = await res.json();
        if (result.success) {
            showToast('配置导入成功! 正在重新加载...', 'success');
            closeImportModal();
            setTimeout(loadConfig, 500);
        } else {
            throw new Error(result.message);
        }
    } catch (e) {
        showToast('导入失败: ' + e.message, 'error');
    }
}

// 解析.env格式
function parseEnvFormat(text) {
    const lines = text.split('\n');
    const obj = {};
    lines.forEach(line => {
        const s = line.trim();
        if (!s || s.startsWith('#')) return;
        const idx = s.indexOf('=');
        if (idx > 0) {
            obj[s.slice(0, idx).trim()] = s.slice(idx + 1).trim();
        }
    });
    return obj;
}

// ====== 恢复默认 ======
function resetToDefault() {
    if (!confirm('确定要恢复默认配置吗？这将覆盖当前所有设置！')) return;

    // 这里可以调用后端API恢复默认值
    // 目前只是提示用户手动操作
    showToast('请删除 .env 和 secrets.env 后重启服务以恢复默认', 'info');
}

// ====== Toast通知 ======
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => toast.remove(), 3000);
}

// ====== DOM辅助函数 ======
function $(id) { return document.getElementById(id); }
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function safeUpdate(id, callback) {
    const el = $(id);
    if (el) callback(el);
}
