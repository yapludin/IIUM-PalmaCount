from fastapi import APIRouter, File, UploadFile, HTTPException
from services.inference import run_inference
import traceback
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/predict")
def predict(image: UploadFile = File(...)):
    """
    Endpoint to receive image, run YOLOv8 inference, and return results
    formatted specifically for the PalmaCount results template.
    """
    try:
        # 1. Run the full inference pipeline (Detections + Area + Charts)
        result = run_inference(image)

        # 2. SAFETY CHECK: Did the function return nothing?
        if result is None:
            print("CRITICAL ERROR: run_inference returned None!")
            raise HTTPException(
                status_code=500, 
                detail="AI processing finished but returned no data."
            )

        # 3. STRUCTURE DATA FOR HTML TEMPLATE
        # We wrap everything in an 'analysis' key so the HTML can use {{ analysis.field }}
        analysis_data = {
            "analysis_id": f"PLC-{str(uuid.uuid4())[:8].upper()}",
            "original_filename": image.filename,
            "processed_filename": result.get("processed_filename", ""), # Path to saved image
            "created_at": datetime.now(),
            
            # Tree Counts
            "mature_count": result["total_mature"],
            "young_count": result["total_young"],
            "total_count": result["total_oil_palms"],
            
            # Area Estimation (The missing part)
            "total_area_m2": result["total_area_m2"],
            "total_area_ha": result["total_area_ha"],
            "method_name": result["method_name"],
            
            # Visuals (Base64)
            "image_base64": result["image_base64"],
            "chart_base64": result["chart_base64"]
        }

        # 4. Return JSON response
        return {
            "status": "success",
            "analysis": analysis_data
        }

    except Exception as e:
        # Print the full error to the terminal for debugging
        print("--- BACKEND ERROR ---")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))