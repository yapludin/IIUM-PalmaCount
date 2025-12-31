from ultralytics import YOLO
import os

# Define your class names
class_names = {
    0: 'Mature(Dead)',
    1: 'Grass',
    2: 'Mature(Healthy)',
    3: 'Young',
    4: 'Mature(Yellow)'
}

_model = None

def get_model():
    """Lazily load the YOLO model."""
    global _model
    if _model is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, "..", "models", "best.pt")
        
        if not os.path.exists(model_path):
            print(f"WARNING: Model not found at {model_path}")
            # Consider raising an exception or handling this gracefully
            
        print(f"Loading YOLO model from {model_path}...")
        _model = YOLO(model_path)
        print("YOLO model loaded successfully.")
    
    return _model


