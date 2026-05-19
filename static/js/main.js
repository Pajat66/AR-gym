// 主应用逻辑
let currentPage = 'home';
let currentMenu = null;

// 训练结束/保存二次确认状态
let stopConfirmPending = false;
let saveConfirmPending = false;
let stopConfirmTimer = null;
let saveConfirmTimer = null;

// 统计图表实例
let statsChart = null;

// 当前登录用户信息（从 /api/me 获取）
let currentUser = null;

// AI虚拟教练上下文
let aiCoachHistory = [];
let toastTimer = null;

// 手势虚拟鼠标模式：'gesture' | 'mouse'
window.handMouseMode = 'gesture';
// 手势虚拟鼠标开关（根据页面和模式综合决定）
window.handMouseEnabled = false;
// 手势导航（1/2/3/4/5 指进入训练）开关，需手动点击“开始识别”开启
window.gestureNavEnabled = false;

// 简单语音播报封装（基于浏览器 Web Speech API）
function speak(text, lang = 'zh-CN') {
    try {
        if (!('speechSynthesis' in window)) {
            console.warn('当前浏览器不支持语音合成');
            return;
        }
        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = lang;
        window.speechSynthesis.speak(utter);
    } catch (e) {
        console.warn('语音播报失败:', e);
    }
}

// 暴露到全局，供其他模块调用
window.speak = speak;

function showToast(message, type = 'success') {
    const toast = document.getElementById('app-toast');
    if (!toast) {
        alert(message);
        return;
    }

    toast.textContent = message;
    toast.className = `app-toast show ${type}`;

    if (toastTimer) {
        clearTimeout(toastTimer);
    }
    toastTimer = setTimeout(() => {
        toast.classList.remove('show');
    }, 3200);
}

// 创建手势虚拟鼠标元素，并暴露更新方法
document.addEventListener('DOMContentLoaded', () => {
    const cursor = document.createElement('div');
    cursor.id = 'hand-mouse-cursor';
    document.body.appendChild(cursor);
});

window.updateHandMouseCursor = function(x, y, click = false) {
    const cursor = document.getElementById('hand-mouse-cursor');
    if (!cursor) return;

    if (!window.handMouseEnabled) {
        cursor.style.display = 'none';
        return;
    }

    cursor.style.display = 'block';
    cursor.style.left = `${x}px`;
    cursor.style.top = `${y}px`;

    if (click) {
        cursor.style.transform = 'translate(-50%, -50%) scale(0.8)';
        setTimeout(() => {
            cursor.style.transform = 'translate(-50%, -50%) scale(1)';
        }, 100);

        // 在页面内模拟一次点击事件（不能控制系统鼠标，只能点击网页元素）
        const el = document.elementFromPoint(x, y);
        if (el) {
            el.click();
        }
    }
};

// 切换首页手势识别 / 鼠标模式
function toggleHandMode() {
    const btn = document.getElementById('hand-mode-toggle');
    if (window.handMouseMode === 'gesture') {
        window.handMouseMode = 'mouse';
        if (btn) btn.textContent = '切换为手势模式';
        if (typeof window.speak === 'function') {
            window.speak('已切换为鼠标模式');
        }
    } else {
        window.handMouseMode = 'gesture';
        if (btn) btn.textContent = '切换为鼠标模式';
        if (typeof window.speak === 'function') {
            window.speak('已切换为手势模式');
        }
    }

    // 根据当前页面立即更新虚拟鼠标开关：
    // 启用鼠标模式时，在所有页面启用手势鼠标（训练过程中由姿态检测代码单独关闭）
    if (window.handMouseMode === 'mouse') {
        window.handMouseEnabled = true;
    } else {
        window.handMouseEnabled = false;
    }
}

// 切换手势导航开关（控制是否用 1~5 手指进入训练）
function toggleGestureNav() {
    const btn = document.getElementById('gesture-nav-toggle');
    window.gestureNavEnabled = !window.gestureNavEnabled;

    if (btn) {
        btn.textContent = window.gestureNavEnabled ? '停止识别' : '开始识别';
    }

    if (typeof window.speak === 'function') {
        window.speak(window.gestureNavEnabled ? '已开启手势识别导航' : '已关闭手势识别导航');
    }
}

// ===== 用户登录 / 注册相关 =====
function toggleAuthPanel(forceOpen) {
    const panel = document.getElementById('auth-panel');
    if (!panel) return;
    if (forceOpen === true) {
        panel.classList.add('open');
    } else if (forceOpen === false) {
        panel.classList.remove('open');
    } else {
        panel.classList.toggle('open');
    }
}

function switchAuthTab(tab) {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');
    if (!loginForm || !registerForm || !tabLogin || !tabRegister) return;

    if (tab === 'login') {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
        tabLogin.classList.add('active');
        tabRegister.classList.remove('active');
    } else {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
        tabLogin.classList.remove('active');
        tabRegister.classList.add('active');
    }
}

function updateAuthUI() {
    const label = document.getElementById('auth-user-label');
    const btnShowAuth = document.getElementById('btn-show-auth');
    const btnLogout = document.getElementById('btn-logout');
    if (!label || !btnShowAuth || !btnLogout) return;

    if (currentUser) {
        label.textContent = `已登录：${currentUser.username}`;
        btnShowAuth.style.display = 'none';
        btnLogout.style.display = 'inline-block';
        // 已登录时隐藏首页登录/注册面板
        toggleAuthPanel(false);
    } else {
        label.textContent = '未登录';
        btnShowAuth.style.display = 'inline-block';
        btnLogout.style.display = 'none';
        // 未登录时默认展示首页登录/注册面板，方便用户操作
        toggleAuthPanel(true);
    }
}

async function fetchCurrentUser() {
    try {
        const res = await fetch('/api/me');
        if (res.status === 401) {
            currentUser = null;
            updateAuthUI();
            return;
        }
        const result = await res.json();
        if (result.success) {
            currentUser = result.data;
        } else {
            currentUser = null;
        }
        updateAuthUI();
    } catch (e) {
        console.error('获取当前用户失败:', e);
    }
}

async function submitLogin(event) {
    event.preventDefault();
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value.trim();
    const errorEl = document.getElementById('login-error');
    if (errorEl) {
        errorEl.style.display = 'none';
        errorEl.textContent = '';
    }

    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const result = await res.json();
        if (!result.success) {
            if (errorEl) {
                errorEl.textContent = result.error || '登录失败';
                errorEl.style.display = 'block';
            } else {
                alert(result.error || '登录失败');
            }
            return false;
        }
        currentUser = result.data;
        updateAuthUI();
        showToast(`欢迎回来，${currentUser.username}`, 'success');
        loadStats();
        loadHistory();
        loadStatsChart();
        return false;
    } catch (e) {
        console.error('登录请求失败:', e);
        if (errorEl) {
            errorEl.textContent = '登录请求失败，请稍后重试';
            errorEl.style.display = 'block';
        }
        return false;
    }
}

async function submitRegister(event) {
    event.preventDefault();
    const username = document.getElementById('register-username').value.trim();
    const password = document.getElementById('register-password').value.trim();
    const errorEl = document.getElementById('register-error');
    if (errorEl) {
        errorEl.style.display = 'none';
        errorEl.textContent = '';
    }

    if (password.length < 6) {
        if (errorEl) {
            errorEl.textContent = '密码长度至少为6位';
            errorEl.style.display = 'block';
        }
        return false;
    }

    try {
        const res = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const result = await res.json();
        if (!result.success) {
            if (errorEl) {
                errorEl.textContent = result.error || '注册失败';
                errorEl.style.display = 'block';
            } else {
                alert(result.error || '注册失败');
            }
            return false;
        }
        currentUser = result.data;
        updateAuthUI();
        showToast(`注册成功，欢迎 ${currentUser.username}`, 'success');
        loadStats();
        loadHistory();
        loadStatsChart();
        return false;
    } catch (e) {
        console.error('注册请求失败:', e);
        if (errorEl) {
            errorEl.textContent = '注册请求失败，请稍后重试';
            errorEl.style.display = 'block';
        }
        return false;
    }
}

async function logoutUser() {
    try {
        await fetch('/api/logout', { method: 'POST' });
    } catch (e) {
        console.error('退出登录请求失败:', e);
    }
    currentUser = null;
    updateAuthUI();
    showToast('已退出登录', 'info');
}

// 请求摄像头权限
async function requestCameraPermission() {
    try {
        console.log('请求摄像头权限...');
        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'user' // 前置摄像头
            } 
        });
        console.log('✓ 摄像头权限已授予');
        
        // 立即停止流，我们会在需要时重新获取
        stream.getTracks().forEach(track => track.stop());
        
        // 更新页面提示
        const videoElement = document.getElementById('input_video');
        if (videoElement) {
            videoElement.style.border = '2px solid #4CAF50';
        }
    } catch (error) {
        console.error('✗ 摄像头权限被拒绝或不可用:', error);
        console.error('错误类型:', error.name);
        console.error('错误信息:', error.message);
        
        if (error.name === 'NotAllowedError') {
            alert('摄像头权限被拒绝。请在浏览器设置中允许摄像头访问，然后刷新页面。');
        } else if (error.name === 'NotFoundError') {
            alert('未检测到摄像头设备。请连接摄像头后刷新页面。');
        } else {
            alert('无法访问摄像头: ' + error.message);
        }
    }
}

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    showPage('home');
    fetchCurrentUser();
    loadStats();
    loadHistory();
    loadVideos(); // 加载视频列表
    loadStatsChart(); // 加载统计折线图
    
    // 先请求摄像头权限（即使MediaPipe未加载）
    requestCameraPermission();
    
    // 等待MediaPipe加载完成后再启动手部检测
    let mediaPipeCheckCount = 0;
    const maxMediaPipeChecks = 50; // 最多检查10秒
    
    function initAfterMediaPipe() {
        mediaPipeCheckCount++;
        
        if (window.MediaPipe && window.MediaPipe.Hands && window.MediaPipe.Camera) {
            console.log('✓ MediaPipe已就绪，启动手部检测并预热姿态检测');
            // 1) 手部检测：用于首页手势导航/手势鼠标
            startHandDetection();
            // 2) 预热姿态检测：提前加载 Pose 模型，减少第一次开始训练的等待时间
            if (typeof initPoseDetection === 'function') {
                initPoseDetection();
            }
            return;
        }
        
        if (mediaPipeCheckCount >= maxMediaPipeChecks) {
            console.error('✗ MediaPipe加载超时，手部检测功能将不可用');
            console.error('请检查：');
            console.error('1. 网络连接是否正常');
            console.error('2. 是否能访问 https://cdn.jsdelivr.net');
            console.error('3. 查看控制台是否有MediaPipe加载错误');
            console.error('4. 尝试刷新页面 (Ctrl+F5)');
            return;
        }
        
        // 只在每5次检查时输出一次日志，减少控制台噪音
        if (mediaPipeCheckCount % 5 === 0) {
            console.log(`等待MediaPipe加载... (${mediaPipeCheckCount}/${maxMediaPipeChecks})`);
        }
        
        setTimeout(initAfterMediaPipe, 200);
    }
    
    // 监听MediaPipe加载完成事件
    window.addEventListener('mediapipeLoaded', function() {
        if (window.MediaPipe) {
            console.log('收到MediaPipe加载完成事件');
            initAfterMediaPipe();
        } else {
            console.error('MediaPipe加载失败，某些功能可能无法使用');
            console.error('请检查浏览器控制台的错误信息');
            console.error('查看Network标签，检查哪些资源加载失败');
        }
    });
    
    // 如果事件已经触发，直接检查
    setTimeout(initAfterMediaPipe, 500);
});

// 页面切换
function showPage(pageName) {
    // 隐藏所有页面
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    
    // 显示目标页面
    const targetPage = document.getElementById(pageName + '-page');
    if (targetPage) {
        targetPage.classList.add('active');
        currentPage = pageName;
    }
    
    // 根据页面和模式启用/禁用手势虚拟鼠标：
    // 启用鼠标模式时，在所有页面启用手势鼠标（训练过程中由姿态检测代码单独关闭）
    if (window.handMouseMode === 'mouse') {
        window.handMouseEnabled = true;
    } else {
        window.handMouseEnabled = false;
    }
}

// 开始训练（选择部位）
function startExercise(type) {
    showPage('exercise');
    
    if (type === 'upper_body') {
        showMenu('upper-body-menu');
    } else if (type === 'lower_body') {
        showMenu('lower-body-menu');
    }
}

// 显示菜单
function showMenu(menuId) {
    // 隐藏所有菜单（包括总菜单和子菜单）
    document.querySelectorAll('.menu-section').forEach(menu => {
        menu.style.display = 'none';
    });
    
    // 隐藏训练界面
    document.getElementById('training-interface').style.display = 'none';
    
    // 显示目标菜单
    const targetMenu = document.getElementById(menuId);
    if (targetMenu) {
        targetMenu.style.display = 'block';
        currentMenu = menuId;
    }
}

// 选择运动类型
function selectExercise(exerciseType) {
    if (exerciseType === 'barbell_curl') {
        showMenu('barbell-curl-menu');
    } else if (exerciseType === 'barbell_sit') {
        showMenu('barbell-sit-menu');
    } else {
        // 直接开始训练
        startExerciseType(exerciseType);
    }
}

// 开始特定类型的训练
function startExerciseType(exerciseType) {
    // 隐藏所有菜单
    document.querySelectorAll('.menu-section').forEach(menu => {
        menu.style.display = 'none';
    });
    
    // 显示训练界面
    const trainingInterface = document.getElementById('training-interface');
    trainingInterface.style.display = 'block';
    
    // 显示训练信息，隐藏视频容器
    const trainingInfo = trainingInterface.querySelector('.training-info');
    const videoContainer = document.getElementById('training-video-container');
    trainingInfo.style.display = 'block';
    videoContainer.style.display = 'none';
    
    // 更新标题
    const exerciseNames = {
        'pushup': '俯卧撑计数',
        'squat': '蹲起',
        'reverse_crunch': '反向卷腹',
        'barbell_curl_left': '左侧杠铃弯举',
        'barbell_curl_right': '右侧杠铃弯举',
        'barbell_sit_left': '左侧杠铃坐姿',
        'barbell_sit_right': '右侧杠铃坐姿'
    };
    
    const exerciseName = exerciseNames[exerciseType] || '训练中';
    document.getElementById('exercise-title').textContent = exerciseName;
    document.getElementById('training-exercise-name').textContent = exerciseName;
    document.getElementById('training-exercise-desc').textContent = '请确保摄像头已开启，站在摄像头前准备开始训练';
    
    // 重置计数
    document.getElementById('exercise-count').textContent = '0';
    document.getElementById('exercise-angle').textContent = '0°';
    document.getElementById('exercise-fps').textContent = '0';
    
    // 保存当前训练类型
    window.currentExerciseType = exerciseType;
}

// 从按钮开始训练
function startTrainingFromButton() {
    if (!window.currentExerciseType) {
        alert('请先选择训练类型');
        return;
    }
    
    // 隐藏训练信息，显示视频容器
    const trainingInfo = document.querySelector('.training-info');
    const videoContainer = document.getElementById('training-video-container');
    trainingInfo.style.display = 'none';
    videoContainer.style.display = 'block';
    
    // 开始姿态检测
    startTraining(window.currentExerciseType);
}

// 停止训练（一次点击确认即可结束）
function stopExercise() {
    const confirmed = window.confirm('确定要结束本次训练吗？');
    if (!confirmed) return;

    // 停止姿态检测与摄像头
    stopTraining();

    // 重置训练界面UI
    const trainingInterface = document.getElementById('training-interface');
    const trainingInfo = trainingInterface ? trainingInterface.querySelector('.training-info') : null;
    const videoContainer = document.getElementById('training-video-container');
    if (trainingInfo) trainingInfo.style.display = 'block';
    if (videoContainer) videoContainer.style.display = 'none';

    // 清空当前训练类型，避免下次“开始训练”直接继续上次
    window.currentExerciseType = null;

    if (typeof window.speak === 'function') {
        window.speak('训练已结束');
    }

    // 返回首页
    backToHome();
}

// 返回首页
function backToHome() {
    showPage('home');
    currentMenu = null;
}

function fillAiPrompt(text) {
    const input = document.getElementById('ai-chat-input');
    if (!input) return;
    input.value = text;
    input.focus();
}

function appendAiMessage(role, content, isLoading = false) {
    const messages = document.getElementById('ai-chat-messages');
    if (!messages) return null;

    const row = document.createElement('div');
    row.className = `chat-message ${role}`;
    if (isLoading) row.classList.add('loading-message');

    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    bubble.textContent = content;

    row.appendChild(bubble);
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
    return row;
}

async function submitAiCoachMessage(event) {
    event.preventDefault();
    const input = document.getElementById('ai-chat-input');
    const submitBtn = document.getElementById('ai-chat-submit');
    if (!input) return false;

    const message = input.value.trim();
    if (!message) {
        showToast('请输入要咨询的问题', 'warning');
        return false;
    }

    appendAiMessage('user', message);
    input.value = '';
    const loadingRow = appendAiMessage('assistant', 'AI教练正在分析...', true);

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = '思考中';
    }

    try {
        const response = await fetch('/api/ai_coach', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                history: aiCoachHistory
            })
        });
        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'AI教练暂时无法回复');
        }

        const reply = result.data.reply || '我暂时没有生成有效回复，请换一种问法试试。';
        if (loadingRow) {
            loadingRow.classList.remove('loading-message');
            const bubble = loadingRow.querySelector('.chat-bubble');
            if (bubble) bubble.textContent = reply;
        }

        aiCoachHistory.push({ role: 'user', content: message });
        aiCoachHistory.push({ role: 'assistant', content: reply });
        aiCoachHistory = aiCoachHistory.slice(-10);
    } catch (error) {
        if (loadingRow) {
            loadingRow.remove();
        }
        appendAiMessage('assistant', `调用失败：${error.message}`);
        showToast('AI教练调用失败，请稍后重试', 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = '发送';
        }
    }

    return false;
}

// 保存运动数据（需要二次确认，并在保存后结束训练）
async function saveExerciseData() {
    if (!window.currentExerciseType || !window.exerciseData || window.exerciseData.count === 0) {
        showToast('没有可保存的数据', 'warning');
        return;
    }

    if (!saveConfirmPending) {
        saveConfirmPending = true;
        if (saveConfirmTimer) {
            clearTimeout(saveConfirmTimer);
        }
        saveConfirmTimer = setTimeout(() => {
            saveConfirmPending = false;
        }, 5000);

        if (typeof window.speak === 'function') {
            window.speak('再次点击保存数据将结束本次训练');
        }
        showToast('再次点击“保存数据”将保存本次训练并结束训练', 'warning');
        return;
    }

    saveConfirmPending = false;
    if (saveConfirmTimer) {
        clearTimeout(saveConfirmTimer);
        saveConfirmTimer = null;
    }

    const duration = Math.floor((Date.now() - window.exerciseData.startTime) / 1000);

    const data = {
        exercise_type: window.currentExerciseType,
        count: window.exerciseData.count,
        duration: duration,
        angle_data: window.exerciseData.angles
    };
    
    try {
        const response = await fetch('/api/save_exercise', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.status === 401) {
            showToast('请先登录后再保存训练数据', 'warning');
            toggleAuthPanel(true);
            showPage('home');
            return;
        }

        const result = await response.json();
        
        if (result.success) {
            showToast('数据保存成功，本次训练已结束', 'success');
            if (typeof window.speak === 'function') {
                window.speak('数据保存成功，本次训练已结束');
            }
            loadStats();
            loadHistory();
            loadStatsChart(); // 同步刷新折线图
            // 保存成功后结束训练并返回首页，避免后台仍有占用
            stopTraining();
            backToHome();
        } else {
            showToast('保存失败: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('保存失败: ' + error.message, 'error');
    }
}

// 加载统计数据
async function loadStats() {
    try {
        const response = await fetch('/api/get_stats');
        if (response.status === 401) {
            // 未登录时不报错，只是不展示数据
            displayStats([]);
            return;
        }
        const result = await response.json();
        
        if (result.success && result.data) {
            displayStats(result.data);
        }
    } catch (error) {
        console.error('加载统计数据失败:', error);
    }
}

// 从统计表加载折线图数据（按动作类型展示总次数，与统计卡片保持一致）
async function loadStatsChart() {
    const canvas = document.getElementById('stats-chart');
    if (!canvas) return;

    try {
        const response = await fetch('/api/get_stats');
        if (response.status === 401) {
            // 未登录时不展示折线图即可
            return;
        }
        const result = await response.json();
        if (!(result.success && result.data && result.data.length > 0)) {
            // 没有数据时销毁旧图表
            if (statsChart) {
                statsChart.destroy();
                statsChart = null;
            }
            return;
        }

        const stats = result.data;
        const exerciseNames = {
            'pushup': '俯卧撑',
            'squat': '蹲起',
            'reverse_crunch': '反向卷腹',
            'barbell_curl_left': '左侧杠铃弯举',
            'barbell_curl_right': '右侧杠铃弯举',
            'barbell_sit_left': '左侧杠铃坐姿',
            'barbell_sit_right': '右侧杠铃坐姿'
        };

        const labels = stats.map(stat => exerciseNames[stat.exercise_type] || stat.exercise_type);
        const data = stats.map(stat => stat.total_count || 0);

        renderStatsChart(labels, data, '各动作总训练次数', '动作类型');
    } catch (error) {
        console.error('加载统计折线图数据失败:', error);
    }
}

function renderStatsChart(labels, data, seriesLabel = '训练次数', xLabel = '日期') {
    const ctx = document.getElementById('stats-chart');
    if (!ctx || typeof Chart === 'undefined') return;

    if (statsChart) {
        statsChart.destroy();
    }

    statsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: seriesLabel,
                data,
                borderColor: 'rgba(99, 102, 241, 1)',
                backgroundColor: 'rgba(99, 102, 241, 0.2)',
                tension: 0.25,
                fill: true,
                pointRadius: 3
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: true },
                tooltip: { enabled: true }
            },
            scales: {
                x: {
                    title: { display: true, text: xLabel }
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: '训练次数' }
                }
            }
        }
    });
}

// 显示统计数据
function displayStats(stats) {
    const statsContent = document.getElementById('stats-content');
    if (!statsContent) return;
    
    if (stats.length === 0) {
        statsContent.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">暂无统计数据</p>';
        return;
    }
    
    const exerciseNames = {
        'pushup': '俯卧撑',
        'squat': '蹲起',
        'reverse_crunch': '反向卷腹',
        'barbell_curl_left': '左侧杠铃弯举',
        'barbell_curl_right': '右侧杠铃弯举',
        'barbell_sit_left': '左侧杠铃坐姿',
        'barbell_sit_right': '右侧杠铃坐姿'
    };
    
    statsContent.innerHTML = stats.map(stat => `
        <div class="stat-item">
            <h3>${exerciseNames[stat.exercise_type] || stat.exercise_type}</h3>
            <p>总次数: <strong>${stat.total_count}</strong></p>
            <p>总时长: <strong>${formatDuration(stat.total_duration)}</strong></p>
            <p>最后训练: <strong>${formatDate(stat.last_exercise_date)}</strong></p>
        </div>
    `).join('');
}

// 加载历史记录
async function loadHistory() {
    try {
        const response = await fetch('/api/get_history?limit=20');
        if (response.status === 401) {
            // 未登录时不展示历史记录
            displayHistory([]);
            return;
        }
        const result = await response.json();
        
        if (result.success && result.data) {
            displayHistory(result.data);
        }
    } catch (error) {
        console.error('加载历史记录失败:', error);
    }
}

// 显示历史记录
function displayHistory(records) {
    const historyContent = document.getElementById('history-content');
    if (!historyContent) return;
    
    if (records.length === 0) {
        historyContent.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">暂无历史记录</p>';
        return;
    }
    
    const exerciseNames = {
        'pushup': '俯卧撑',
        'squat': '蹲起',
        'reverse_crunch': '反向卷腹',
        'barbell_curl_left': '左侧杠铃弯举',
        'barbell_curl_right': '右侧杠铃弯举',
        'barbell_sit_left': '左侧杠铃坐姿',
        'barbell_sit_right': '右侧杠铃坐姿'
    };
    
    historyContent.innerHTML = records.map(record => `
        <div class="history-item">
            <h3>${exerciseNames[record.exercise_type] || record.exercise_type}</h3>
            <p>次数: <strong>${record.count}</strong></p>
            <p>时长: <strong>${formatDuration(record.duration)}</strong></p>
            <p>时间: <strong>${formatDate(record.created_at)}</strong></p>
        </div>
    `).join('');
}

// 格式化时长
function formatDuration(seconds) {
    if (!seconds) return '0秒';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}小时${minutes}分钟${secs}秒`;
    } else if (minutes > 0) {
        return `${minutes}分钟${secs}秒`;
    } else {
        return `${secs}秒`;
    }
}

// 格式化日期
function formatDate(dateString) {
    if (!dateString) return '未知';
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN');
}

// 加载视频列表
async function loadVideos() {
    try {
        const response = await fetch('/api/get_videos?limit=12');
        const result = await response.json();
        
        if (result.success && result.data) {
            displayVideos(result.data);
        } else {
            const container = document.getElementById('videos-container');
            if (container) {
                container.innerHTML = `<p style="text-align: center; color: var(--danger-color);">视频加载失败：${escapeHtml(result.error || '暂无视频')}</p>`;
            }
        }
    } catch (error) {
        console.error('加载视频失败:', error);
        const container = document.getElementById('videos-container');
        if (container) {
            container.innerHTML = '<p style="text-align: center; color: var(--danger-color);">加载视频失败，请稍后重试</p>';
        }
    }
}

// 显示视频列表
function getVideoPlaceholder(title = '视频封面') {
    const safeTitle = escapeHtml(title || '视频封面');
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360"><defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#07111f"/><stop offset="1" stop-color="#1e3a4a"/></linearGradient></defs><rect fill="url(#g)" width="640" height="360"/><circle cx="320" cy="150" r="44" fill="#2dd4bf" opacity=".9"/><path d="M306 126v48l42-24z" fill="#07111f"/><text x="320" y="250" fill="#cbd5e1" font-size="24" font-family="Arial, sans-serif" text-anchor="middle">${safeTitle}</text></svg>`;
    return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[char]));
}

function displayVideos(videos) {
    const container = document.getElementById('videos-container');
    if (!container) return;
    
    if (videos.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">暂无视频</p>';
        return;
    }
    
    container.innerHTML = videos.map(video => {
        const videoId = Number(video.Video_ID);
        if (!Number.isFinite(videoId)) return '';
        return `
        <div class="video-card" onclick="playVideo(${videoId})">
            <img src="${escapeHtml(video.Video_Image_URL || getVideoPlaceholder(video.Title))}"
                 alt="${escapeHtml(video.Title)}"
                 class="video-thumbnail"
                 referrerpolicy="no-referrer"
                 onerror="this.onerror=null; this.src='${getVideoPlaceholder()}';">
            <div class="video-card-content">
                <h4 class="video-card-title">${escapeHtml(video.Title)}</h4>
                <div class="video-card-meta">
                    <span>⏱️ ${escapeHtml(video.Estimated_Time)}分钟</span>
                    <span>🔥 ${escapeHtml(video.Estimated_Calories)}卡</span>
                    <span>⭐ ${video.StarCount || 0}</span>
                </div>
            </div>
        </div>
    `;
    }).join('');
}

// 播放视频
async function playVideo(videoId) {
    try {
        const response = await fetch(`/api/get_video/${videoId}`);
        const result = await response.json();
        
        if (result.success && result.data) {
            const video = result.data;
            const modal = document.getElementById('video-modal');
            const player = document.getElementById('video-player');
            const source = document.getElementById('video-source');
            const fallback = document.getElementById('video-fallback');
            const openLink = document.getElementById('video-open-link');
            
            // 设置视频信息
            document.getElementById('video-modal-title').textContent = video.Title;
            document.getElementById('video-content').textContent = video.Content || '暂无介绍';
            document.getElementById('video-suitable').textContent = video.Suitable_People || '所有人';
            document.getElementById('video-time').textContent = `⏱️ ${video.Estimated_Time}分钟`;
            document.getElementById('video-calories').textContent = `🔥 ${video.Estimated_Calories}卡路里`;
            document.getElementById('video-coach').textContent = video.Coach_Name ? `👨‍🏫 ${video.Coach_Name}` : '';
            
            // 设置视频源
            const videoUrl = video.Video_URL || '';
            source.src = videoUrl;
            if (openLink) openLink.href = videoUrl || '#';
            if (fallback) fallback.style.display = videoUrl ? 'none' : 'block';
            if (player) {
                player.onerror = function() {
                    if (fallback) fallback.style.display = 'block';
                };
                player.oncanplay = function() {
                    if (fallback) fallback.style.display = 'none';
                };
                player.load();
            }
            
            // 显示模态框
            modal.style.display = 'block';
        } else {
            alert('视频加载失败');
        }
    } catch (error) {
        console.error('播放视频失败:', error);
        alert('播放视频失败，请稍后重试');
    }
}

// 关闭视频模态框
function closeVideoModal() {
    const modal = document.getElementById('video-modal');
    const player = document.getElementById('video-player');
    const fallback = document.getElementById('video-fallback');
    if (modal) modal.style.display = 'none';
    if (fallback) fallback.style.display = 'none';
    if (player) {
        player.pause();
        player.currentTime = 0;
    }
}

// 点击模态框外部关闭
window.onclick = function(event) {
    const modal = document.getElementById('video-modal');
    if (event.target === modal) {
        closeVideoModal();
    }
}

