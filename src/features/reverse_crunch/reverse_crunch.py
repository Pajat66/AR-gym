import cv2
import numpy as np
import time
from modules.pose_module6 import poseDetector  # 修改为模块化路径
from PIL import ImageFont, ImageDraw, Image
from modules.text_to_speech import speak

# 配置参数
ROTATE_VIDEO = False   # True-手机竖屏模式 / False-电脑横屏模式
MIRROR_IMAGE = True
FONT_PATH = '../assets/fonts/msyh.ttc'  # 字体路径（根据项目结构调整）

# 运动参数
MIN_ANGLE = 50   # 动作完成的最小角度
MAX_ANGLE = 120  # 动作完成的最大角度
OPTIMAL_RANGE = (50, 90)  # 动作的最佳幅度范围

def dynamic_layout(img):
    """动态界面布局系统"""
    h, w = img.shape[:2]
    return {
        "count_box": (20, 20, 320, 120) if not ROTATE_VIDEO else (20, h-160, 320, h-20),
        "angle_pos": (w-300, 100) if not ROTATE_VIDEO else (w//2-80, h//2),
        "fps_pos": (w-200, 50) if not ROTATE_VIDEO else (30, 50),
        "bar_pos": (w-100, 300, w-50, 600) if not ROTATE_VIDEO else (w-100, 300, w-50, h-100)
    }

def map_color(angle, last_feedback, danger_timer, optimal_timer):
    """智能颜色映射"""
    if angle < MIN_ANGLE or angle > MAX_ANGLE:
        feedback = "危险范围"
        danger_timer += 2
        optimal_timer = 0  # 重置最佳幅度计时器
    elif OPTIMAL_RANGE[0] <= angle <= OPTIMAL_RANGE[1]:
        feedback = "最佳幅度"
        optimal_timer += 2
        danger_timer = 0  # 重置危险范围计时器
    else:
        feedback = "注意幅度"
        danger_timer = 0
        optimal_timer = 0

    if feedback != last_feedback:
        if feedback == "危险范围" and danger_timer >= 4:
            speak(feedback)
            last_feedback = feedback
        elif feedback == "最佳幅度" and optimal_timer >= 10:
            speak(feedback)
            last_feedback = feedback

    if feedback == "危险范围":
        return (0, 0, 255), feedback, last_feedback, danger_timer, optimal_timer
    elif feedback == "最佳幅度":
        return (0, 255, 0), feedback, last_feedback, danger_timer, optimal_timer
    else:
        return (0, 255, 255), feedback, last_feedback, danger_timer, optimal_timer

def putChineseText(img, text, pos, size, color):
    """Pillow中文渲染函数"""
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    try:
        font = ImageFont.truetype(FONT_PATH, size)
    except:
        print(f"字体加载失败，请检查路径: {FONT_PATH}")
        return img

    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_width = right - left
    text_height = bottom - top
    x = pos[0] if pos[0] > 0 else (img.shape[1] - text_width) // 2
    y = pos[1] if pos[1] > 0 else (img.shape[0] - text_height) // 2

    draw.text((x, y), text, font=font, fill=color)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def calculate_leg_angle(lmList, detector, img):
    """计算肩部与胯部的连线和胯部与脚踝的连线间的夹角"""
    try:
        angle = detector.findAngle(img, 11, 23, 25, draw=False)
        return angle
    except:
        return 0

def run_reverse_crunch():
    """运行反向卷腹功能"""
    speak("Starting reverse crunch")
    cap = cv2.VideoCapture(0)
    if ROTATE_VIDEO:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1280)
    else:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    detector = poseDetector()
    count = 0
    dir = 0
    pTime = 0
    last_feedback = ""
    danger_timer = 0
    optimal_timer = 0

    while True:
        success, img = cap.read()
        if not success:
            break

        # 图像预处理
        if MIRROR_IMAGE:
            img = cv2.flip(img, 1)
        if ROTATE_VIDEO:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

        # 姿态检测
        img = detector.findPose(img, draw=False)
        lmList = detector.findPosition(img, draw=False)

        # 获取动态布局参数
        layout = dynamic_layout(img)
        h, w = img.shape[:2]

        # 动作检测逻辑
        angle = calculate_leg_angle(lmList, detector, img)
        if angle > 0:
            # 智能计数系统
            if angle > OPTIMAL_RANGE[1] and dir == 0:
                count += 0.5
                dir = 1
            elif angle < OPTIMAL_RANGE[0] and dir == 1:
                count += 0.5
                dir = 0

            # 可视化反馈
            color, feedback, last_feedback, danger_timer, optimal_timer = map_color(
                angle, last_feedback, danger_timer, optimal_timer
            )
            img = putChineseText(img, f"{int(angle)}°", layout["angle_pos"], 40, color[::-1])
            img = putChineseText(img, feedback, (layout["angle_pos"][0], layout["angle_pos"][1]+70), 30, color[::-1])

        # 界面绘制
        # 1. 计数面板
        x1, y1, x2, y2 = layout["count_box"]
        cv2.rectangle(img, (x1, y1), (x2, y2), (245, 117, 16), -1)
        img = putChineseText(img, f"计数: {int(count)}", (x1+50, y1+40), 30, (255, 255, 255))

        # 2. FPS显示
        cTime = time.time()
        fps = 1 / (cTime - pTime)
        pTime = cTime
        img = putChineseText(img, f"帧率: {int(fps)}", layout["fps_pos"], 24, (0, 255, 0))

        # 3. 安全指示条
        bx1, by1, bx2, by2 = layout["bar_pos"]
        cv2.rectangle(img, (bx1, by1), (bx2, by2), (100, 100, 100), 2)
        if angle > 0:
            bar_pos = int(np.interp(angle, (MIN_ANGLE, MAX_ANGLE), (by2, by1)))
            cv2.rectangle(img, (bx1, bar_pos), (bx2, by2), color, -1)

        cv2.imshow("AI反向卷腹计数器", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()