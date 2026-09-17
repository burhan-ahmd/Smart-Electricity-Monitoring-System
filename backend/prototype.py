from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from sheet import sheetdata, update_latest_row
from main_ocr import process_two_meters
from validator import validate_and_map_meters
from datetime import datetime
from analysis import run_analysis
from fastapi.responses import PlainTextResponse


app = FastAPI(title="Smart Electricity Meter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# TEMP FOLDER
# =========================
UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
async def health_check():
    return {
        "status": "ok",
        "service": "Smart Electricity Meter API",
        "endpoints": {
            "process_meters": "/process-meters"
        }
    }


@app.get("/latest-report")
async def latest_report():
    try:
        report_text = await run_analysis()
    except Exception as e:
        report_text = f"Analysis failed: {str(e)}"

    return PlainTextResponse(
        content=report_text,
        media_type="text/plain"
    )



@app.post("/process-meters")
async def process_meters(
    image1: UploadFile = File(...),
    image2: UploadFile = File(...)
):
    # ============================================
    # 🔹 STEP 1: SAVE UPLOADED IMAGES TEMPORARILY
    # ============================================
    path1 = f"{UPLOAD_DIR}/{image1.filename}"
    path2 = f"{UPLOAD_DIR}/{image2.filename}"

    with open(path1, "wb") as f:
        shutil.copyfileobj(image1.file, f)

    with open(path2, "wb") as f:
        shutil.copyfileobj(image2.file, f)
        
    # ============================================
    # 🔹 STEP 2: FETCH LATEST USER DATA (SOURCE OF TRUTH)
    # ============================================
    user_data = sheetdata()

    if not user_data:
        return {
            "status": "error",
            "message": "No user data found in sheet"
        }

    # ============================================
    # 🔹 STEP 3: RUN OCR ON UPLOADED IMAGES
    # ============================================
    ocr_data = await process_two_meters(path1, path2)
    print("ocr_data: ", ocr_data)

    # ============================================
    # 🔹 STEP 3: VALIDATE + MAP OCR → CORRECT METERS
    # (Handles wrong order + wrong images)
    # ============================================
    validation = validate_and_map_meters(user_data, ocr_data)
    print("validation: ", validation)

    # ❌ If validation fails → return error to user
    if validation["status"] == "error":
        return validation

    mapping = validation["mapping"]

    # ============================================
    # 🔹 STEP 4: CALCULATE USAGE (CLEAN + SAFE)
    # ============================================
    results = {}

    for meter_name, data in mapping.items():

        # Convert "Meter 1" → "meter1"
        key = meter_name.lower().replace(" ", "")

        # Last month reading from sheet
        last_reading = int(user_data[key]["last_month_reading"])

        # Current reading from OCR (already validated)
        current_reading = data["current"]

        # Usage calculation
        usage = current_reading - last_reading
        
        # Todays Date 
        today = datetime.now().strftime("%d/%m/%Y")

        # Store result
        results[meter_name] = {
            "Owner Name": user_data[key]["owner_name"],
            "Meter Number": user_data[key]["meter_number"],
            "Group With": user_data[key]["connected_with"],
            "Model": data["model"],
            "Confidence": data["confidence"],
            "Current Reading Date": today,
            "Last Readers Reading Date": user_data[key]["last_reading_date"],
            "Last Readers Reading": last_reading,
            "Current Reading": current_reading,
            "Usage": usage,
            "Difference_from_last": round(data["diff"], 2)  # debug insight
        }

    # ============================================
    # 🔹 STEP 5: UPDATE GOOGLE SHEET (DYNAMIC METERS)
    # ============================================
    try:
        update_payload = {
            meter_name: data["current"]
            for meter_name, data in mapping.items()
        }

        # 🔥 Build full_data EXACTLY like your final response
        full_data = {
            "Date": today,
            "active_meters": list(mapping.keys()),
            "results": results
        }

        # ✅ pass BOTH now
        update_status = update_latest_row(update_payload, full_data)

    except Exception as e:
        update_status = False
        print("UPDATE ERROR:", str(e))
        
    # ============================================
    # 🔹 STEP 7: CLEANUP (IMPORTANT)
    # ============================================
    os.remove(path1)
    os.remove(path2)

    # ============================================
    # 🔹 STEP 6: FINAL RESPONSE
    # ============================================
    try:
        report_text = await run_analysis()
    except Exception as e:
        report_text = f"❌ Analysis failed: {str(e)}"

    # ============================================
    # 🔹 FINAL RESPONSE (WHATSAPP READY TEXT)
    # ============================================
    
    return PlainTextResponse(
    content=report_text,
    media_type="text/plain"
    )
    
    # return {
    #     "status": "success",
    #     "user": {
    #         "name": user_data["name"],
    #         "phone": user_data["phone"]
    #     },
    #     "Date": today,
    #     "active_meters": list(mapping.keys()),
    #     "results": results,
    #     "sheet_updated": update_status,
    #     "report": PlainTextResponse(content=report_text, media_type="text/plain") 
    # }
