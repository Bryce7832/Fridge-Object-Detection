from ultralytics import YOLO

def main():
    print("Loading base YOLOv8n model...")
    model = YOLO("yolov8n.pt") 

    # Train using low epochs
    print("Starting training pipeline...")
    results = model.train(
        data="C:/Users/aksha/Downloads/Fridge-Food-Dataset/data.yaml",
        epochs=5,
        imgsz=640,
        device=0,                               # '0' uses NVIDIA's GPU. Change to 'cpu' if you don't have one.
        batch=8,
        project="fridge_vision_project",
        name="initial_test_run"
    )

    print("Validating model...")
    metrics = model.val()
    print(f"Test complete! Check the '{results.save_dir}' directory for your new weights and training graphs.")

if __name__ == '__main__':
    main()