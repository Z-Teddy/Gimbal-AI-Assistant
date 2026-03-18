from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from math import ceil
from typing import Iterable, List, Sequence, Tuple

import cv2
import numpy as np


_VARIANCES = (0.1, 0.2)
_MIN_SIZES = ((16, 32), (64, 128), (256, 512))
_STEPS = (8, 16, 32)


@dataclass(frozen=True)
class LetterboxMeta:
    scale: float
    offset_x: int
    offset_y: int
    input_size: int
    image_width: int
    image_height: int


@dataclass(frozen=True)
class RetinaFaceDetection:
    bbox: Tuple[int, int, int, int]
    score: float
    landmarks: Tuple[Tuple[int, int], ...] = ()

    @property
    def center(self) -> Tuple[int, int]:
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)

    @property
    def area(self) -> int:
        _, _, w, h = self.bbox
        return max(0, w) * max(0, h)

    @property
    def xyxy(self) -> Tuple[int, int, int, int]:
        x, y, w, h = self.bbox
        return (x, y, x + w, y + h)


def letterbox_resize(
    image: np.ndarray,
    input_size: int,
    bg_color: int = 114,
) -> Tuple[np.ndarray, LetterboxMeta]:
    image_height, image_width = image.shape[:2]
    scale = min(input_size / image_width, input_size / image_height)
    resized_width = max(1, int(image_width * scale))
    resized_height = max(1, int(image_height * scale))

    resized = cv2.resize(
        image,
        (resized_width, resized_height),
        interpolation=cv2.INTER_AREA,
    )
    canvas = np.full((input_size, input_size, 3), bg_color, dtype=np.uint8)
    offset_x = (input_size - resized_width) // 2
    offset_y = (input_size - resized_height) // 2
    canvas[offset_y:offset_y + resized_height, offset_x:offset_x + resized_width] = resized

    meta = LetterboxMeta(
        scale=scale,
        offset_x=offset_x,
        offset_y=offset_y,
        input_size=input_size,
        image_width=image_width,
        image_height=image_height,
    )
    return canvas, meta


@lru_cache(maxsize=4)
def build_priors(input_size: int) -> np.ndarray:
    anchors = []
    feature_maps = [[ceil(input_size / step), ceil(input_size / step)] for step in _STEPS]
    for feature_index, feature_map in enumerate(feature_maps):
        min_sizes = _MIN_SIZES[feature_index]
        step = _STEPS[feature_index]
        for i, j in product(range(feature_map[0]), range(feature_map[1])):
            for min_size in min_sizes:
                s_kx = min_size / input_size
                s_ky = min_size / input_size
                dense_cx = [(j + 0.5) * step / input_size]
                dense_cy = [(i + 0.5) * step / input_size]
                for cy, cx in product(dense_cy, dense_cx):
                    anchors.extend((cx, cy, s_kx, s_ky))
    return np.asarray(anchors, dtype=np.float32).reshape(-1, 4)


def decode_boxes(loc: np.ndarray, priors: np.ndarray) -> np.ndarray:
    boxes = np.concatenate(
        (
            priors[:, :2] + loc[:, :2] * _VARIANCES[0] * priors[:, 2:],
            priors[:, 2:] * np.exp(loc[:, 2:] * _VARIANCES[1]),
        ),
        axis=1,
    )
    boxes[:, :2] -= boxes[:, 2:] / 2
    boxes[:, 2:] += boxes[:, :2]
    return boxes


def decode_landmarks(landms: np.ndarray, priors: np.ndarray) -> np.ndarray:
    return np.concatenate(
        (
            priors[:, :2] + landms[:, 0:2] * _VARIANCES[0] * priors[:, 2:],
            priors[:, :2] + landms[:, 2:4] * _VARIANCES[0] * priors[:, 2:],
            priors[:, :2] + landms[:, 4:6] * _VARIANCES[0] * priors[:, 2:],
            priors[:, :2] + landms[:, 6:8] * _VARIANCES[0] * priors[:, 2:],
            priors[:, :2] + landms[:, 8:10] * _VARIANCES[0] * priors[:, 2:],
        ),
        axis=1,
    )


def nms(dets: np.ndarray, threshold: float) -> List[int]:
    if dets.size == 0:
        return []

    x1 = dets[:, 0]
    y1 = dets[:, 1]
    x2 = dets[:, 2]
    y2 = dets[:, 3]
    scores = dets[:, 4]

    areas = np.maximum(0.0, x2 - x1 + 1) * np.maximum(0.0, y2 - y1 + 1)
    order = scores.argsort()[::-1]

    keep: List[int] = []
    while order.size > 0:
        index = int(order[0])
        keep.append(index)

        xx1 = np.maximum(x1[index], x1[order[1:]])
        yy1 = np.maximum(y1[index], y1[order[1:]])
        xx2 = np.minimum(x2[index], x2[order[1:]])
        yy2 = np.minimum(y2[index], y2[order[1:]])

        width = np.maximum(0.0, xx2 - xx1 + 1)
        height = np.maximum(0.0, yy2 - yy1 + 1)
        inter = width * height
        union = areas[index] + areas[order[1:]] - inter
        iou = np.divide(inter, union, out=np.zeros_like(inter), where=union > 0)

        remaining = np.where(iou <= threshold)[0]
        order = order[remaining + 1]

    return keep


def _prepare_tensor(output: np.ndarray, expected_last_dim: int) -> np.ndarray:
    tensor = np.asarray(output)
    tensor = np.squeeze(tensor)

    if tensor.ndim == 1:
        if tensor.size % expected_last_dim != 0:
            raise ValueError(
                f"无法将输出 reshape 为 (*, {expected_last_dim})，实际 size={tensor.size}"
            )
        tensor = tensor.reshape(-1, expected_last_dim)

    if tensor.ndim != 2:
        raise ValueError(f"不支持的输出维度: {tensor.shape}")

    if tensor.shape[-1] == expected_last_dim:
        return tensor.astype(np.float32, copy=False)

    if tensor.shape[0] == expected_last_dim:
        return tensor.T.astype(np.float32, copy=False)

    raise ValueError(
        f"输出 shape 与预期不匹配: actual={tensor.shape} expected_last_dim={expected_last_dim}"
    )


def _split_outputs(outputs: Sequence[np.ndarray]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    if len(outputs) < 3:
        raise ValueError(f"RetinaFace 至少需要 3 个输出，实际只有 {len(outputs)} 个")

    grouped = {}
    for output in outputs:
        tensor = np.squeeze(np.asarray(output))
        if tensor.ndim >= 2 and tensor.shape[-1] in {2, 4, 10} and tensor.shape[-1] not in grouped:
            grouped[tensor.shape[-1]] = output

    if {2, 4, 10}.issubset(grouped):
        loc_raw = grouped[4]
        conf_raw = grouped[2]
        landms_raw = grouped[10]
    else:
        loc_raw, conf_raw, landms_raw = outputs[:3]

    loc = _prepare_tensor(loc_raw, 4)
    conf = _prepare_tensor(conf_raw, 2)
    landms = _prepare_tensor(landms_raw, 10)
    return loc, conf, landms


def _scale_boxes_to_image(boxes: np.ndarray, meta: LetterboxMeta) -> np.ndarray:
    scale = np.array(
        [meta.input_size, meta.input_size, meta.input_size, meta.input_size],
        dtype=np.float32,
    )
    boxes = boxes * scale
    boxes[:, 0::2] = np.clip(
        (boxes[:, 0::2] - meta.offset_x) / meta.scale,
        0,
        meta.image_width,
    )
    boxes[:, 1::2] = np.clip(
        (boxes[:, 1::2] - meta.offset_y) / meta.scale,
        0,
        meta.image_height,
    )
    return boxes


def _scale_landmarks_to_image(landmarks: np.ndarray, meta: LetterboxMeta) -> np.ndarray:
    scale = np.array([meta.input_size, meta.input_size] * 5, dtype=np.float32)
    landmarks = landmarks * scale
    landmarks[:, 0::2] = np.clip(
        (landmarks[:, 0::2] - meta.offset_x) / meta.scale,
        0,
        meta.image_width,
    )
    landmarks[:, 1::2] = np.clip(
        (landmarks[:, 1::2] - meta.offset_y) / meta.scale,
        0,
        meta.image_height,
    )
    return landmarks


def postprocess_retinaface(
    outputs: Sequence[np.ndarray],
    meta: LetterboxMeta,
    priors: np.ndarray,
    candidate_threshold: float = 0.02,
    score_threshold: float = 0.4,
    nms_threshold: float = 0.4,
) -> List[RetinaFaceDetection]:
    loc, conf, landms = _split_outputs(outputs)

    if not (loc.shape[0] == conf.shape[0] == landms.shape[0] == priors.shape[0]):
        raise ValueError(
            "RetinaFace 输出数量与 priors 数量不匹配: "
            f"loc={loc.shape} conf={conf.shape} landms={landms.shape} priors={priors.shape}"
        )

    boxes = _scale_boxes_to_image(decode_boxes(loc, priors), meta)
    landmarks = _scale_landmarks_to_image(decode_landmarks(landms, priors), meta)
    scores = conf[:, 1]

    keep = np.where(scores > candidate_threshold)[0]
    if keep.size == 0:
        return []

    boxes = boxes[keep]
    landmarks = landmarks[keep]
    scores = scores[keep]

    order = scores.argsort()[::-1]
    boxes = boxes[order]
    landmarks = landmarks[order]
    scores = scores[order]

    dets = np.hstack((boxes, scores[:, np.newaxis])).astype(np.float32, copy=False)
    final_keep = nms(dets, nms_threshold)

    detections: List[RetinaFaceDetection] = []
    for index in final_keep:
        score = float(scores[index])
        if score < score_threshold:
            continue

        x1, y1, x2, y2 = boxes[index]
        x1_i = max(0, int(x1))
        y1_i = max(0, int(y1))
        x2_i = max(x1_i, int(x2))
        y2_i = max(y1_i, int(y2))
        width = x2_i - x1_i
        height = y2_i - y1_i

        raw_landmarks = landmarks[index].reshape(5, 2)
        points = tuple((int(point[0]), int(point[1])) for point in raw_landmarks)

        detections.append(
            RetinaFaceDetection(
                bbox=(x1_i, y1_i, width, height),
                score=score,
                landmarks=points,
            )
        )

    return detections


__all__ = [
    "LetterboxMeta",
    "RetinaFaceDetection",
    "build_priors",
    "letterbox_resize",
    "postprocess_retinaface",
]
