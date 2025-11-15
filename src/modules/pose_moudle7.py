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
        return img
    
    def findPosition(self, img, draw=True):
        self.lmList = []
        if self.results.pose_landmarks:
            for id, lm in enumerate(self.results.pose_landmarks.landmark):
                h, w = img.shape[:2]
                cx, cy = int(lm.x * w), int(lm.y * h)
                self.lmList.append([id, cx, cy])
                if draw and id in [11, 23, 25]:
                    radius = 10 if id == 23 else 8  # 肩部和膝部加大显示
                    cv2.circle(img, (cx, cy), radius, (255,0,0), cv2.FILLED)
        return self.lmList
    
    def findAngle(self, img, p1, p2, p3, draw=True):
        try:
            x1, y1 = self.lmList[p1][1], self.lmList[p1][2]
            x2, y2 = self.lmList[p2][1], self.lmList[p2][2]
            x3, y3 = self.lmList[p3][1], self.lmList[p3][2]
            
            # 计算角度
            angle = math.degrees(math.atan2(y3 - y2, x3 - x2) - math.atan2(y1 - y2, x1 - x2))
            angle = abs(angle)
            if angle > 180:
                angle = 360 - angle
            
            if draw:
                cv2.line(img, (x1,y1), (x2,y2), (255,0,0), 3)
                cv2.line(img, (x3,y3), (x2,y2), (255,0,0), 3)
                cv2.circle(img, (x1, y1), 10, (0,0,255), cv2.FILLED)
                cv2.circle(img, (x1, y1), 15, (0,0,255), 2)
                cv2.circle(img, (x2, y2), 10, (0,0,255), cv2.FILLED)
                cv2.circle(img, (x2, y2), 15, (0,0,255), 2)
                cv2.circle(img, (x3, y3), 10, (0,0,255), cv2.FILLED)
                cv2.circle(img, (x3, y3), 15, (0,0,255), 2)
                cv2.putText(img, str(int(angle)), (x2-50, y2+50), cv2.FONT_HERSHEY_PLAIN, 2, (0,0,255), 2)
            return angle
        except:
            return 0