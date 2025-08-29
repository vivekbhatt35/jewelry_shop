# YOLOv8 Training Script
# Use this script to train your security detection model with the updated class structure

import os
import yaml
from ultralytics import YOLO

# Configuration
CONFIG_PATH = 'security_dataset.yaml'
MODEL_NAME = 'yolov8m.pt'  # Start with medium-sized model
BATCH_SIZE = 16
EPOCHS = 100
IMAGE_SIZE = 640  # Standard YOLO image size

def main():
    # Ensure the config file exists
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: Dataset configuration file {CONFIG_PATH} not found!")
        print("Please create it with the correct path to your dataset.")
        return
    
    # Load the dataset configuration to verify it
    try:
        with open(CONFIG_PATH, 'r') as file:
            config = yaml.safe_load(file)
            print(f"Loaded dataset config with {len(config['names'])} classes:")
            for idx, name in config['names'].items():
                print(f"  {idx}: {name}")
    except Exception as e:
        print(f"Error loading dataset configuration: {e}")
        return
    
    # Initialize the model
    print(f"Loading base model: {MODEL_NAME}")
    model = YOLO(MODEL_NAME)
    
    # Train the model
    print("Starting training...")
    results = model.train(
        data=CONFIG_PATH,
        epochs=EPOCHS,
        batch=BATCH_SIZE,
        imgsz=IMAGE_SIZE,
        workers=8,
        project='security_model',
        name='yolov8_security_detector',
        verbose=True,
        device='0',  # Use GPU. Set to 'cpu' if no GPU available
        patience=10,  # Early stopping patience
        save=True,
        save_period=10,  # Save checkpoints every 10 epochs
    )
    
    # Validate the model after training
    print("Validating trained model...")
    model.val()
    
    print("Training complete! Model saved to security_model/yolov8_security_detector")
    print("Copy the best.pt file to your model directory to use it in your system")

if __name__ == "__main__":
    main()
