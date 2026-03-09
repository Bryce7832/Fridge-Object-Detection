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