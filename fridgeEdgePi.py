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

# Handles incoming HTTP requests from the fog layer (PC)
class PiRequestHandler(BaseHTTPRequestHandler):
    # Jetson connection details, set from env vars before server starts
    jetsonIp = JETSON_IP
    jetsonPort = JETSON_PORT

    def do_GET(self):
        # Route incoming GET requests to the appropriate handler
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/scan":
            minConf = float(params.get("min_conf", [DEFAULT_MIN_CONFIDENCE])[0])
            scanConf = float(params.get("scan_conf", [0.25])[0])

            print("[REQUEST] /scan from {} (min_conf={}%, scan_conf={})".format(
                self.client_address[0], minConf, scanConf))

            # Forward scan request to Jetson Nano
            jetsonUrl = "http://{}:{}/scan?conf={}".format(
                self.jetsonIp, self.jetsonPort, scanConf)

            try:
                print("[FORWARD] Requesting scan from Jetson at {}".format(jetsonUrl))
                tStart = time.time()
                response = requests.get(jetsonUrl, timeout=30)
                tJetson = time.time()

                if response.status_code != 200:
                    self._sendJson({"error": "Jetson returned error",
                                    "jetson_status": response.status_code,
                                    "jetson_response": response.text}, 502)
                    return

                rawReport = response.json()
                print("[RECEIVED] Raw report: {} items from Jetson ({:.0f}ms round-trip)".format(
                    rawReport.get("total_items_detected", 0),
                    (tJetson - tStart) * 1000))

            except requests.exceptions.ConnectionError:
                self._sendJson({
                    "error": "Cannot connect to Jetson Nano at {}:{}".format(
                        self.jetsonIp, self.jetsonPort),
                    "hint": "Is fridge_edge_server.py running on the Jetson?"
                }, 503)
                return
            except requests.exceptions.Timeout:
                self._sendJson({"error": "Jetson request timed out (30s)"}, 504)
                return

            # Filter the report by confidence threshold
            filteredReport = filterReport(rawReport, minConfidence=minConf)

            tTotal = time.time()
            filteredReport["pi_processing_time_ms"] = round((tTotal - tJetson) * 1000, 1)
            filteredReport["total_round_trip_ms"] = round((tTotal - tStart) * 1000, 1)

            print("[FILTERED] {} → {} items (removed {} below {}%)".format(
                filteredReport["items_before_filter"],
                filteredReport["items_after_filter"],
                filteredReport["items_removed"],
                minConf))

            # Send filtered report back to the PC
            self._sendJson(filteredReport, 200)

        # Report Pi status and check if Jetson is reachable
        elif parsed.path == "/health":
            jetsonStatus = "unknown"
            try:
                r = requests.get("http://{}:{}/health".format(
                    self.jetsonIp, self.jetsonPort), timeout=5)
                if r.status_code == 200:
                    jetsonStatus = "online"
                else:
                    jetsonStatus = "error (HTTP {})".format(r.status_code)
            except Exception:
                jetsonStatus = "offline"

            health = {
                "status": "online",
                "device": "raspberry-pi",
                "layer": "edge_middleware",
                "confidence_filter_pct": DEFAULT_MIN_CONFIDENCE,
                "jetson_nano": {
                    "ip": self.jetsonIp,
                    "port": self.jetsonPort,
                    "status": jetsonStatus
                },
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self._sendJson(health, 200)

        # Bypass filter and return raw Jetson data for debugging
        elif parsed.path == "/raw":
            scanConf = float(params.get("scan_conf", [0.25])[0])
            try:
                r = requests.get("http://{}:{}/scan?conf={}".format(
                    self.jetsonIp, self.jetsonPort, scanConf), timeout=30)
                self._sendJson(r.json(), r.status_code)
            except Exception as e:
                self._sendJson({"error": str(e)}, 503)

        else:
            self._sendJson({
                "error": "Not found",
                "endpoints": {
                    "GET /scan": "Scan fridge (filtered). Params: ?min_conf=75&scan_conf=0.25",
                    "GET /health": "Check Pi and Jetson status",
                    "GET /raw": "Get raw unfiltered report from Jetson (debug)"
                }
            }, 404)
    #Enables browers from other sites to call API without issues
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    #Sends the data back to the brower in json format
    def _sendJson(self, data, status):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))
def main():
    parser = argparse.ArgumentParser(description="Fridge Pi Middleware — Raspberry Pi")

    # Point the request handler at the Jetson's address
    PiRequestHandler.jetsonIp = JETSON_IP
    PiRequestHandler.jetsonPort = JETSON_PORT

if __name__ == "__main__":
    main()