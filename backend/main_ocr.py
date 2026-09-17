import cv2
from inference_sdk import InferenceHTTPClient
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from dotenv import load_dotenv
from pydantic import BaseModel
from pathlib import Path
import uuid


# ==============================
# LOAD API FOR LLM
# ==============================
load_dotenv()

# ==============================
# RESPONSE MODEL
# ==============================
class Digits(BaseModel):
    digits: float
    confidence: int


# ==============================
# INIT MODELS (GLOBAL = FAST)
# ==============================
# roboflow_client = InferenceHTTPClient(
#     api_url="https://serverless.roboflow.com",
#     api_key="DH8qnhbDkjGvL9lcjIVq"
# )

# initialize the client
roboflow_client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="DH8qnhbDkjGvL9lcjIVq"
)

# ==============================
# SETUP OF GOOGLE MODELS WITH THINKING LEVEL CONFIG
# ==============================

model_settings = GoogleModelSettings(google_thinking_config={'thinking_level': 'high'})  # 'low' or 'high'

primary_model = GoogleModel('gemini-3-flash-preview')
fallback_model = GoogleModel('gemini-3.1-flash-lite-preview')

agent_primary = Agent(
    primary_model, 
    system_prompt="Extract exact decimal number from meter image. Return accurate digits with decimal and confidence.",          
    model_settings=model_settings,
    output_type=Digits
)

agent_fallback = Agent(
    fallback_model,
    system_prompt="Extract exact decimal number from meter image. Return accurate digits with decimal and confidence.",          
    model_settings=model_settings,
    output_type=Digits
)


# agent_primary = Agent(
#     "gemini-3-flash-preview",  # fast, high limit
#     system_prompt="Extract exact decimal number from meter image. Return accurate digits with decimal and confidence.",
# )

# agent_fallback = Agent(
#     "gemini-3.1-flash-lite-preview",  # backup
#     system_prompt="Extract exact decimal number from meter image. Return accurate digits with decimal and confidence.",
#     output_type=Digits
# )


# ==============================
# CORE OCR FUNCTION (SINGLE IMAGE)
# ==============================
async def process_single_image(image_path: str):
    try:
        img = cv2.imread(image_path)

        if img is None:
            return {"error": f"Image not found: {image_path}"}

        # 🔹 STEP 1: Detect screen
        result = roboflow_client.infer(img, model_id="meter-box-144tb/1")
        predictions = result.get("predictions", [])

        if not predictions:
            return {"error": "No meter detected"}

        best = max(predictions, key=lambda p: p["confidence"])

        x1 = int(best["x"] - best["width"] / 2)
        y1 = int(best["y"] - best["height"] / 2)
        x2 = int(best["x"] + best["width"] / 2)
        y2 = int(best["y"] + best["height"] / 2)

        # bounds safety
        h, w = img.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        cropped = img[y1:y2, x1:x2]
        
        # # 1. upscale
        # img2 = cv2.resize(cropped, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # # 2. grayscale
        # gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # # # 3. denoise
        # denoise = cv2.fastNlMeansDenoising(gray, None, 5, 7, 21)

        # # # 4. contrast boost
        # clahe = cv2.createCLAHE(clipLimit=9.9, tileGridSize=(1,1))
        # contrast_boost = clahe.apply(denoise)

        # 🔹 save temp cropped image (needed for LLM)
        temp_path = f"temp_{uuid.uuid4().hex}.jpg"
        cv2.imwrite(temp_path, cropped)

        image_bytes = Path(temp_path).read_bytes()

        try:
            # 🔹 STEP 2: OCR with primary model
            try:
                response = await agent_primary.run([
                    "What digits are in this image?",
                    BinaryContent(data=image_bytes, media_type="image/jpeg")
                ])
                print("Primary Agent Worked successfully")
                return {
                    "digits": response.output.digits,
                    "confidence": response.output.confidence,
                    "model": "primary"
                }

            except Exception:
                # 🔁 fallback model
                response = await agent_fallback.run([
                    "What digits are in this image?",
                    BinaryContent(data=image_bytes, media_type="image/jpeg")
                ])
                print("Fallback Agent Worked successfully")
                return {
                    "digits": response.output.digits,
                    "confidence": response.output.confidence,
                    "model": "fallback"
                }

        finally:
            # 🔥 ALWAYS DELETE TEMP FILE
            try:
                if Path(temp_path).exists():
                    Path(temp_path).unlink()
                    print(f"Deleted temp file: {temp_path}")
            except Exception as cleanup_error:
                print("Cleanup error:", cleanup_error)

    except Exception as e:
        return {"error": str(e)}


# ==============================
# MAIN FUNCTION (2 IMAGES)
# ==============================
async def process_two_meters(image1: str, image2: str):
    result1 = await process_single_image(image1)
    result2 = await process_single_image(image2)
    
    print(f"result1: {result1} and result2: {result2} ")

    return {
        "Meter 1": result1,
        "Meter 2": result2
    }

