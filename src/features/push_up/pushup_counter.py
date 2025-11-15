import cv2
import numpy as np
import time
from modules.pose_module5 import PoseDetector  # 修改为模块化路径
from PIL import ImageFont, ImageDraw, Image  # 新增Pillow依赖
from modules.text_to_speech import speak  # 导入语音播报模块

# 配置参数
ROTATE_VIDEO = False  # True-手机竖屏模式 / False-电脑横屏模式
MIRROR_IMAGE = True
FONT_PATH = '../assets/fonts/msyh.ttc'  # 字体路径（根据项目结构调整）

# 运动参数
MIN_ANGLE = 40    # 最低点角度（胸部接近地面）
MAX_ANGLE = 130   # 最高点角度（手臂伸直）
TRUNK_ANGLE_THRESHOLD = 150  # 躯干直线阈值

# 滤波器参数
FILTER_WINDOW_SIZE = 5
angle_buffer = []

def dynamic_layout(img):
    """动态界面布局系统"""
    h, w = img.shape[:2]
    return {
        "count_box": (20, 20, 320, 120) if not ROTATE_VIDEO else (20, h-160, 320, h-20),
        "angle_pos": (w-300, 100) if not ROTATE_VIDEO else (w//2-80, h//2),
        "fps_pos": (w-200, 50) if not ROTATE_VIDEO else (30, 50),
        "bar_pos": (w-100, 300, w-50, 600) if not ROTATE_VIDEO else (w-100, 300, w-50, h-100)  # 调整 y 坐标
    }

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

def filter_angle(angle):
    """使用滑动窗口滤波器平滑角度"""
    angle_buffer.append(angle)
    if len(angle_buffer) > FILTER_WINDOW_SIZE:
        angle_buffer.pop(0)
    return np.mean(angle_buffer)

def run_pushup_counter():
    """运行俯卧撑计数功能"""
    speak("Starting push-up counter")
    cap = cv2.VideoCapture(0)
    if ROTATE_VIDEO:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 720)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1280)
    else:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    detector = PoseDetector()
    count = 0
    direction = 0  # 0=向上阶段, 1=向下阶段
    pTime = 0
    last_feedback = ""
    danger_timer = 0

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
        img = detector.find_pose(img, draw=False)
        lm_list = detector.find_position(img, draw=True)

        # 获取动态布局参数
        layout = dynamic_layout(img)
        h, w = img.shape[:2]

        if len(lm_list) >= 25:  # 确保检测到所有关键点
            # 计算肩部与脚腕之间的角度
            shoulder_to_ankle_angle = detector.find_angle(img, 11, 23, 27)

            # 使用滤波器平滑角度
            filtered_angle = filter_angle(shoulder_to_ankle_angle)

            # 俯卧撑计数逻辑
            if filtered_angle > MAX_ANGLE - 20 and direction == 0:  # 增加缓冲区
                direction = 1  # 进入下降阶段
            elif filtered_angle < MIN_ANGLE + 20 and direction == 1:  # 增加缓冲区
                direction = 0
                count += 1  # 完整动作计数

            # 可视化反馈
            color = (0, 255, 0) if direction == 0 else (0, 0, 255)
            img = putChineseText(img, f"{int(filtered_angle)}°", layout["angle_pos"], 40, color[::-1])  # BGR转RGB
            img = putChineseText(img, f"计数: {count}", (layout["angle_pos"][0], layout["angle_pos"][1]+50), 30, color[::-1])

        # 界面绘制
        # 1. 计数面板
        x1, y1, x2, y2 = layout["count_box"]
        cv2.rectangle(img, (x1, y1), (x2, y2), (245, 117, 16), -1)
        img = putChineseText(img, f"计数: {int(count)}", (x1+20, y1+30), 30, (255, 255, 255))

        # 2. FPS显示
        cTime = time.time()
        fps = 1 / (cTime - pTime)
        pTime = cTime
        img = putChineseText(img, f"帧率: {int(fps)}", layout["fps_pos"], 24, (0, 255, 0))

        # 3. 安全指示条
        bx1, by1, bx2, by2 = layout["bar_pos"]
        cv2.rectangle(img, (bx1, by1), (bx2, by2), (100, 100, 100), 2)
        if len(lm_list) >= 25:
            bar_pos = int(np.interp(filtered_angle, (MIN_ANGLE, MAX_ANGLE), (by2, by1)))
            cv2.rectangle(img, (bx1, bar_pos), (bx2, by2), color, -1)

        cv2.imshow("AI俯卧撑计数器", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()