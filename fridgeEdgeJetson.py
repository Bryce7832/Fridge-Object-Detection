import sys
import os
import json
import time
import base64
import argparse
import threading
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Computer vision and ML libraries
import cv2
import torch
import numpy as np

# Add yolo directory to path so model utilities can be imported
FILE = Path(__file__).resolve()
ROOT = FILE.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from models.experimental import attempt_load
from utils.general import check_img_size, non_max_suppression, scale_coords, set_logging
from utils.datasets import letterbox
from utils.torch_utils import select_device, TracedModel

# Add yolo directory to path so model utilities can be imported
FILE = Path(__file__).resolve()
ROOT = FILE.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from models.experimental import attempt_load
from utils.general import check_img_size, non_max_suppression, scale_coords, set_logging
from utils.datasets import letterbox
from utils.torch_utils import select_device, TracedModel

class FridgeDetector:
    def __init__(self, weights, deviceId, imgSize, cameraIndex):
        # Initialize device, load the YOLO model and run a warmup pass
        self.device = select_device(deviceId)
        self.imgSize = imgSize
        self.cameraIndex = cameraIndex
        self._lock = threading.Lock()

        print("[INIT] Loading model: {}".format(weights))
        self.model = attempt_load(weights, map_location=self.device)
        self.stride = int(self.model.stride.max())
        self.imgSize = check_img_size(imgSize, s=self.stride)
        self.model = TracedModel(self.model, self.device, self.imgSize)

        # Get class names from the model
        self.classNames = self.model.module.names if hasattr(self.model, "module") else self.model.names
        if isinstance(self.classNames, dict):
            self.classNames = [self.classNames[i] for i in range(len(self.classNames))]

        # Initial warmup pass for the jetson nano to reduce latency on the first real run
        if self.device.type != 'cpu':
            self.model(torch.zeros(1, 3, self.imgSize, self.imgSize).to(self.device).type_as(
                next(self.model.parameters())))

        print("[INIT] Model loaded. {} classes: {}".format(len(self.classNames), self.classNames))

    def captureAndDetect(self, confThres=0.25, iouThres=0.45):
        # Capture a single frame from the camera and run it through the YOLO model to detect items in the fridge
        with self._lock:
            cap = cv2.VideoCapture('/dev/video{}'.format(self.cameraIndex), cv2.CAP_V4L2)
            if not cap.isOpened():
                return {"error": "Cannot open webcam {}".format(self.cameraIndex)}, 500

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

            for _ in range(5):
                cap.read()

            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                return {"error": "Failed to capture frame"}, 500

        # Preprocess the captured frame and prepare it for inference
        img = letterbox(frame, self.imgSize, stride=self.stride)[0]
        img = img[:, :, ::-1].transpose(2, 0, 1)
        img = np.ascontiguousarray(img)
        img = torch.from_numpy(img).to(self.device).float()
        img /= 255.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # Run inference and measure time taken for the model to process the image
        t1 = time.time()
        with torch.no_grad():
            pred = self.model(img)[0]
        t2 = time.time()

        pred = non_max_suppression(pred, confThres, iouThres)
        t3 = time.time()

        inferenceMs = (t2 - t1) * 1000
        nmsMs = (t3 - t2) * 1000

        # Process the model's predictions to extract detected items, their confidence scores, and bounding boxes
        detections = []
        for det in pred:
            if len(det):
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], frame.shape).round()
                for *xyxy, conf, clsId in reversed(det):
                    detections.append({
                        "item": self.classNames[int(clsId)],
                        "confidence_pct": round(float(conf) * 100, 2),
                        "bounding_box": {
                            "x1": int(xyxy[0]), "y1": int(xyxy[1]),
                            "x2": int(xyxy[2]), "y2": int(xyxy[3])
                        }
                    })

        # Output a summary of detected items, including counts and average confidence scores
        summary = {}
        for det in detections:
            item = det["item"]
            if item not in summary:
                summary[item] = {"count": 0, "confidences": []}
            summary[item]["count"] += 1
            summary[item]["confidences"].append(det["confidence_pct"])

        inventorySummary = []
        for item, info in sorted(summary.items()):
            avgConf = round(sum(info["confidences"]) / len(info["confidences"]), 2)
            inventorySummary.append({
                "item": item,
                "count": info["count"],
                "avg_confidence_pct": avgConf,
                "individual_confidences_pct": info["confidences"]
            })

        # Draw bounding boxes on the frame for the annotated image
        annotated = frame.copy()
        for det in detections:
            bb = det["bounding_box"]
            label = "{} {:.1f}%".format(det["item"], det["confidence_pct"])
            cv2.rectangle(annotated, (bb["x1"], bb["y1"]), (bb["x2"], bb["y2"]), (0, 255, 0), 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(annotated, (bb["x1"], bb["y1"] - th - 10), (bb["x1"] + tw, bb["y1"]), (0, 255, 0), -1)
            cv2.putText(annotated, label, (bb["x1"], bb["y1"] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

        # Allows the annotated image to be sent as a string in the JSON response
        _, imgEncoded = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        imgBase64 = base64.b64encode(imgEncoded.tobytes()).decode('utf-8')