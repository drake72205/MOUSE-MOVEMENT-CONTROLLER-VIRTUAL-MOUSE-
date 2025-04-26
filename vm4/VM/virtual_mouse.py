import cv2
import numpy as np
import HardTrackingModule as htm  # Your custom hand tracking module
import autopy
import time
import pyautogui
import streamlit as st
import os

# For volume control
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# Initialize session state for app running status
if 'running' not in st.session_state:
    st.session_state.running = True

##########################
wCam, hCam = 640, 480
frameR = 100  # Frame reduction
smoothening = 7
##########################

# Initialize camera
cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)

if not cap.isOpened():
    st.error("Error: Camera not found!")
    st.session_state.running = False
    st.stop()

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

# Dragging state
dragging = False
rightClicked = False

# Streamlit app title
st.title("🖐️ Hand Gesture Control System")

# Sidebar controls
enable_mouse_control = st.sidebar.checkbox("🖱 Enable Mouse Control", value=True)
enable_volume_control = st.sidebar.checkbox("🔊 Enable Volume Control", value=True)
enable_screenshot = st.sidebar.checkbox("📸 Enable Screenshot", value=True)
enable_scrolling = st.sidebar.checkbox("🧭 Enable Scrolling", value=True)
enable_dragging = st.sidebar.checkbox("✊ Enable Dragging", value=True)

# Exit button
if st.sidebar.button("❌ Exit App"):
    st.session_state.running = False
    if cap.isOpened():
        cap.release()
    cv2.destroyAllWindows()
    st.warning("App stopped. You can close this tab.")
    st.stop()

# Real-time frame display in Streamlit
frame_placeholder = st.empty()

def cleanup():
    if cap.isOpened():
        cap.release()
    cv2.destroyAllWindows()

try:
    while st.session_state.running:
        success, img = cap.read()
        if not success:
            st.error("Error: Failed to capture image!")
            st.session_state.running = False
            break

        img = detector.findHands(img)
        lmList, bbox = detector.findPosition(img, draw=False)

        if len(lmList) != 0:
            x1, y1 = lmList[8][1], lmList[8][2]
            x2, y2 = lmList[12][1], lmList[12][2]
            x0, y0 = lmList[4][1], lmList[4][2]

            fingers = detector.fingerUp()

            if enable_mouse_control and fingers[1] == 1 and fingers[2] == 0:
                x3 = np.interp(x1, (frameR, wCam - frameR), (0, screenW))
                y3 = np.interp(y1, (frameR, hCam - frameR), (0, screenH))

                clocX = plocX + (x3 - plocX) / smoothening
                clocY = plocY + (y3 - plocY) / smoothening

                autopy.mouse.move(screenW - clocX, clocY)
                plocX, plocY = clocX, clocY

                cv2.circle(img, (x1, y1), 10, (255, 0, 255), cv2.FILLED)

            if enable_mouse_control and fingers[1] == 1 and fingers[2] == 1:
                length, img, lineInfo = detector.findDistance(8, 12, img)
                if length < 40:
                    cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (0, 255, 0), cv2.FILLED)
                    autopy.mouse.click()

            if enable_volume_control and fingers[0] == 1 and fingers[1] == 1 and fingers[2] == 0:
                length, img, lineInfo = detector.findDistance(4, 8, img)
                vol = np.interp(length, [30, 200], [minVol, maxVol])
                volume.SetMasterVolumeLevel(vol, None)

                volPercent = int(np.interp(vol, [minVol, maxVol], [0, 100]))
                cv2.putText(img, f"Volume: {volPercent}%", (10, 150), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
                cv2.circle(img, (lineInfo[4], lineInfo[5]), 10, (0, 0, 255), cv2.FILLED)

            if enable_screenshot and fingers == [0, 0, 0, 0, 0]:
                filename = f'screenshot_{int(time.time())}.png'
                pyautogui.screenshot(filename)
                cv2.putText(img, "Screenshot Taken", (10, 120), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)
                time.sleep(1)

            if enable_scrolling and fingers == [0, 1, 1, 1, 1]:
                pyautogui.scroll(30)
                cv2.putText(img, "Scrolling Up", (10, 180), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 100), 2)

            if enable_scrolling and fingers == [1, 1, 1, 1, 1]:
                pyautogui.scroll(-30)
                cv2.putText(img, "Scrolling Down", (10, 180), cv2.FONT_HERSHEY_PLAIN, 2, (0, 100, 255), 2)

            if enable_mouse_control and fingers == [0, 0, 0, 1, 1]:
                if not rightClicked:
                    autopy.mouse.click(autopy.mouse.Button.RIGHT)
                    rightClicked = True
                    cv2.putText(img, "Right Click", (10, 240), cv2.FONT_HERSHEY_PLAIN, 2, (100, 200, 255), 2)
                    time.sleep(0.9)

            if enable_mouse_control and fingers == [0, 0, 0, 0, 1]:
                autopy.mouse.click()
                time.sleep(0.1)
                autopy.mouse.click()
                cv2.putText(img, "Double Click", (10, 270), cv2.FONT_HERSHEY_PLAIN, 2, (255, 100, 100), 2)
                time.sleep(0.9)

            if enable_dragging and fingers == [0, 0, 1, 1, 1]:
                x_drag, y_drag = lmList[12][1], lmList[12][2]
                y_drag_screen = np.interp(y_drag, (frameR, hCam - frameR), (0, screenH))
                x_drag_screen = np.interp(x_drag, (frameR, wCam - frameR), (0, screenW))

                clocX = plocX + (x_drag_screen - plocX) / smoothening
                clocY = plocY + (y_drag_screen - plocY) / smoothening

                autopy.mouse.move(screenW - clocX, clocY)
                plocX, plocY = clocX, clocY

                if not dragging:
                    pyautogui.mouseDown()
                    dragging = True
                    cv2.putText(img, "Drag Start", (10, 300), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 150), 2)
            else:
                if dragging:
                    pyautogui.mouseUp()
                    dragging = False
                    cv2.putText(img, "Drop", (10, 300), cv2.FONT_HERSHEY_PLAIN, 2, (0, 150, 255), 2)

        cTime = time.time()
        fps = 1 / (cTime - pTime)
        pTime = cTime
        cv2.putText(img, f"FPS: {int(fps)}", (10, 70), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 255), 3)

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        frame_placeholder.image(img_rgb, channels="RGB", use_container_width=True)

finally:
    cleanup()
