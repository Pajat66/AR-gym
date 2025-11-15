import cv2
import mediapipe as mp
import time
import numpy as np
import math

class poseDetector:
    def __init__(self, mode=False, smooth=True, detectionCon=0.7, trackCon=0.7):
        self.mode = mode
        self.smooth = smooth
        self.detectionCon = detectionCon
        self.trackCon = trackCon

        self.mpDraw = mp.solutions.drawing_utils
        self.mpPose = mp.solutions.pose
        self.pose = self.mpPose.Pose(
            static_image_mode=self.mode,
            model_complexity=1,
            smooth_landmarks=self.smooth,
            min_detection_confidence=self.detectionCon,
            min_tracking_confidence=self.trackCon
        )

    def findPose(self, img, draw=True):
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.pose.process(imgRGB)
        if self.results.pose_landmarks and draw:
            # 只绘制关键连接线
            connections = self.mpPose.POSE_CONNECTIONS
            key_connections = [c for c in connections if c[0] in [12,14,16,11,13,15]]
            self.mpDraw.draw_landmarks(img, self.results.pose_landmarks, key_connections)
        return img
    
    def findPosition(self, img, draw=True):
        self.lmList = []
        if self.results.pose_landmarks:
            for id, lm in enumerate(self.results.pose_landmarks.landmark):
                h, w = img.shape[:2]
                cx, cy = int(lm.x * w), int(lm.y * h)
                self.lmList.append([id, cx, cy])
                if draw and id in [11,13,15]:
                    # 绘制智能关键点（不同关节不同大小）
                    radius = 12 if id == 14 else 8  # 肘关节加大显示
                    cv2.circle(img, (cx, cy), radius, (255,0,0), cv2.FILLED)
        return self.lmList
    
    def findAngle(self, img, p1, p2, p3, draw=True):
        try:
            # 三维空间角度计算
            x1, y1, z1 = self.lmList[p1][1], self.lmList[p1][2], self.results.pose_landmarks.landmark[p1].z
            x2, y2, z2 = self.lmList[p2][1], self.lmList[p2][2], self.results.pose_landmarks.landmark[p2].z
            x3, y3, z3 = self.lmList[p3][1], self.lmList[p3][2], self.results.pose_landmarks.landmark[p3].z
            
            # 计算三维向量
            v1 = np.array([x1-x2, y1-y2, z1-z2])
            v2 = np.array([x3-x2, y3-y2, z3-z2])
            
            # 向量夹角公式
            cos_theta = np.dot(v1, v2) / (np.linalg.norm(v1)*np.linalg.norm(v2))
            angle = np.degrees(np.arccos(np.clip(cos_theta, -1, 1)))
            
            if draw:
                cv2.line(img,(x1,y1),(x2,y2),(255,0,0),3)
                cv2.line(img,(x3,y3),(x2,y2),(255,0,0),3)
                cv2.circle(img, (x1, y1), 10,(0, 0, 255),cv2.FILLED)
                cv2.circle(img, (x1, y1), 15,(0, 0, 255),2)
                cv2.circle(img, (x2, y2), 10,(0, 0, 255),cv2.FILLED)
                cv2.circle(img, (x2, y2), 15,(0, 0, 255),2)
                cv2.circle(img, (x3, y3), 10,(0, 0, 255),cv2.FILLED)
                cv2.circle(img, (x3, y3), 15,(0, 0, 255),2)
                cv2.putText(img, str(int(angle)), (x2 - 50, y2 + 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
            return angle
        except Exception as e:
            return 0