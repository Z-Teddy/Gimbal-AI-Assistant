from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np

import config

from app.detectors.base import BaseDetector, DetectionResult
from app.detectors.retinaface_postprocess import (
    RetinaFaceDetection,
    build_priors,
    letterbox_resize,
    postprocess_retinaface,
)


class RetinaFaceRKNNDetector(BaseDetector):
    detector_type = "retinaface"

    def __init__(self, settings):
        self.logger = logging.getLogger(__name__)
        self.settings = settings

        detector_cfg = settings.get("detector", {})
        retinaface_cfg = detector_cfg.get("retinaface", {})
        if not isinstance(retinaface_cfg, dict):
            raise ValueError("detector.retinaface 必须是对象")

        self.model_path = self._resolve_model_path(
            str(
                retinaface_cfg.get(
                    "model_path",
                    "models/retinaface/RetinaFace_mobile320.rknn",
                )
            )
        )
        self.input_size = int(retinaface_cfg.get("input_size", 320))
        if self.input_size != 320:
            raise ValueError("第一版 RetinaFace detector 仅支持 input_size=320")

        self.candidate_threshold = float(retinaface_cfg.get("candidate_threshold", 0.02))
        self.score_threshold = float(retinaface_cfg.get("score_threshold", 0.4))
        self.nms_threshold = float(retinaface_cfg.get("nms_threshold", 0.4))
        self.draw_landmarks = bool(retinaface_cfg.get("draw_landmarks", False))
        self.bg_color = int(retinaface_cfg.get("bg_color", 114))
        self._printed_infer_input = False

        camera_cfg = settings.get("camera", {})
        self.flip = camera_cfg.get("flip", config.CAM_FLIP)
        self.priors = build_priors(self.input_size)
        self.runtime = self._init_runtime(self.model_path)

        self.logger.info(
            "RetinaFace detector 初始化完成: model=%s input_size=%s",
            self.model_path,
            self.input_size,
        )

    def _resolve_model_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path

        project_dir = Path(__file__).resolve().parents[2]
        config_dir = Path(config.CONFIG_PATH).resolve().parent

        candidates = [
            Path.cwd() / path,
            project_dir / path,
            config_dir / path,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()

        return (project_dir / path).resolve()

    def _init_runtime(self, model_path: Path):
        if not model_path.exists():
            raise FileNotFoundError(f"RetinaFace RKNN 模型不存在: {model_path}")

        try:
            from rknnlite.api import RKNNLite
        except ImportError as exc:
            raise RuntimeError(
                "无法导入 rknnlite.api.RKNNLite，请在 conda gimbal 环境中运行"
            ) from exc

        runtime = RKNNLite()

        ret = runtime.load_rknn(str(model_path))
        if ret != 0:
            raise RuntimeError(f"加载 RKNN 模型失败: {model_path} ret={ret}")

        ret = runtime.init_runtime(core_mask=RKNNLite.NPU_CORE_AUTO)
        if ret != 0:
            runtime.release()
            raise RuntimeError(f"初始化 RKNNLite runtime 失败 ret={ret}")

        return runtime

    def _prepare_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, object]:
        display_frame = frame
        if self.flip is not None:
            display_frame = cv2.flip(display_frame, self.flip)

        letterbox_frame, meta = letterbox_resize(
            display_frame,
            self.input_size,
            bg_color=self.bg_color,
        )
        infer_frame = cv2.cvtColor(letterbox_frame, cv2.COLOR_BGR2RGB)
        infer_frame = np.expand_dims(infer_frame, axis=0)
        infer_frame = np.ascontiguousarray(infer_frame)
        return display_frame, infer_frame, meta

    def _infer_outputs(self, infer_frame: np.ndarray) -> Sequence[np.ndarray]:
        if not self._printed_infer_input:
            print(
                f"[RetinaFace] inference input shape={infer_frame.shape} dtype={infer_frame.dtype}"
            )
            self._printed_infer_input = True

        try:
            outputs = self.runtime.inference(
                inputs=[infer_frame],
                data_format="nhwc",
            )
        except TypeError:
            outputs = self.runtime.inference(inputs=[infer_frame])

        if outputs is None:
            raise RuntimeError("RKNNLite inference 未返回任何输出")
        return outputs

    def _select_primary_target(
        self,
        detections: Sequence[RetinaFaceDetection],
    ) -> Optional[RetinaFaceDetection]:
        if not detections:
            return None
        return max(detections, key=lambda item: item.area)

    def _draw_detections(
        self,
        frame: np.ndarray,
        detections: Sequence[RetinaFaceDetection],
        primary: Optional[RetinaFaceDetection],
    ) -> None:
        for detection in detections:
            x, y, w, h = detection.bbox
            color = (0, 255, 0)
            thickness = 2
            if detection is primary:
                color = (0, 0, 255)
                thickness = 3

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
            cv2.putText(
                frame,
                f"{detection.score:.3f}",
                (x, max(18, y + 14)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )

            if self.draw_landmarks:
                for point in detection.landmarks:
                    cv2.circle(frame, point, 2, (255, 255, 0), -1)

        if primary is None:
            cv2.putText(
                frame,
                "Scanning...",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 0, 0),
                2,
            )
            return

        center = primary.center
        cv2.circle(frame, center, 5, (0, 0, 255), -1)
        cv2.putText(
            frame,
            f"Target: {center}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
        )

    def _build_result(
        self,
        frame: np.ndarray,
        detections: Sequence[RetinaFaceDetection],
    ) -> DetectionResult:
        annotated_frame = frame.copy()
        primary = self._select_primary_target(detections)
        self._draw_detections(annotated_frame, detections, primary)

        target_center = primary.center if primary is not None else None
        boxes = tuple(detection.bbox for detection in detections)

        return DetectionResult(
            annotated_frame=annotated_frame,
            target_center=target_center,
            detections=boxes,
        )

    def detect_with_outputs(self, frame: np.ndarray) -> Tuple[DetectionResult, Sequence[np.ndarray]]:
        display_frame, infer_frame, meta = self._prepare_frame(frame)
        outputs = self._infer_outputs(infer_frame)
        detections = postprocess_retinaface(
            outputs,
            meta,
            self.priors,
            candidate_threshold=self.candidate_threshold,
            score_threshold=self.score_threshold,
            nms_threshold=self.nms_threshold,
        )
        result = self._build_result(display_frame, detections)
        return result, outputs

    def detect(self, frame) -> DetectionResult:
        result, _ = self.detect_with_outputs(frame)
        return result

    def close(self) -> None:
        if self.runtime is not None:
            self.runtime.release()
            self.runtime = None


__all__ = ["RetinaFaceRKNNDetector"]
