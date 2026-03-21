import cv2
import imutils

from monitor.config import MIN_AREA, THRESHOLD


def motion_detection(prev_frame, curr_frame) -> bool:
    """对比两帧画面，检测是否有移动。返回 True 表示有移动。"""
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)
    curr_gray = cv2.GaussianBlur(curr_gray, (21, 21), 0)

    frame_delta = cv2.absdiff(prev_gray, curr_gray)
    thresh = cv2.threshold(frame_delta, THRESHOLD, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)

    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)

    for c in cnts:
        if cv2.contourArea(c) > MIN_AREA:
            return True
    return False
