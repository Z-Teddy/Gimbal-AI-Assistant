#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import config  # noqa: E402
from app.detectors import create_detector  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description="RetinaFace RKNNLite 单图测试")
    parser.add_argument(
        "--config",
        default=str(PROJECT_DIR / "configs" / "default.yaml"),
        help="YAML 配置文件路径",
    )
    parser.add_argument(
        "--image",
        required=True,
        help="待测试图片路径",
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_DIR / "retinaface_result.jpg"),
        help="结果图输出路径",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    config.configure(args.config)
    settings = config.get_settings()
    settings.setdefault("detector", {})["type"] = "retinaface"

    image = cv2.imread(args.image)
    if image is None:
        raise FileNotFoundError(f"无法读取测试图片: {args.image}")

    detector = create_detector(settings)
    try:
        if not hasattr(detector, "detect_with_outputs"):
            raise RuntimeError("当前 detector 不支持 detect_with_outputs() 调试接口")

        result, outputs = detector.detect_with_outputs(image)
        print(f"outputs_count: {len(outputs)}")
        for index, output in enumerate(outputs):
            array = np.asarray(output)
            print(f"output[{index}]: shape={array.shape} dtype={array.dtype}")

        print(f"target_center: {result.target_center}")
        print(f"detections: {result.detections}")

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), result.annotated_frame)
        print(f"saved_result: {output_path}")
    finally:
        if hasattr(detector, "close"):
            detector.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
