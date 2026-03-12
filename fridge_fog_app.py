#!/usr/bin/env python3
"""
PC (Fog Layer)
Runs on PC. Provides a web UI where the user can:
  1. Click "Scan Fridge" -> requests go through Pi -> Jetson -> back
  2. See the current fridge inventory + annotated camera image
  3. Ask an LLM: "Can I make pasta?" or "What am I missing for tacos?"
  4. Push inventory to Firebase Cloud
Usage:
    pip install flask requests
    python3 fridge_fog_app.py --pi-ip <JETSON_IP> --pi-port 5000 --port 8080 --groq-key gsk_YOUR_KEY
    then open localhost:8080
"""

import os
import json
import argparse
import time
from datetime import datetime

from flask import Flask, render_template, jsonify, request
import requests as http_requests

app = Flask(__name__)

# Config (set through CLI)
# ====================================================================
PI_IP = os.environ.get("PI_IP", "192.168.1.60")
PI_PORT = int(os.environ.get("PI_PORT", "5001"))
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
FIREBASE_ENABLED = False
firebase_db = None

# Store latest inventory in memory
latest_inventory = None
inventory_history = []

# Firebase Integration
# ====================================================================
def init_firebase(cred_path, project_id):
    global FIREBASE_ENABLED, firebase_db
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {"projectId": project_id})
        firebase_db = firestore.client()
        FIREBASE_ENABLED = True
        print("[FIREBASE] Connected to project: {}".format(project_id))
    except Exception as e:
        print("[FIREBASE] Not configured: {}".format(e))
        FIREBASE_ENABLED = False


def push_to_firebase(report, user_id="default_user"):
    if not FIREBASE_ENABLED or firebase_db is None:
        return False
    try:
        from firebase_admin import firestore as fs

        doc_data = {
            "timestamp": report.get("report_timestamp", ""),
            "total_items": report.get("total_items_detected", 0),
            "unique_items": report.get("unique_items", 0),
            "inventory": report.get("inventory_summary", []),
            "confidence_filter_pct": report.get("confidence_filter_pct", 75),
            "uploaded_at": fs.SERVER_TIMESTAMP
        }

        firebase_db.collection("users").document(user_id)\
            .collection("fridge_reports").add(doc_data)

        firebase_db.collection("users").document(user_id)\
            .collection("fridge_latest").document("current").set(doc_data)

        return True
    except Exception as e:
        print("[FIREBASE] Push failed: {}".format(e))
        return False


# LLM Integration (Groq)
# ====================================================================
def ask_llm(question, inventory_items):
    """Ask Groq LLM about recipes based on current fridge inventory."""

    if not GROQ_API_KEY:
        return {
            "answer": "LLM not configured. Get a free API key from console.groq.com and pass --groq-key to enable the recipe assistant.",
            "configured": False
        }

    try:
        import requests as req

        inventory_text = "\n".join([
            "- {} (x{}, avg confidence: {:.0f}%)".format(
                item["item"], item["count"], item["avg_confidence_pct"])
            for item in inventory_items
        ])

        if not inventory_text:
            inventory_text = "(fridge is empty or no scan has been done yet)"

        prompt = """You are a helpful kitchen assistant for a smart fridge system.
        The user has a fridge with items detected by a computer vision system.
        Based on the current inventory, answer their questions about what they can cook,
        what ingredients they're missing, or suggest recipes.

        Be concise and practical. If they ask about a specific recipe, list which ingredients
        they HAVE and which they're MISSING. Keep responses short (2-4 sentences max) unless
        they ask for a full recipe.

        Current fridge inventory:
        {}

        User question: {}"""
        prompt = prompt.format(inventory_text, question)

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(GROQ_API_KEY)
        }
        body = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500
        }

        response = req.post(url, headers=headers, json=body, timeout=30)

        if response.status_code == 200:
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            return {"answer": answer, "configured": True}
        else:
            return {"answer": "Groq API error (HTTP {}): {}".format(
                response.status_code, response.text[:200]), "configured": True}

    except Exception as e:
        return {"answer": "LLM error: {}".format(str(e)), "configured": False}