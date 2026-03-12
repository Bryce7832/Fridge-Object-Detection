import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Firebase SDK for cloud storage
import firebase_admin as firebaseAdmin
from firebase_admin import credentials, firestore

# Flask for the web server and HTTP requests for calling Pi/Jetson
from flask import Flask, render_template, jsonify, request
import requests as httpRequests

app = Flask(__name__)

# Loads API keys and IP addresses from .env file
load_dotenv()

# Network addresses for the Raspberry Pi and Jetson Nano edge devices
PI_IP = os.getenv('PI_IP')
PI_PORT = int(os.getenv('PI_PORT', 5001))
JETSON_IP = os.getenv('JETSON_IP')
JETSON_PORT = int(os.getenv('JETSON_PORT', 5000))

# API keys and server config
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
WEB_PORT = int(os.getenv('WEB_PORT', 8080))
FIREBASE_CRED = os.getenv('FIREBASE_CRED', '')
FIREBASE_PROJECT = os.getenv('FIREBASE_PROJECT', '')

# Firebase connection state
FIREBASE_ENABLED = False
firebaseDb = None

# Stores most recent scan and full scan history
latestInventory = None
inventoryHistory = []

def initFirebase(credPath, projectId):
    # Connects to Firebase using a service account credentials file
    global FIREBASE_ENABLED, firebaseDb

    try:
        cred = credentials.Certificate(credPath)
        firebaseAdmin.initialize_app(cred, {"projectId": projectId})
        firebaseDb = firestore.client()  # Creates a Firestore database client
        FIREBASE_ENABLED = True
        print("[FIREBASE] Connected to project: {}".format(projectId))
    except Exception as e:
        # App can continue functioning without Firebase
        print("[FIREBASE] Not configured: {}".format(e))
        FIREBASE_ENABLED = False

def pushToFirebase(report, userId="default_user"):
    # Uploads the latest scan report to Firestore
    if not FIREBASE_ENABLED or firebaseDb is None:
        return False

    try:
        from firebase_admin import firestore as fs

        # Flatten the report into a Firestore-friendly document
        docData = {
            "timestamp": report.get("report_timestamp", ""),
            "total_items": report.get("total_items_detected", 0),
            "unique_items": report.get("unique_items", 0),
            "inventory": report.get("inventory_summary", []),
            "confidence_filter_pct": report.get("confidence_filter_pct", 75),
            "uploaded_at": fs.SERVER_TIMESTAMP
        }

        # Append to the full history collection
        (
            firebaseDb.collection("users")
            .document(userId)
            .collection("fridge_reports")
            .add(docData)
        )

        # Overwrite the current snapshot for quick reads
        (
            firebaseDb.collection("users")
            .document(userId)
            .collection("fridge_latest")
            .document("current")
            .set(docData)
        )

        return True

    except Exception as e:
        print("[FIREBASE] Push failed: {}".format(e))
        return False

def askLLM(question, inventoryItems):
    # Sends the user's question and current inventory to the Groq LLM and returns an answer
    if not GROQ_API_KEY:
        return {
            "answer": "LLM not configured. Set GROQ_API_KEY in your .env file.",
            "configured": False,
        }

    try:
        # Format the inventory list into readable text for the prompt
        inventoryText = "\n".join(
            "- {} (x{}, avg confidence: {:.0f}%)".format(
                item["item"], item["count"], item["avg_confidence_pct"])
            for item in inventoryItems
        )

        if not inventoryText:
            inventoryText = "(fridge is empty or no scan has been done yet)"

        prompt = """You are a helpful kitchen assistant for a smart fridge system.
                The user has a fridge with items detected by a computer vision system.
                Based on the current inventory, answer their questions about what they can cook,
                what ingredients they're missing, or suggest recipes.

                Be concise and practical. If they ask about a specific recipe, list which ingredients
                they have and which they're missing. Keep responses short (2-4 sentences max) unless
                they ask for a full recipe.

                Current fridge inventory:
                {}

    User question: {}""".format(inventoryText, question)

        # Call the Groq API with the constructed prompt
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(GROQ_API_KEY)
        }
        body = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
        }

        response = httpRequests.post(url, headers=headers, json=body, timeout=30)

        if response.status_code == 200:
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            return {"answer": answer, "configured": True}
        else:
            return {
                "answer": "Groq API error (HTTP {}): {}".format(
                    response.status_code, response.text[:200]),
                "configured": True,
            }

    except Exception as e:
        return {"answer": "LLM error: {}".format(str(e)), "configured": False}