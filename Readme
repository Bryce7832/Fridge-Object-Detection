# Smart Fridge System - Guide

**Team 18: Bryce Hojo, Hiep Tran, Akshay Jayasinghe**

### Communication Protocol

All devices communicate via HTTP REST. The PC sends GET requests to the Raspberry Pi, which forwards them to the Jetson Nano. Responses go back the same way. Configuration on the Pi and PC is managed through `.env` which contains IP Address and API Keys. All devices must be on the same local network.

### How the System Works

1. User opens browser at http://localhost:8080 and clicks "Scan My Fridge"
2. PC sends GET to Raspberry Pi
3. Pi forwards GET to Jetson Nano
4. Jetson opens webcam, captures frame, runs YOLOv7 on the image to detect objects
5. Jetson returns back a JSON with bounding boxes and confidence scores
6. Pi filters out items below 75% confidence
7. Pi returns filtered report + image to PC (Website)
8. PC renders inventory in React UI with annotated camera image
9. User can ask LLM questions (Uses Grok API)
10. User clicks "Push to Firebase" → Inventory stored in Firestore Cloud