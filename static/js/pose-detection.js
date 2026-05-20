// 姿态检测模块
let poseDetector = null;
let trainingCamera = null;
let isTrainingActive = false;
let currentExerciseType = null;
let exerciseData = {
    count: 0,
    angles: [],
    startTime: null,
    fps: 0
};

const POSE_MEDIAPIPE_THEME = {
    connectorColor: '#0f2f4d',
    connectorShadow: 'rgba(15, 47, 77, 0.28)',
    landmarkColor: '#e6b451',
    landmarkOutline: '#ffffff',
    promptBg: 'rgba(255, 255, 255, 0.88)',
    promptText: '#0f2f4d'
};

// 将变量暴露到全局，以便main.js访问
window.currentExerciseType = currentExerciseType;
window.exerciseData = exerciseData;

function initPoseDetection() {
    // 已初始化则直接复用，避免重复加载模型
    if (poseDetector) return;

    if (!window.MediaPipe || !window.MediaPipe.Pose) {
        console.warn('MediaPipe Pose未加载，等待中...');
        // 减少重试频率，避免过多日志
        setTimeout(() => {
            if (window.MediaPipe && window.MediaPipe.Pose) {
                initPoseDetection();
            }
        }, 500);
        return;
    }
    
    console.log('初始化姿态检测...');
    const { Pose } = window.MediaPipe;
    
    poseDetector = new Pose({
        locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
        }
    });
    
    poseDetector.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        smoothSegmentation: false,
        minDetectionConfidence: 0.7,
        minTrackingConfidence: 0.7
    });
    
    poseDetector.onResults(onPoseResults);
}

function onPoseResults(results) {
    const video = document.getElementById('training_video');
    const canvas = document.getElementById('training_canvas');
    const ctx = canvas.getContext('2d');
    
    // 如果训练已停止或尚未选择训练类型，则忽略后续结果，避免误触发语音和计数
    if (!isTrainingActive || !currentExerciseType) {
        return;
    }

    if (!video || !canvas) return;
    
    // 确保canvas尺寸与video匹配
    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
    }
    
    ctx.save();
    ctx.scale(-1, 1);
    ctx.translate(-canvas.width, 0);
    ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);
    
    if (results.poseLandmarks && results.poseLandmarks.length >= 33) {
        const { drawConnectors, drawLandmarks, POSE_CONNECTIONS } = window.MediaPipe || {};
        
        if (drawConnectors && drawLandmarks && POSE_CONNECTIONS) {
            // 绘制姿态骨架（与画面一起镜像）
            ctx.shadowColor = POSE_MEDIAPIPE_THEME.connectorShadow;
            ctx.shadowBlur = 8;
            drawConnectors(ctx, results.poseLandmarks, POSE_CONNECTIONS, {
                color: POSE_MEDIAPIPE_THEME.connectorColor,
                lineWidth: 3
            });
            ctx.shadowBlur = 0;
            drawLandmarks(ctx, results.poseLandmarks, {
                color: POSE_MEDIAPIPE_THEME.landmarkOutline,
                lineWidth: 1,
                radius: 5
            });
            drawLandmarks(ctx, results.poseLandmarks, {
                color: POSE_MEDIAPIPE_THEME.landmarkColor,
                lineWidth: 1,
                radius: 3
            });
        }
        
        // 根据不同的运动类型进行检测
        processExercise(results.poseLandmarks);
    } else {
        // 如果没有检测到姿态，显示提示（同样在镜像坐标系中绘制）
        const prompt = '请确保全身在摄像头视野内';
        ctx.font = '700 24px Arial';
        ctx.textAlign = 'center';
        const textWidth = ctx.measureText(prompt).width;
        const boxX = canvas.width / 2 - textWidth / 2 - 22;
        const boxY = canvas.height / 2 - 30;
        const boxWidth = textWidth + 44;
        const boxHeight = 56;
        ctx.fillStyle = POSE_MEDIAPIPE_THEME.promptBg;
        ctx.strokeStyle = 'rgba(230, 180, 81, 0.68)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        drawRoundedRect(ctx, boxX, boxY, boxWidth, boxHeight, 14);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = POSE_MEDIAPIPE_THEME.promptText;
        ctx.fillText(prompt, canvas.width / 2, canvas.height / 2 + 9);
    }

    ctx.restore();
    
    // 更新FPS
    updateFPS();
}

function drawRoundedRect(ctx, x, y, width, height, radius) {
    if (typeof ctx.roundRect === 'function') {
        ctx.roundRect(x, y, width, height, radius);
        return;
    }

    const r = Math.min(radius, width / 2, height / 2);
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + width - r, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + r);
    ctx.lineTo(x + width, y + height - r);
    ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
    ctx.lineTo(x + r, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
}

function processExercise(landmarks) {
    if (!currentExerciseType) {
        return;
    }
    
    // MediaPipe Pose有33个关键点，确保有足够的数据
    if (!landmarks || landmarks.length < 33) {
        // 调试信息：如果landmarks不足，可能是检测失败
        if (landmarks && landmarks.length > 0) {
            console.warn(`检测到${landmarks.length}个关键点，需要33个`);
        }
        return;
    }
    
    let angle = 0;
    let shouldCount = false;
    
    // 根据不同的训练类型选择不同的关键点
    switch (currentExerciseType) {
        case 'pushup':
            // 俯卧撑：使用右肩(11)-右髋(23)-右踝(27)的角度
            angle = calculateAngle(landmarks, 11, 23, 27);
            shouldCount = detectPushup(angle);
            break;
            
        case 'squat':
            // 蹲起：使用左髋(24)-左膝(26)-左踝(28)的角度
            angle = calculateAngle(landmarks, 24, 26, 28);
            shouldCount = detectSquat(angle);
            break;
            
        case 'barbell_curl_left':
            // 左侧（屏幕左侧）杠铃弯举：由于画面镜像，使用右肩(11)-右肘(13)-右腕(15)
            angle = calculateAngle(landmarks, 11, 13, 15);
            shouldCount = detectBarbellCurl(angle);
            break;
            
        case 'barbell_curl_right':
            // 右侧（屏幕右侧）杠铃弯举：使用左肩(12)-左肘(14)-左腕(16)
            angle = calculateAngle(landmarks, 12, 14, 16);
            shouldCount = detectBarbellCurl(angle);
            break;
            
        case 'barbell_sit_left':
            // 左侧（屏幕左侧）杠铃坐姿：使用右肩(11)-右肘(13)-右腕(15)
            angle = calculateAngle(landmarks, 11, 13, 15);
            shouldCount = detectBarbellSit(angle);
            break;
            
        case 'barbell_sit_right':
            // 右侧（屏幕右侧）杠铃坐姿：使用左肩(12)-左肘(14)-左腕(16)
            angle = calculateAngle(landmarks, 12, 14, 16);
            shouldCount = detectBarbellSit(angle);
            break;
            
        case 'reverse_crunch':
            // 反向卷腹：使用右肩(11)-右髋(23)-右膝(25)
            angle = calculateAngle(landmarks, 11, 23, 25);
            shouldCount = detectReverseCrunch(angle);
            break;
            
        default:
            return; // 未知的训练类型
    }
    
    // 基于角度进行动作规范性语音提示
    provideExerciseFeedback(currentExerciseType, angle);
    
    // 更新角度显示（只在角度有效时更新）
    const angleElement = document.getElementById('exercise-angle');
    if (angleElement && angle > 0) {
        angleElement.textContent = Math.round(angle) + '°';
    } else if (angleElement && angle === 0) {
        angleElement.textContent = '--°';
    }
    
    // 记录角度数据（限制数组大小，避免内存问题）
    if (exerciseData.angles.length > 1000) {
        exerciseData.angles = exerciseData.angles.slice(-500); // 只保留最近500条
    }
    exerciseData.angles.push({
        angle: angle,
        timestamp: Date.now()
    });
    window.exerciseData = exerciseData; // 更新全局变量
    
    // 如果检测到完整动作，增加计数
    if (shouldCount) {
        exerciseData.count++;
        window.exerciseData = exerciseData; // 更新全局变量
        const countElement = document.getElementById('exercise-count');
        if (countElement) {
            countElement.textContent = exerciseData.count;
        }

        // 语音提示：简单鼓励与阶段汇报
        if (typeof window.speak === 'function') {
            if (exerciseData.count === 1) {
                window.speak('很好，继续保持');
            } else if (exerciseData.count > 0 && exerciseData.count % 10 === 0) {
                window.speak(`已完成 ${exerciseData.count} 次`);
            }
        }
    }
}

function calculateAngle(landmarks, p1, p2, p3) {
    // MediaPipe Pose landmarks是数组，每个元素有x, y, z, visibility属性
    if (!landmarks || landmarks.length <= Math.max(p1, p2, p3)) {
        return 0;
    }
    
    const point1 = landmarks[p1];
    const point2 = landmarks[p2];
    const point3 = landmarks[p3];
    
    // 检查关键点是否存在且可见
    if (!point1 || !point2 || !point3) return 0;
    if (point1.visibility < 0.5 || point2.visibility < 0.5 || point3.visibility < 0.5) {
        return 0; // 关键点不可见，返回0
    }
    
    // 计算两个向量之间的角度
    // 向量1: point2 -> point1
    // 向量2: point2 -> point3
    const radians = Math.atan2(point3.y - point2.y, point3.x - point2.x) -
                    Math.atan2(point1.y - point2.y, point1.x - point2.x);
    let angle = Math.abs(radians * 180.0 / Math.PI);
    
    // 确保角度在0-180度之间
    if (angle > 180.0) {
        angle = 360 - angle;
    }
    
    return angle;
}

// 移除calculateLegAngle函数，直接在processExercise中使用calculateAngle

// 运动检测逻辑
let pushupState = { direction: 0, lastAngle: 0 };
const PUSHUP_MIN = 40;
const PUSHUP_MAX = 130;

function detectPushup(angle) {
    if (angle > PUSHUP_MAX - 20 && pushupState.direction === 0) {
        pushupState.direction = 1;
    } else if (angle < PUSHUP_MIN + 20 && pushupState.direction === 1) {
        pushupState.direction = 0;
        pushupState.lastAngle = angle;
        return true;
    }
    return false;
}

let squatState = { direction: 0, lastAngle: 0 };
const SQUAT_MIN = 50;
const SQUAT_MAX = 120;

function detectSquat(angle) {
    if (angle > SQUAT_MAX && squatState.direction === 0) {
        squatState.direction = 1;
    } else if (angle < SQUAT_MIN && squatState.direction === 1) {
        squatState.direction = 0;
        squatState.lastAngle = angle;
        return true;
    }
    return false;
}

let curlState = { direction: 0, lastAngle: 0 };
const CURL_MIN = 60;
const CURL_MAX = 140;
const CURL_OPTIMAL_MIN = 80;
const CURL_OPTIMAL_MAX = 120;

function detectBarbellCurl(angle) {
    // 根据原始代码，使用0.5计数系统
    // 当角度从大于最优范围上限*0.95变为小于最优范围下限*1.05时，完成一个动作
    if (angle > CURL_OPTIMAL_MAX * 0.95 && curlState.direction === 0) {
        curlState.direction = 1;
        curlState.lastAngle = angle;
        return false; // 开始下降，不计数
    } else if (angle < CURL_OPTIMAL_MIN * 1.05 && curlState.direction === 1) {
        curlState.direction = 0;
        curlState.lastAngle = angle;
        return true; // 完成一个完整动作
    }
    return false;
}

let sitState = { direction: 0, lastAngle: 0 };
const SIT_MIN = 60;
const SIT_MAX = 140;
const SIT_OPTIMAL_MIN = 80;
const SIT_OPTIMAL_MAX = 120;

function detectBarbellSit(angle) {
    // 杠铃坐姿使用与弯举类似的逻辑
    if (angle > SIT_OPTIMAL_MAX * 0.95 && sitState.direction === 0) {
        sitState.direction = 1;
        sitState.lastAngle = angle;
        return false;
    } else if (angle < SIT_OPTIMAL_MIN * 1.05 && sitState.direction === 1) {
        sitState.direction = 0;
        sitState.lastAngle = angle;
        return true;
    }
    return false;
}

let crunchState = { direction: 0, lastAngle: 0 };
const CRUNCH_MIN = 40;
const CRUNCH_MAX = 90;
const CRUNCH_OPTIMAL_MIN = 50;
const CRUNCH_OPTIMAL_MAX = 80;

function detectReverseCrunch(angle) {
    // 反向卷腹：使用0.5计数系统
    // 当角度从大于最优范围上限变为小于最优范围下限时，完成一个动作
    if (angle > CRUNCH_OPTIMAL_MAX && crunchState.direction === 0) {
        crunchState.direction = 1;
        crunchState.lastAngle = angle;
        return false;
    } else if (angle < CRUNCH_OPTIMAL_MIN && crunchState.direction === 1) {
        crunchState.direction = 0;
        crunchState.lastAngle = angle;
        return true;
    }
    return false;
}

// 动作规范性语音反馈状态
const feedbackState = {
    pushup: { lastFeedback: '', lastSpeakTime: 0, currentBand: null, bandStartTime: 0 },
    squat: { lastFeedback: '', lastSpeakTime: 0, currentBand: null, bandStartTime: 0 },
    barbell_curl_left: { lastFeedback: '', lastSpeakTime: 0, currentBand: null, bandStartTime: 0 },
    barbell_curl_right: { lastFeedback: '', lastSpeakTime: 0, currentBand: null, bandStartTime: 0 },
    barbell_sit_left: { lastFeedback: '', lastSpeakTime: 0, currentBand: null, bandStartTime: 0 },
    barbell_sit_right: { lastFeedback: '', lastSpeakTime: 0, currentBand: null, bandStartTime: 0 },
    reverse_crunch: { lastFeedback: '', lastSpeakTime: 0, currentBand: null, bandStartTime: 0 }
};

function provideExerciseFeedback(exerciseType, angle) {
    // 未在训练中或角度无效时不提示
    if (!isTrainingActive || !currentExerciseType) return;
    if (!angle || angle <= 0) return;
    if (typeof window.speak !== 'function') return;
    const state = feedbackState[exerciseType];
    if (!state) return;

    const now = Date.now();
    // 任意两次语音提示之间至少间隔 8 秒，避免过于频繁
    const MIN_INTERVAL_MS = 8000;
    if (now - state.lastSpeakTime < MIN_INTERVAL_MS) {
        return;
    }

    // 不同动作的角度范围设置（参考原Python实现，并略作调整）
    let min = 0, max = 180, optimalMin = 0, optimalMax = 180;
    switch (exerciseType) {
        case 'pushup':
            min = PUSHUP_MIN;      // 40
            max = PUSHUP_MAX;      // 130
            optimalMin = 60;       // 建议发力区间
            optimalMax = 110;
            break;
        case 'squat':
            min = SQUAT_MIN;       // 50
            max = SQUAT_MAX;       // 120
            optimalMin = 60;       // 稍微下蹲即可
            optimalMax = 100;
            break;
        case 'barbell_curl_left':
        case 'barbell_curl_right':
            min = CURL_MIN;
            max = CURL_MAX;
            optimalMin = CURL_OPTIMAL_MIN;
            optimalMax = CURL_OPTIMAL_MAX;
            break;
        case 'barbell_sit_left':
        case 'barbell_sit_right':
            min = SIT_MIN;
            max = SIT_MAX;
            optimalMin = SIT_OPTIMAL_MIN;
            optimalMax = SIT_OPTIMAL_MAX;
            break;
        case 'reverse_crunch':
            min = CRUNCH_MIN;          // 40
            max = CRUNCH_MAX;          // 90
            optimalMin = CRUNCH_OPTIMAL_MIN;   // 50
            optimalMax = CRUNCH_OPTIMAL_MAX;   // 80
            break;
        default:
            return;
    }

    // 根据当前角度划分区间：danger / optimal / middle
    let band = null;
    if (angle < min || angle > max) {
        band = 'danger';
    } else if (angle >= optimalMin && angle <= optimalMax) {
        band = 'optimal';
    } else {
        band = 'middle';
    }

    // 如果区间发生变化，重置计时
    if (state.currentBand !== band) {
        state.currentBand = band;
        state.bandStartTime = now;
        return;
    }

    const holdMs = now - state.bandStartTime;
    // 各区间需要保持的最少时间（毫秒）
    const DANGER_HOLD_MS = 800;   // 危险区域至少 0.8 秒
    const OPTIMAL_HOLD_MS = 1500; // 最佳区域至少 1.5 秒
    const MIDDLE_HOLD_MS = 1200;  // 注意区域至少 1.2 秒

    let feedback = '';

    if (band === 'danger' && holdMs >= DANGER_HOLD_MS) {
        feedback = '危险范围，注意调整';
    } else if (band === 'optimal' && holdMs >= OPTIMAL_HOLD_MS) {
        feedback = '动作幅度很好';
    } else if (band === 'middle' && holdMs >= MIDDLE_HOLD_MS) {
        feedback = '注意动作幅度';
    } else {
        return; // 停留时间不够，不提示
    }

    // 避免同一个提示在短时间内重复播放
    if (feedback === state.lastFeedback && now - state.lastSpeakTime < MIN_INTERVAL_MS * 2) {
        return;
    }

    window.speak(feedback);
    state.lastFeedback = feedback;
    state.lastSpeakTime = now;
}

let lastFpsTime = Date.now();
let fpsFrameCount = 0;

function updateFPS() {
    fpsFrameCount++;
    const now = Date.now();
    if (now - lastFpsTime >= 1000) {
        exerciseData.fps = fpsFrameCount;
        document.getElementById('exercise-fps').textContent = fpsFrameCount;
        fpsFrameCount = 0;
        lastFpsTime = now;
    }
}

function startTraining(exerciseType) {
    if (isTrainingActive) return;

    if (!window.MediaPipe || !window.MediaPipe.Camera || !window.MediaPipe.Pose) {
        console.warn('MediaPipe训练依赖尚未加载，等待中...');
        setTimeout(() => {
            if (!isTrainingActive) {
                startTraining(exerciseType);
            }
        }, 500);
        return;
    }

    if (!poseDetector) {
        initPoseDetection();
    }

    if (!poseDetector) {
        console.warn('MediaPipe Pose尚未初始化，等待中...');
        setTimeout(() => {
            if (!isTrainingActive) {
                startTraining(exerciseType);
            }
        }, 500);
        return;
    }
    
    // 语音提示：开始某种训练
    if (typeof window.speak === 'function') {
        const exerciseNames = {
            'pushup': '开始俯卧撑训练',
            'squat': '开始蹲起训练',
            'reverse_crunch': '开始反向卷腹训练',
            'barbell_curl_left': '开始左侧杠铃弯举训练',
            'barbell_curl_right': '开始右侧杠铃弯举训练',
            'barbell_sit_left': '开始左侧杠铃坐姿训练',
            'barbell_sit_right': '开始右侧杠铃坐姿训练'
        };
        window.speak(exerciseNames[exerciseType] || '开始训练');
    }
    
    isTrainingActive = true;
    currentExerciseType = exerciseType;
    exerciseData = {
        count: 0,
        angles: [],
        startTime: Date.now(),
        fps: 0
    };
    
    // 更新全局变量
    window.currentExerciseType = currentExerciseType;
    window.exerciseData = exerciseData;
    
    // 重置所有状态
    pushupState = { direction: 0, lastAngle: 0 };
    squatState = { direction: 0, lastAngle: 0 };
    curlState = { direction: 0, lastAngle: 0 };
    sitState = { direction: 0, lastAngle: 0 };
    crunchState = { direction: 0, lastAngle: 0 };
    
    const video = document.getElementById('training_video');

    // 启动训练前停止手部检测，避免占用同一个摄像头
    if (typeof stopHandDetection === 'function') {
        stopHandDetection();
    }

    // 启动训练时禁用手势虚拟鼠标，避免冲突
    window.handMouseEnabled = false;
    
    const { Camera } = window.MediaPipe;
    
    trainingCamera = new Camera(video, {
        onFrame: async () => {
            if (poseDetector) {
                await poseDetector.send({image: video});
            }
        },
        width: 1280,
        height: 720
    });
    
    trainingCamera.start().catch(error => {
        console.error('训练摄像头启动失败:', error);
        isTrainingActive = false;
        currentExerciseType = null;
        window.currentExerciseType = null;
        if (typeof showToast === 'function') {
            showToast('训练摄像头启动失败，请确认摄像头权限或刷新页面重试', 'error');
        }
    });
}

function stopTraining() {
    if (trainingCamera) {
        trainingCamera.stop();
        trainingCamera = null;
    }
    isTrainingActive = false;
    currentExerciseType = null;

    // 立即停止所有尚未播完的语音提示，避免训练结束后仍继续播报
    try {
        if (window.speechSynthesis && typeof window.speechSynthesis.cancel === 'function') {
            window.speechSynthesis.cancel();
        }
    } catch (e) {
        console.warn('停止语音失败:', e);
    }

    // 重置训练数据并同步到全局，避免下次训练复用旧状态
    exerciseData = {
        count: 0,
        angles: [],
        startTime: null,
        fps: 0
    };
    window.currentExerciseType = null;
    window.exerciseData = exerciseData;

    // 重置反馈状态，避免上一次训练的计时影响下一次
    Object.keys(feedbackState).forEach(key => {
        feedbackState[key].lastFeedback = '';
        feedbackState[key].lastSpeakTime = 0;
        feedbackState[key].currentBand = null;
        feedbackState[key].bandStartTime = 0;
    });

    // 训练结束后恢复手部检测和手势鼠标（如果处于鼠标模式）
    if (typeof startHandDetection === 'function') {
        startHandDetection();
    }
    if (window.handMouseMode === 'mouse') {
        window.handMouseEnabled = true;
    }
}

