import cv2

import config

from app.detectors.base import BaseDetector, DetectionResult


class HaarFaceDetector(BaseDetector):
    detector_type = "haar_face"

    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        if self.face_cascade.empty():
            raise RuntimeError("无法加载 OpenCV Haar Cascade 模型")

    def detect(self, frame) -> DetectionResult:
        if config.CAM_FLIP is not None:
            frame = cv2.flip(frame, config.CAM_FLIP)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 6)

        target_center = None
        max_area = 0
        boxes = []

        for (x, y, w, h) in faces:
            boxes.append((int(x), int(y), int(w), int(h)))
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            area = w * h
            if area > max_area:
                max_area = area
                target_center = (x + w // 2, y + h // 2)

        if target_center:
            cv2.circle(frame, target_center, 5, (0, 0, 255), -1)
            cv2.putText(
                frame,
                f"Target: {target_center}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )
        else:
            cv2.putText(
                frame,
                "Scanning...",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 0, 0),
                2,
            )

        return DetectionResult(
            annotated_frame=frame,
            target_center=target_center,
            detections=tuple(boxes),
        )
