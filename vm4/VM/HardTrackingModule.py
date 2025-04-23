import cv2
import mediapipe as mp
import time
import math
import pyautogui  # For mouse control


class handDetector():
    def __init__(self, mode=False, maxHands=2, detectionCon=0.5, trackCon=0.5):
        self.mode = mode
        self.maxHands = maxHands
        self.detectionCon = detectionCon
        self.trackCon = trackCon

        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(
            static_image_mode=self.mode,
            max_num_hands=self.maxHands,
            min_detection_confidence=self.detectionCon,
            min_tracking_confidence=self.trackCon
        )
        self.mpDraw = mp.solutions.drawing_utils
        self.lmList = []
        self.handType = "Right"

    def findHands(self, img, draw=True):
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)

        if self.results.multi_hand_landmarks:
            for handLms in self.results.multi_hand_landmarks:
                if draw:
                    self.mpDraw.draw_landmarks(img, handLms, self.mpHands.HAND_CONNECTIONS)
        return img

    def findPosition(self, img, handNo=0, draw=True):
        xList, yList = [], []
        bbox = []
        self.lmList = []

        if self.results.multi_hand_landmarks:
            if handNo < len(self.results.multi_hand_landmarks):
                myHand = self.results.multi_hand_landmarks[handNo]

                # Handedness
                if self.results.multi_handedness:
                    self.handType = self.results.multi_handedness[handNo].classification[0].label

                for id, lm in enumerate(myHand.landmark):
                    h, w, c = img.shape
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    xList.append(cx)
                    yList.append(cy)
                    self.lmList.append([id, cx, cy])
                    if draw:
                        cv2.circle(img, (cx, cy), 5, (255, 0, 255), cv2.FILLED)
                        cv2.putText(img, str(id), (cx + 5, cy + 5),
                                    cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 255), 1)

                xMin, xMax = min(xList), max(xList)
                yMin, yMax = min(yList), max(yList)
                bbox = xMin, yMin, xMax, yMax
                if draw:
                    cv2.rectangle(img, (xMin - 20, yMin - 20),
                                  (xMax + 20, yMax + 20), (0, 255, 0), 2)

        return self.lmList, bbox

    def fingerUp(self):
        fingers = []
        if not self.lmList:
            return fingers

        # Thumb
        if self.handType == "Right":
            fingers.append(1 if self.lmList[4][1] < self.lmList[3][1] else 0)
        else:
            fingers.append(1 if self.lmList[4][1] > self.lmList[3][1] else 0)

        # Fingers: Index to Pinky
        for id in [8, 12, 16, 20]:
            fingers.append(1 if self.lmList[id][2] < self.lmList[id - 2][2] - 20 else 0)

        return fingers

    def findDistance(self, p1, p2, img, draw=True):
        if len(self.lmList) <= max(p1, p2):
            return 0, img, [0, 0, 0, 0, 0, 0]

        x1, y1 = self.lmList[p1][1], self.lmList[p1][2]
        x2, y2 = self.lmList[p2][1], self.lmList[p2][2]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        if draw:
            cv2.circle(img, (x1, y1), 10, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (x2, y2), 10, (255, 0, 255), cv2.FILLED)
            cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 2)
            cv2.circle(img, (cx, cy), 10, (0, 255, 0), cv2.FILLED)

        length = math.hypot(x2 - x1, y2 - y1)
        return length, img, [x1, y1, x2, y2, cx, cy]


def main():
    pTime = 0
    cap = cv2.VideoCapture(0)
    detector = handDetector()

    while True:
        success, img = cap.read()
        if not success:
            break

        img = detector.findHands(img)
        lmList, bbox = detector.findPosition(img)

        if lmList:
            fingers = detector.fingerUp()
            print("Fingers:", fingers)  # Debug info

            thumb_up = fingers[0] == 1
            pinky_up = fingers[4] == 1
            other_fingers = fingers[1:4]  # index, middle, ring

            # Left Click: Only thumb up
            if thumb_up and all(f == 0 for f in other_fingers) and not pinky_up:
                pyautogui.click(button='left')
                cv2.putText(img, 'Left Click', (50, 150),
                            cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 3)
                time.sleep(0.3)

            # Right Click: Only pinky up
            elif pinky_up and all(f == 0 for f in fingers[0:4]):
                pyautogui.click(button='right')
                cv2.putText(img, 'Right Click', (50, 200),
                            cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 3)
                time.sleep(0.3)

        # FPS Display
        cTime = time.time()
        fps = 1 / (cTime - pTime) if cTime != pTime else 0
        pTime = cTime
        cv2.putText(img, f'FPS: {int(fps)}', (10, 70),
                    cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 255), 3)

        cv2.imshow("Hand Tracking", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
