from ultralytics import YOLO

# Load your trained YOLOv8 model
import os

# Load your trained YOLOv8 model - Use relative path for production compatibility
# We assume the model is in 'models/best.pt' relative to this file's parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, "..", "models", "best.pt")

if not os.path.exists(model_path):
    print(f"WARNING: Model not found at {model_path}. Please ensure 'best.pt' is in the 'backend/models' folder.")

model = YOLO(model_path)

# Define your class names
class_names = {
    0: 'Mature(Dead)',
    1: 'Grass',
    2: 'Mature(Healthy)',
    3: 'Young',
    4: 'Mature(Yellow)'
}


