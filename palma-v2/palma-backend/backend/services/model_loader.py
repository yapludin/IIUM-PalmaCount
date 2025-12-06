from ultralytics import YOLO

# Load your trained YOLOv8 model
model = YOLO("C:/Users/Isyraf Haziq/palma-v2/palma-backend/backend/models/best.pt")  # move your model to backend/models folder

# Define your class names
class_names = {
    0: 'Mature(Dead)',
    1: 'Grass',
    2: 'Mature(Healthy)',
    3: 'Young',
    4: 'Mature(Yellow)'
}
