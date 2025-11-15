import cv2
import mediapipe as mp
import numpy as np
import math

class PoseDetector:
    def __init__(self, mode=False, complexity=1, smooth_landmarks=True,
                 enable_segmentation=False, smooth_segmentation=True,
                 detectionCon=0.5, trackCon=0.5):
        self.mode = mode
        self.complexity = complexity
        self.smooth_landmarks = smooth_landmarks
        self.enable_segmentation = enable_segmentation
        self.smooth_segmentation = smooth_segmentation
        self.detectionCon = detectionCon
        self.trackCon = trackCon

        self.mp_draw = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            self.mode, self.complexity, self.smooth_landmarks,
            self.enable_segmentation, self.smooth_segmentation,
            self.detectionCon, self.trackCon
        )

    def find_pose(self, img, draw=True):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.pose.process(img_rgb)
        if self.results.pose_landmarks and draw:
            self.mp_draw.draw_landmarks(
                img, self.results.pose_landmarks, 
                self.mp_pose.POSE_CONNECTIONS
            )
        return img

    def find_position(self, img, draw=True):
        lm_list = []
        if self.results.pose_landmarks:
            for id, lm in enumerate(self.results.pose_landmarks.landmark):
                h, w = img.shape[:2]
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append([id, cx, cy])
                if draw and id in [11, 23, 27]:  # 关键点：左肩、左髋、左脚踝
                    cv2.circle(img, (cx, cy), 5, (255,0,0), cv2.FILLED)
        return lm_list

    def find_angle(self, img, p1, p2, p3, draw=True):
        lm_list = self.find_position(img, draw=False)  # 获取关键点列表
        if not lm_list:
            return 0  # 如果关键点列表为空，返回0

        try:
            x1, y1 = lm_list[p1][1], lm_list[p1][2]
            x2, y2 = lm_list[p2][1], lm_list[p2][2]
            x3, y3 = lm_list[p3][1], lm_list[p3][2]

            # 三维角度计算（改进版）
            v1 = np.array([x1 - x2, y1 - y2])
            v2 = np.array([x3 - x2, y3 - y2])
            dot_product = np.dot(v1, v2)
            angle = np.degrees(np.arccos(
                dot_product / (np.linalg.norm(v1) * np.linalg.norm(v2))
            ))

            if draw:
                # 绘制关键点和连接线
                cv2.line(img, (x1, y1), (x2, y2), (255, 0, 0), 3)
                cv2.line(img, (x3, y3), (x2, y2), (255, 0, 0), 3)
                cv2.circle(img, (x1, y1), 10, (0, 0, 255), cv2.FILLED)
                cv2.circle(img, (x1, y1), 15, (0, 0, 255), 2)
                cv2.circle(img, (x2, y2), 10, (0, 0, 255), cv2.FILLED)
                cv2.circle(img, (x2, y2), 15, (0, 0, 255), 2)
                cv2.circle(img, (x3, y3), 10, (0, 0, 255), cv2.FILLED)
                cv2.circle(img, (x3, y3), 15, (0, 0, 255), 2)
                cv2.putText(img, str(int(angle)), (x2 - 50, y2 + 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
            return angle
        except:
            return 0  # 处理关键点缺失的情况