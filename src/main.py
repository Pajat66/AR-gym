from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
import time
from modules.handtrackmodule import handDetector
from features.barbell_curl.barbell_curl1 import run_barbell_curl_left
from features.barbell_curl.barbell_curl2 import run_barbell_curl
from features.barbell_sit.barbell_sit1 import run_barbell_sit_left
from features.barbell_sit.barbell_sit2 import run_barbell_sit_right
from features.hand.FingerCounter import FingerCounter
from features.push_up.pushup_counter import run_pushup_counter
from features.reverse_crunch.reverse_crunch import run_reverse_crunch
from features.squat.sqaut import run_squat_counter  # 添加蹲起功能的导入
from modules.text_to_speech import speak  # 导入语音功能

def display_menu(img, menu_text):
    """在屏幕上显示菜单（支持中文）"""
    # 将 OpenCV 图像转换为 Pillow 图像
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)

    # 加载字体（确保路径正确，或者使用系统字体）
    font_path = "C:/Windows/Fonts/simhei.ttf"  # 黑体字体路径
    font = ImageFont.truetype(font_path, 32)

    # 绘制菜单文本
    y_start = 50
    for i, text in enumerate(menu_text):
        draw.text((50, y_start + i * 40), f"{i}: {text}", font=font, fill=(0, 0, 0))

    # 将 Pillow 图像转换回 OpenCV 图像
    img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    return img

def main():
    cap = cv2.VideoCapture(0)
    cap.set(3, 1280)
    cap.set(4, 720)
    detector = handDetector(detectionCon=0.8, maxHands=1)

    # 菜单设计
    main_menu = ["上肢检测", "下肢检测", "退出"]
    upper_body_menu = ["杠铃弯举", "杠铃坐姿", "返回主菜单"]
    lower_body_menu = ["俯卧撑计数", "反向卷腹", "蹲起", "返回主菜单"]  # 添加蹲起选项
    barbell_curl_menu = ["左侧弯举", "右侧弯举", "返回上一级"]
    barbell_sit_menu = ["左侧坐姿", "右侧坐姿", "返回上一级"]

    current_menu = main_menu
    current_level = "main"

    detected_finger = None  # 当前检测到的手势数字
    detection_start_time = None  # 检测开始时间

    # 程序启动时的语音提示
    speak("欢迎使用健身动作检测系统，请选择您想锻炼的动作")

    while True:
        success, img = cap.read()
        if not success:
            break

        img = cv2.flip(img, 1)
        img = detector.findHands(img)
        lmList, _ = detector.findPosition(img, draw=False)

        if len(lmList) >= 21:
            fingers = detector.fingersUp()
            total_fingers = fingers.count(1)

            # 如果检测到的手势数字发生变化，重置计时
            if total_fingers != detected_finger:
                detected_finger = total_fingers
                detection_start_time = time.time()  # 记录当前时间

            # 检查手势是否保持超过 3 秒
            if detected_finger is not None and (time.time() - detection_start_time >= 3):
                # 执行相应动作
                if current_level == "main":
                    if detected_finger == 1:
                        speak("您选择了上肢检测")
                        current_menu = upper_body_menu
                        current_level = "upper_body"
                    elif detected_finger == 2:
                        speak("您选择了下肢检测")
                        current_menu = lower_body_menu
                        current_level = "lower_body"
                    elif detected_finger == 3:
                        speak("程序即将退出")
                        break  # 退出程序

                elif current_level == "upper_body":
                    if detected_finger == 1:
                        speak("您选择了杠铃弯举")
                        current_menu = barbell_curl_menu
                        current_level = "barbell_curl"
                    elif detected_finger == 2:
                        speak("您选择了杠铃坐姿")
                        current_menu = barbell_sit_menu
                        current_level = "barbell_sit"
                    elif detected_finger == 3:
                        speak("返回主菜单")
                        current_menu = main_menu
                        current_level = "main"

                elif current_level == "lower_body":
                    if detected_finger == 1:
                        speak("开始俯卧撑计数")
                        run_pushup_counter()
                        current_menu = main_menu  # 返回主菜单
                        current_level = "main"
                    elif detected_finger == 2:
                        speak("开始反向卷腹")
                        run_reverse_crunch()
                        current_menu = main_menu  # 返回主菜单
                        current_level = "main"
                    elif detected_finger == 3:
                        speak("开始蹲起")
                        run_squat_counter()  # 调用蹲起功能
                        current_menu = main_menu  # 返回主菜单
                        current_level = "main"
                    elif detected_finger == 4:
                        speak("返回主菜单")
                        current_menu = main_menu
                        current_level = "main"

                elif current_level == "barbell_curl":
                    if detected_finger == 1:
                        speak("开始左侧弯举")
                        run_barbell_curl_left()
                        current_menu = upper_body_menu  # 返回上一级菜单
                        current_level = "upper_body"
                    elif detected_finger == 2:
                        speak("开始右侧弯举")
                        run_barbell_curl()
                        current_menu = upper_body_menu  # 返回上一级菜单
                        current_level = "upper_body"
                    elif detected_finger == 3:
                        speak("返回上一级菜单")
                        current_menu = upper_body_menu
                        current_level = "upper_body"

                elif current_level == "barbell_sit":
                    if detected_finger == 1:
                        speak("开始左侧坐姿")
                        run_barbell_sit_left()
                        current_menu = upper_body_menu  # 返回上一级菜单
                        current_level = "upper_body"
                    elif detected_finger == 2:
                        speak("开始右侧坐姿")
                        run_barbell_sit_right()
                        current_menu = upper_body_menu  # 返回上一级菜单
                        current_level = "upper_body"
                    elif detected_finger == 3:
                        speak("返回上一级菜单")
                        current_menu = upper_body_menu
                        current_level = "upper_body"

                # 重置检测状态，避免重复执行
                detected_finger = None
                detection_start_time = None

        img = display_menu(img, current_menu)
        cv2.imshow("Menu", img)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()