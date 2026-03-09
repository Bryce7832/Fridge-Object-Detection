# Smart Fridge System

**Team 18: Bryce Hojo, Hiep Tran, Akshay Jayasinghe**

## Communication Protocol

All devices communicate via HTTP REST. The PC sends GET requests to the Raspberry Pi, which forwards them to the Jetson Nano. Responses go back the same way. Configuration on the Pi and PC is managed through `.env` which contains IP Address and API Keys. All devices must be on the same local network.

## How the System Works

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


## Part 1: Jetson Nano (Edge Device)

### Hardware
- NVIDIA Jetson Nano Developer Kit (4GB RAM)
- OBSBOT Tiny 2 Lite USB Webcam (Any USB Webcam should work)

### 1.1 Install Dependencies

```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y python3-pip python3-dev libjpeg-dev \
    libopenblas-dev libopenmpi-dev libomp-dev libfreetype6-dev git wget curl
python3 -m pip install -U pip
python3 -m pip install gdown
```

### 1.2 Install CUDA PyTorch

```bash
gdown "https://drive.google.com/file/d/1TqC6_2cwqiYacjoLhLgrZoap6-sVL2sd/view?usp=sharing" --fuzzy
python3 -m pip install ./torch-1.10.0a0+git36449ea-cp36-cp36m-linux_aarch64.whl

gdown "https://drive.google.com/file/d/1C7y6VSIBkmL2RQnVy8xF9cAnrrpJiJ-K/view?usp=sharing" --fuzzy
python3 -m pip install ./torchvision-0.11.0a0+fa347eb-cp36-cp36m-linux_aarch64.whl
```

### 1.3 Clone YOLOv7 Tiny

```bash
mkdir ~/fridge-detector
cd ~/fridge-detector

git clone https://github.com/WongKinYiu/yolov7.git
cd yolov7

pip3 install --upgrade pip setuptools wheel
pip3 install numpy==1.19.4 matplotlib

sed -i 's/^opencv-python/#opencv-python/' requirements.txt
sed -i 's/^torch/#torch/' requirements.txt
sed -i 's/^torchvision/#torchvision/' requirements.txt

pip3 install -r requirements.txt
python3 -m pip install cython pyyaml --upgrade
```

### 1.4 Start Edge Server

```bash
cd ~/fridge-detector/yolov7
python3 fridgeEdgeJetson.py --weights best.pt --port 5000 --camera 0
```

## Part 2: Raspberry Pi (Edge Middleware)

### Hardware
- Raspberry Pi 5

### 2.1 Install Dependencies

```bash
sudo apt update
sudo apt install python3-pip -y
pip3 install requests python-dotenv
```

### 2.2 Create .env File

```
JETSON_IP=<YOUR_JETSON_IP>
JETSON_PORT=5000
PI_IP=<YOUR_PI_IP>
PI_PORT=5001
```