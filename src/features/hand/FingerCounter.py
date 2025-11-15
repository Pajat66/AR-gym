import cv2
import modules.handtrackmodule as htm

class FingerCounter:
    def __init__(self, wCam=640, hCam=480):
        self.wCam = wCam
        self.hCam = hCam
        self.cap = cv2.VideoCapture(0)
        self.cap.set(3, self.wCam)
        self.cap.set(4, self.hCam)
        self.detector = htm.handDetector(detectionCon=0.8, maxHands=1)
        self.tipIds = [4, 8, 12, 16, 20]

    def count_fingers(self):
        """启动手指数检测功能"""
        while True:
            success, img = self.cap.read()
            if not success:
                break

            img = cv2.flip(img, 1)  # 水平翻转视频
            self.detector.findHands(img)
            lmList, bbox = self.detector.findPosition(img, draw=False)

            if len(lmList) >= 21:  # 确保 lmList 至少包含 21 个关键点
                fingers = []
                # 检测拇指
                if lmList[self.tipIds[0]][1] < lmList[self.tipIds[0] - 1][1]:
                    fingers.append(1)
                else:
                    fingers.append(0)

                # 检测其他手指
                for id in range(1, 5):
                    if lmList[self.tipIds[id]][2] < lmList[self.tipIds[id] - 2][2]:
                        fingers.append(1)
                    else:
                        fingers.append(0)

                totalFingers = fingers.count(1)

                # 显示手指数
                cv2.rectangle(img, (50, 350), (200, 450), (0, 255, 0), cv2.FILLED)
                cv2.putText(img, str(totalFingers), (90, 430), cv2.FONT_HERSHEY_PLAIN, 4, (0, 0, 255), 8)

            cv2.imshow("Finger Counting", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):  # 按 'q' 键退出
                break

        self.cap.release()
        cv2.destroyAllWindows()