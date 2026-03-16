from app.detectors.base import BaseDetector, DetectionResult
from app.detectors.haar_detector import HaarFaceDetector


def create_detector(settings) -> BaseDetector:
    detector_cfg = settings.get("detector", {})
    detector_type = str(detector_cfg.get("type", "haar_face")).strip()

    if detector_type == "haar_face":
        return HaarFaceDetector()

    raise ValueError(f"不支持的 detector.type: {detector_type}")


__all__ = [
    "BaseDetector",
    "DetectionResult",
    "HaarFaceDetector",
    "create_detector",
]
