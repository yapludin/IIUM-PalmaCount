from fastapi import APIRouter, File, UploadFile
from services.inference import run_inference

router = APIRouter()

@router.post("/predict")
async def predict(image: UploadFile = File(...)):
    """
    Endpoint to receive image, run YOLOv8 inference, and return results.
    """
    # Run your inference function
    result = run_inference(image)

    # Return JSON response
    return {
        "status": "success",
        "counts": result["counts"],
        "total_mature": result["total_mature"],
        "total_young": result["total_young"],
        "total_oil_palms": result["total_oil_palms"],
        "image_base64": result["image_base64"]
    }
