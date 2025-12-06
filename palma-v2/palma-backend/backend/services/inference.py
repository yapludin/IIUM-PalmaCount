import base64
from io import BytesIO
from PIL import Image
import numpy as np
from .model_loader import model, class_names

def run_inference(image_file):
    """
    Runs YOLOv8 model on uploaded image and returns counts and base64 image
    """

    # Load image using PIL
    img = Image.open(image_file.file)
    img_array = np.array(img)

    # Run YOLOv8 prediction
    results = model.predict(img_array)[0]

    # Initialize counters
    counters = {name: 0 for name in class_names.values()}

    # Count detections
    for box in results.boxes:
        class_id = int(box.cls)
        class_name = class_names[class_id]
        counters[class_name] += 1

    # Calculate totals (optional)
    total_mature = counters['Mature(Dead)'] + counters['Mature(Healthy)'] + counters['Mature(Yellow)']
    total_young = counters['Young']

    # Draw annotated image
    annotated_image = results.plot()
    annotated_image_rgb = Image.fromarray(annotated_image[..., ::-1])

    # Convert image to base64
    buffer = BytesIO()
    annotated_image_rgb.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode()

    return {
        "counts": counters,
        "total_mature": total_mature,
        "total_young": total_young,
        "total_oil_palms": total_mature + total_young,
        "image_base64": img_base64
    }
