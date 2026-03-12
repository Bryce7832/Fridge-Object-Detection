import json
import argparse
import time
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# HTTP client for forwarding requests to the Jetson
import requests

# Loads IP addresses and port numbers from .env file
load_dotenv()

JETSON_IP = os.getenv('JETSON_IP')
JETSON_PORT = int(os.getenv('JETSON_PORT'))
PI_PORT = int(os.getenv('PI_PORT'))
PI_IP = os.getenv('PI_IP')

# Minimum confidence threshold, anything below this will be filtered out of the report before sending to the PC
DEFAULT_MIN_CONFIDENCE = 75.0

# Filters a raw Jetson report, removing detections below the confidence threshold
def filterReport(rawReport, minConfidence=75.0):

    # Keep only detections that meet the minimum confidence
    filteredDetections = [
        det for det in rawReport.get("detailed_detections", [])
        if det["confidence_pct"] >= minConfidence
    ]

    # Rebuild per-item summary from filtered detections only
    summary = {}
    for det in filteredDetections:
        item = det["item"]
        if item not in summary:
            summary[item] = {"count": 0, "confidences": []}
        summary[item]["count"] += 1
        summary[item]["confidences"].append(det["confidence_pct"])

    filteredInventory = []
    for item, info in sorted(summary.items()):
        avgConf = round(sum(info["confidences"]) / len(info["confidences"]), 2)
        filteredInventory.append({
            "item": item,
            "count": info["count"],
            "avg_confidence_pct": avgConf,
            "individual_confidences_pct": info["confidences"]
        })

    filteredReport = {
        "report_timestamp": rawReport.get("report_timestamp", ""),
        "source": rawReport.get("source", "unknown"),
        "processed_by": "raspberry_pi",
        "layer": "edge_filtered",

        # Filter info
        "confidence_filter_pct": minConfidence,
        "items_before_filter": rawReport.get("total_items_detected", 0),
        "items_after_filter": len(filteredDetections),
        "items_removed": rawReport.get("total_items_detected", 0) - len(filteredDetections),

        # Timing from Jetson
        "inference_time_ms": rawReport.get("inference_time_ms", 0),
        "nms_time_ms": rawReport.get("nms_time_ms", 0),

        # Filtered results
        "total_items_detected": len(filteredDetections),
        "unique_items": len(summary),
        "inventory_summary": filteredInventory,
        "detailed_detections": filteredDetections,

        "raw_summary": rawReport.get("inventory_summary", []),

        # Pass through the annotated image from Jetson
        "annotated_image_base64": rawReport.get("annotated_image_base64", "")
    }

    return filteredReport