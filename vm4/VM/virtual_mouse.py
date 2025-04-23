import cv2
import numpy as np
import HardTrackingModule as htm  # Your custom hand tracking module
import autopy
import time
import math
import pyautogui

# For volume control
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

##########################
wCam, hCam = 640, 480
frameR = 100  # Frame reduction
smoothening = 7
##########################

cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)

if not cap.isOpened():
    print("Error: Camera not found!")
    exit()

pTime = 0
plocX, plocY = 0, 0
clocX, clocY = 0, 0

detector = htm.handDetector(maxHands=1)
screenW, screenH = autopy.screen.size()

# Volume control setup
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
volRange = volume.GetVolumeRange()
minVol, maxVol = volRange[0], volRange[1]
#drag and drop
dragging = False
# Right Click
rightClicked = False
while True:
    # Read frame from camera
    success, img = cap.read()
    if not success:
        print("Error: Failed to capture image!")
        break

    img = detector.findHands(img)
    lmList, bbox = detector.findPosition(img, draw=False)

    if len(lmList) != 0:
        x1, y1 = lmList[8][1], lmList[8][2]   # Index
        x2, y2 = lmList[12][1], lmList[12][2] # Middle
        x0, y0 = lmList[4][1], lmList[4][2]   # Thumb

        fingers = detector.fingerUp()

        # 1. Move mouse with index finger only
        if fingers[1] == 1 and fingers[2] == 0:
            x3 = np.interp(x1, (frameR, wCam - frameR), (0, screenW))
            y3 = np.interp(y1, (frameR, hCam - frameR), (0, screenH))

            clocX = plocX + (x3 - plocX) / smoothening
            clocY = plocY + (y3 - plocY) / smoothening

            autopy.mouse.move(screenW - clocX, clocY)
            plocX, plocY = clocX, clocY

            cv2.circle(img, (x1, y1), 10, (255, 0, 255), cv2.FILLED)

        # 2. Click when index and middle are up
        if fingers[1] == 1 and fingers[2] == 1:
            length, img, lineInfo = detector.findDistance(8, 12, img)
            if length < 40:
                cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (0, 255, 0), cv2.FILLED)
                autopy.mouse.click()

        # 3. Volume control with thumb and index
        if fingers[0] == 1 and fingers[1] == 1 and fingers[2] == 0:
            length, img, lineInfo = detector.findDistance(4, 8, img)
            vol = np.interp(length, [30, 200], [minVol, maxVol])
            volume.SetMasterVolumeLevel(vol, None)

            # Show volume level
            volPercent = int(np.interp(vol, [minVol, maxVol], [0, 100]))
            cv2.putText(img, f"Volume: {volPercent}%", (10, 150), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
            cv2.circle(img, (lineInfo[4], lineInfo[5]), 10, (0, 0, 255), cv2.FILLED)

        # 4. Screenshot if all fingers are down
        if fingers == [0, 0, 0, 0, 0]:
            filename = f'screenshot_{int(time.time())}.png'
            pyautogui.screenshot(filename)
            cv2.putText(img, "Screenshot Taken", (10, 120), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)
            time.sleep(1)  # avoid multiple captures

         # 5. Scroll with index and pinky
        if fingers == [0, 1, 1, 1, 1]:
            pyautogui.scroll(30)  # Positive = Scroll up
            cv2.putText(img, "Scrolling Up", (10, 180), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 100), 2)
                
        # 6. Scroll Down when all fingers are up
        if fingers == [1, 1, 1, 1, 1]:
            pyautogui.scroll(-30)  # Negative = Scroll down
            cv2.putText(img, "Scrolling Down", (10, 180), cv2.FONT_HERSHEY_PLAIN, 2, (0, 100, 255), 2)

        # 7. Right Click with Ring + Pinky
        if fingers[0] == 0 and fingers[1] == 0 and fingers[2] == 0 and fingers[3] == 1 and fingers[4] == 1:
            if not rightClicked:
                autopy.mouse.click(autopy.mouse.Button.RIGHT)
                rightClicked = True
                cv2.putText(img, "Right Click", (10, 240), cv2.FONT_HERSHEY_PLAIN, 2, (100, 200, 255), 2)
                time.sleep(0.9)


        
        # 8. Double Click with pinky
        if fingers == [0, 0, 0, 0, 1]:
            autopy.mouse.click()
            time.sleep(0.1)
            autopy.mouse.click()
            cv2.putText(img, "Double Click", (10, 270), cv2.FONT_HERSHEY_PLAIN, 2, (255, 100, 100), 2)
            time.sleep(0.9)
    
         # 9. Drag and Move with Middle + Ring + Pinky
        if fingers == [0, 0, 1, 1, 1]:  # Check if Middle, Ring, and Pinky are up
            # Get the middle finger's position
            x_drag, y_drag = lmList[12][1], lmList[12][2]
    
            # Map the finger's position to screen coordinates
            y_drag_screen = np.interp(y_drag, (frameR, hCam - frameR), (0, screenH))
            x_drag_screen = np.interp(x_drag, (frameR, wCam - frameR), (0, screenW))

            # Smooth the movement to avoid jittery motion
            clocX = plocX + (x_drag_screen - plocX) / smoothening
            clocY = plocY + (y_drag_screen - plocY) / smoothening
    
            # Move the mouse to the new position
            autopy.mouse.move(screenW - clocX, clocY)
            plocX, plocY = clocX, clocY

            #        Start dragging if not already dragging
            if not dragging:
                pyautogui.mouseDown()  # Mouse down to start dragging
                dragging = True
                cv2.putText(img, "Drag Start", (10, 300), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 150), 2)
        else:
            # Release the mouse when the gesture ends
            if dragging:        
               pyautogui.mouseUp()  # Mouse up to drop the dragged item
               dragging = False
               cv2.putText(img, "Drop", (10, 300), cv2.FONT_HERSHEY_PLAIN, 2, (0, 150, 255), 2)

        # 10. Show finger count




             

    # Show FPS
    cTime = time.time()
    fps = 1 / (cTime - pTime)
    pTime = cTime
    cv2.putText(img, f"FPS: {int(fps)}", (10, 70), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 255), 3)

    # Show image
    cv2.imshow("Virtual Mouse", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
