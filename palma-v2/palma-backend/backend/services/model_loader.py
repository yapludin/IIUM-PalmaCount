from ultralytics import YOLO

import os

# Get the directory where model_loader.py is located (backend/services)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up one level to 'backend'
backend_dir = os.path.dirname(current_dir)
# Build path to models/best.pt
model_path = os.path.join(backend_dir, "models", "best.pt")

# Load your trained YOLOv8 model
model = YOLO(model_path)

# Define your class names
class_names = {
    0: 'Mature(Dead)',
    1: 'Grass',
    2: 'Mature(Healthy)',
    3: 'Young',
    4: 'Mature(Yellow)'
}


