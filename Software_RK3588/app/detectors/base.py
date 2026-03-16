from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple


BoundingBox = Tuple[int, int, int, int]
TargetCenter = Tuple[int, int]


@dataclass(frozen=True)
class DetectionResult:
    annotated_frame: object
    target_center: Optional[TargetCenter]
    detections: Tuple[BoundingBox, ...] = ()

    @property
    def found(self) -> bool:
        return self.target_center is not None


class BaseDetector(ABC):
    detector_type = "base"

    def process_frame(self, frame) -> DetectionResult:
        return self.detect(frame)

    @abstractmethod
    def detect(self, frame) -> DetectionResult:
        raise NotImplementedError
