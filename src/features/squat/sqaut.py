import cv2
import numpy as np
import time
from modules.pose_moudle7 import poseDetector  # 修改为模块化路径
from PIL import ImageFont, ImageDraw, Image  # 新增Pillow依赖
from modules.text_to_speech import speak  # 引入全局语音模块

# 配置参数
ROTATE_VIDEO = False  # True-手机竖屏模式 / False-电脑横屏模式
MIRROR_IMAGE = True
FONT_PATH = '../assets/fonts/msyh.ttc'  # 字体路径（根据项目结构调整）

# 运动参数
MIN_ANGLE = 50
MAX_ANGLE = 120
OPTIMAL_RANGE = (40, 90)

def dynamic_layout(img):
    """动态界面布局系统"""
    h, w = img.shape[:2]
    return {
        "count_box": (20, 20, 320, 120) if not ROTATE_VIDEO else (20, h-160, 320, h-20),
        "angle_pos": (w-300, 100) if not ROTATE_VIDEO else (w//2-80, h//2),
        "fps_pos": (w-200, 50) if not ROTATE_VIDEO else (30, 50),
        "bar_pos": (w-100, 200, w-50, 500) if not ROTATE_VIDEO else (w-100, 200, w-50, h-200)
    }

def map_color(angle, last_feedback, optimal_timer):
    """智能颜色映射"""
    feedback = ""
    color = (255, 255, 0)  # 默认颜色为黄色，表示注意稳定

    # 如果夹角在最佳范围内，增加稳定性计数器
    if OPTIMAL_RANGE[0] <= angle <= OPTIMAL_RANGE[1]:
        optimal_timer += 1
    else:
        optimal_timer = 0

    # 根据稳定性计数器给出反馈
    if optimal_timer >= 10:  # 连续10次夹角在最佳范围内，认为姿势稳定
        feedback = "姿势稳定，很棒"
        color = (0, 255, 0)  # 绿色
        optimal_timer = 0  # 重置稳定性计数器
    else:
        feedback = "注意身体保持稳定"

    # 给予语音提示
    if feedback != last_feedback:
        speak(feedback)  # 使用全局语音模块
        last_feedback = feedback

    return color, feedback, last_feedback, optimal_timer

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

def draw_keypoints_and_connections(img, lmlist, p1, p2, p3, draw=True):
    """绘制关键点和连接线"""
    if not lmlist:
        return

    x1, y1 = lmlist[p1][1], lmlist[p1][2]
    x2, y2 = lmlist[p2][1], lmlist[p2][2]
    x3, y3 = lmlist[p3][1], lmlist[p3][2]

    if draw:
        # 绘制关键点和连接线
        cv2.line(img, (x1, y1), (x2, y2), (255, 0, 0), 3)
        cv2.line(img, (x3, y3), (x2, y2), (255, 0, 0), 3)
        cv2.circle(img, (x1, y1), 10, (0, 0, 255), cv2.FILLED)
        cv2.circle(img, (x2, y2), 10, (0, 0, 255), cv2.FILLED)
        cv2.circle(img, (x3, y3), 10, (0, 0, 255), cv2.FILLED)

def run_squat_counter():
    """运行蹲起计数功能"""
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

        if len(lmList) >= 16:
            # 计算胯部、膝关节和脚踝之间的夹角
            angle = detector.findAngle(img, 24, 26, 28)

            # 智能计数系统
            if angle > MAX_ANGLE and dir == 0:
                count += 0.5
                dir = 1
            elif angle < MIN_ANGLE and dir == 1:
                count += 0.5
                dir = 0

            # 可视化反馈
            color, feedback, last_feedback, optimal_timer = map_color(angle, last_feedback, optimal_timer)
            img = putChineseText(img, f"{int(angle)}°", layout["angle_pos"], 40, color[::-1])  # BGR转RGB
            img = putChineseText(img, feedback, (layout["angle_pos"][0], layout["angle_pos"][1]+50), 30, color[::-1])

            # 关节保护提示
            if angle < 20:
                img = putChineseText(img, "膝盖弯曲过度警告！", (layout["angle_pos"][0], layout["angle_pos"][1]+100), 30, (255, 0, 0))

            # 绘制左髋-左膝-左脚踝的关键点和连接线
            draw_keypoints_and_connections(img, lmList, 24, 26, 28)

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
        if len(lmList) >= 16:
            bar_pos = int(np.interp(angle, (MIN_ANGLE, MAX_ANGLE), (by2, by1)))
            cv2.rectangle(img, (bx1, bar_pos), (bx2, by2), color, -1)

        cv2.imshow("AI健身教练 - 蹲起检测", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()