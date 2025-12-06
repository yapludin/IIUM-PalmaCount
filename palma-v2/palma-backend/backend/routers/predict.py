from fastapi import APIRouter, File, UploadFile, HTTPException
from services.inference import run_inference
import traceback

router = APIRouter()

@router.post("/predict")
async def predict(image: UploadFile = File(...)):
    """
    Endpoint to receive image, run YOLOv8 inference, and return results.
    """
    try:
        # Run your inference function
        result = run_inference(image)

        # SAFETY CHECK: Did the function return nothing?
        if result is None:
            print("CRITICAL ERROR: run_inference returned None!")
            raise HTTPException(status_code=500, detail="AI processing finished but returned no data. Check inference.py return statement.")

        # Return JSON response
        return {
            "status": "success",
            "counts": result["counts"],
            "total_mature": result["total_mature"],
            "total_young": result["total_young"],
            "total_oil_palms": result["total_oil_palms"],
            
            # New Research Data
            "total_area_m2": result["total_area_m2"],
            "total_area_ha": result["total_area_ha"],
            "method_used": result["method_name"],
            
            # Images
            "image_base64": result["image_base64"],
            "chart_base64": result["chart_base64"]
        }

    except Exception as e:
        # Print the full error to the terminal so you can see it
        print("--- BACKEND ERROR ---")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))