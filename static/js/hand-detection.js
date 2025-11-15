// 手部检测模块
let handDetector = null;
let camera = null;
let isHandDetectionActive = false;

function initHandDetection() {
    if (!window.MediaPipe || !window.MediaPipe.Hands) {
        console.warn('MediaPipe Hands未加载，等待中...');
        // 减少重试频率，避免过多日志
        setTimeout(() => {
            if (window.MediaPipe && window.MediaPipe.Hands) {
                initHandDetection();
            }
        }, 500);
        return;
    }
    
    console.log('初始化手部检测...');
    const { Hands } = window.MediaPipe;
    
    handDetector = new Hands({
        locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
        }
    });
    
    handDetector.setOptions({
        maxNumHands: 1,
        modelComplexity: 1,
        minDetectionConfidence: 0.8,
        minTrackingConfidence: 0.8
    });
    
    handDetector.onResults(onHandResults);
}

function onHandResults(results) {
    const video = document.getElementById('input_video');
    const canvas = document.getElementById('output_canvas');
    const ctx = canvas.getContext('2d');
    
    if (!video || !canvas) return;
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    ctx.save();
    ctx.scale(-1, 1);
    ctx.translate(-canvas.width, 0);
    ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);

    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
        const { drawConnectors, drawLandmarks, HAND_CONNECTIONS } = window.MediaPipe || {};
        
        if (drawConnectors && drawLandmarks && HAND_CONNECTIONS) {
            for (const landmarks of results.multiHandLandmarks) {
                drawConnectors(ctx, landmarks, HAND_CONNECTIONS, {
                    color: '#00FF00',
                    lineWidth: 2
                });
                drawLandmarks(ctx, landmarks, {
                    color: '#FF0000',
                    lineWidth: 1,
                    radius: 3
                });
            }
        }
        
        const landmarks = results.multiHandLandmarks[0];

        // 手势导航：仅在“手势模式”且显式开启识别时生效
        const fingerCount = countFingers(landmarks);
        if ((!window.handMouseMode || window.handMouseMode === 'gesture') && window.gestureNavEnabled) {
            handleGesture(fingerCount);
        }

        // 在鼠标模式下，使用三指/四指控制页面滚动
        if (window.handMouseEnabled && window.handMouseMode === 'mouse') {
            handleScrollGesture(fingerCount);
        }

        // 手势虚拟鼠标逻辑：仅在启用时生效
        if (window.handMouseEnabled && typeof window.updateHandMouseCursor === 'function') {
            // 使用食指指尖控制光标位置，食指+中指捏合触发点击
            const indexTip = landmarks[8];
            const middleTip = landmarks[12];

            // 镜像后的横坐标（画面是左右翻转的，这里也做反向映射）
            const normX = 1 - indexTip.x;
            const normY = indexTip.y;
            const screenX = normX * window.innerWidth;
            const screenY = normY * window.innerHeight;

            let click = false;

            // 只有在 1 或 2 指的情况下才允许捏合触发点击，避免三指/五指滚动时误触
            if (fingerCount <= 2) {
                const dx = (indexTip.x - middleTip.x);
                const dy = (indexTip.y - middleTip.y);
                const dist = Math.sqrt(dx * dx + dy * dy);

                // 简单阈值判断捏合点击（阈值可视情况调整）
                const pinchThreshold = 0.05;
                if (!window._handMousePrevPinch) {
                    window._handMousePrevPinch = false;
                }
                if (dist < pinchThreshold && !window._handMousePrevPinch) {
                    click = true;
                    window._handMousePrevPinch = true;
                } else if (dist >= pinchThreshold) {
                    window._handMousePrevPinch = false;
                }
            } else {
                // 滚动等多指手势时，重置点击状态，防止残留
                window._handMousePrevPinch = false;
            }

            window.updateHandMouseCursor(screenX, screenY, click);
        }
    }

    ctx.restore();
}

function countFingers(landmarks) {
    const fingerTips = [4, 8, 12, 16, 20];
    const fingerPips = [3, 6, 10, 14, 18];
    let count = 0;
    
    // 检测拇指（特殊处理）
    if (landmarks[4].x > landmarks[3].x) {
        count++;
    }
    
    // 检测其他四指
    for (let i = 1; i < 5; i++) {
        if (landmarks[fingerTips[i]].y < landmarks[fingerPips[i]].y) {
            count++;
        }
    }
    
    return count;
}

let lastGesture = null;
let gestureStartTime = null;
const GESTURE_HOLD_TIME = 3000; // 3秒

function handleGesture(fingerCount) {
    const now = Date.now();
    
    if (fingerCount !== lastGesture) {
        lastGesture = fingerCount;
        gestureStartTime = now;
        return;
    }
    
    if (gestureStartTime && (now - gestureStartTime) >= GESTURE_HOLD_TIME) {
        // 手势保持3秒，触发动作
        onGestureConfirmed(fingerCount);
        lastGesture = null;
        gestureStartTime = null;
    }
    
    // 更新提示
    updateGestureHint(fingerCount);
}

function updateGestureHint(fingerCount) {
    const hint = document.getElementById('gesture-hint');
    if (!hint) return;
    
    if (fingerCount > 0) {
        const holdTime = gestureStartTime ? Math.floor((Date.now() - gestureStartTime) / 1000) : 0;
        hint.innerHTML = `
            <p>检测到: ${fingerCount} 根手指（保持 ${holdTime}/${GESTURE_HOLD_TIME/1000} 秒确认）</p>
            <p>1️⃣ 俯卧撑计数</p>
            <p>2️⃣ 蹲起</p>
            <p>3️⃣ 反向卷腹</p>
            <p>4️⃣ 左侧杠铃弯举</p>
            <p>5️⃣ 右侧杠铃弯举</p>
        `;
    } else {
        hint.innerHTML = `
            <p>请伸出手指选择具体动作：</p>
            <p>1️⃣ 俯卧撑计数</p>
            <p>2️⃣ 蹲起</p>
            <p>3️⃣ 反向卷腹</p>
            <p>4️⃣ 左侧杠铃弯举</p>
            <p>5️⃣ 右侧杠铃弯举</p>
        `;
    }
}

function onGestureConfirmed(fingerCount) {
    let exerciseType = null;
    let message = '';

    switch (fingerCount) {
        case 1:
            exerciseType = 'pushup';
            message = '已选择俯卧撑计数';
            break;
        case 2:
            exerciseType = 'squat';
            message = '已选择蹲起';
            break;
        case 3:
            exerciseType = 'reverse_crunch';
            message = '已选择反向卷腹';
            break;
        case 4:
            exerciseType = 'barbell_curl_left';
            message = '已选择左侧杠铃弯举';
            break;
        case 5:
            exerciseType = 'barbell_curl_right';
            message = '已选择右侧杠铃弯举';
            break;
        default:
            return;
    }

    if (typeof window.speak === 'function' && message) {
        window.speak(message);
    }

    // 直接跳转到训练页面并配置对应动作
    if (typeof showPage === 'function') {
        showPage('exercise');
    }
    if (typeof startExerciseType === 'function' && exerciseType) {
        startExerciseType(exerciseType);
    }
}

// 三指/五指滚动页面：三指向上=向下滚动，五指向上=向上滚动
let lastScrollGesture = 0;

function handleScrollGesture(fingerCount) {
    if (fingerCount !== 3 && fingerCount !== 5) {
        lastScrollGesture = 0;
        return;
    }

    // 避免同一手势在保持期间重复触发，只在手指数从其他状态切换到3或5时触发一次
    if (fingerCount === lastScrollGesture) return;
    lastScrollGesture = fingerCount;

    const delta = 200; // 每次滚动的像素，可以根据需要调整

    // 若视频模态框已打开，则优先滚动模态框内容；否则滚动整个页面
    const modal = document.getElementById('video-modal');
    const modalVisible = modal && modal.style.display !== 'none';

    if (fingerCount === 3) {
        // 三指：向下滚动
        if (modalVisible) {
            modal.scrollTop += delta;
        } else {
            window.scrollBy({ top: delta, left: 0, behavior: 'smooth' });
        }
    } else if (fingerCount === 5) {
        // 五指：向上滚动
        if (modalVisible) {
            modal.scrollTop -= delta;
        } else {
            window.scrollBy({ top: -delta, left: 0, behavior: 'smooth' });
        }
    }
}

function startHandDetection() {
    if (isHandDetectionActive) return;
    
    isHandDetectionActive = true;
    const video = document.getElementById('input_video');
    
    if (!handDetector) {
        initHandDetection();
    }
    
    if (!window.MediaPipe || !window.MediaPipe.Camera) {
        console.warn('MediaPipe Camera未加载，等待中...');
        setTimeout(() => {
            if (window.MediaPipe && window.MediaPipe.Camera) {
                startHandDetection();
            }
        }, 500);
        return;
    }
    
    const { Camera } = window.MediaPipe;
    
    camera = new Camera(video, {
        onFrame: async () => {
            if (handDetector) {
                await handDetector.send({image: video});
            }
        },
        width: 1280,
        height: 720
    });
    
    camera.start();
}

function stopHandDetection() {
    if (camera) {
        camera.stop();
        camera = null;
    }
    isHandDetectionActive = false;
}

