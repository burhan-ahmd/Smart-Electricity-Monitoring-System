from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

import httpx
import asyncio
import os

from datetime import datetime
from collections import defaultdict

# =========================================================
# IMPORT MAIN OCR ENGINE
# This function will come from prototype.py later
# =========================================================
from prototype import process_meter_paths


# =========================================================
# FASTAPI APP
# =========================================================
app = FastAPI()


# =========================================================
# WHATSAPP CONFIG
# =========================================================
VERIFY_TOKEN = "my_custom_verify_token"  # set same in Meta dev portal
WHATSAPP_TOKEN = "EAAV2f979RF0BRgZCHfieCYyY7YuPuXdDj1Lc7k8LknTqu9V6qIQI5JERPctRiSZAUywKqZASKONBRAh3wEFZAuFwxoESlXguQAJII2v3yz6LOEgi9PaLj6sZB4v0w94KjqosR8hIEdLgOwIveOJioGhMZCIZAsSWjAZABthxGxqe0YcHZClo0ncC9y6thHAU2gAZDZD"  # your Meta access token
PHONE_NUMBER_ID = "1096629463540487" # 03334530105
# PHONE_NUMBER_ID = "1149603001567952" # 03204343279


# =========================================================
# GLOBAL HTTP CLIENT
# Reused connection = faster performance
# =========================================================
client = httpx.AsyncClient(timeout=120.0)


# =========================================================
# IMAGE STORAGE FOLDER
# =========================================================
IMAGE_DIR = "received_images"

os.makedirs(IMAGE_DIR, exist_ok=True)


# =========================================================
# TEMP USER IMAGE STORAGE
#
# Example:
# {
#   "923001112222": [
#       "received_images/img1.jpg",
#       "received_images/img2.jpg"
#   ]
# }
# =========================================================
user_image_buffer = defaultdict(list)


# =========================================================
# USERS CURRENTLY PROCESSING
#
# Prevent duplicate OCR runs
# =========================================================
processing_users = set()


# =========================================================
# MIDDLEWARE
#
# Removes ngrok browser warning issue
# =========================================================
@app.middleware("http")
async def add_ngrok_header(request: Request, call_next):

    response = await call_next(request)

    response.headers["ngrok-skip-browser-warning"] = "true"

    return response


# =========================================================
# WEBHOOK VERIFICATION
#
# Meta calls this once while verifying webhook
# =========================================================
@app.get("/webhook")
async def verify_webhook(request: Request):

    params = request.query_params

    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge)

    return PlainTextResponse(
        content="Invalid token",
        status_code=403
    )


# =========================================================
# MARK MESSAGE AS READ
# =========================================================
async def mark_as_read(message_id: str):

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }

    try:

        await client.post(
            f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages",
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            },
            json=payload
        )

    except Exception as e:
        print("⚠️ mark_as_read failed:", e)


# =========================================================
# SHOW TYPING INDICATOR
#
# Shows "typing..." in WhatsApp
# =========================================================
async def show_typing(message_id: str):

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
        "typing_indicator": {
            "type": "text"
        }
    }

    try:

        await client.post(
            f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages",
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            },
            json=payload
        )

    except Exception as e:
        print("⚠️ typing indicator failed:", e)


# =========================================================
# SEND WHATSAPP MESSAGE
# =========================================================
async def send_whatsapp_message(to: str, text: str):

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {
            "body": text
        }
    }

    try:

        await client.post(
            f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages",
            json=payload,
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            }
        )

    except Exception as e:
        print("❌ send message failed:", e)


# =========================================================
# GET MEDIA DOWNLOAD URL
#
# WhatsApp does NOT directly send image file.
# First we request image URL from Meta servers.
# =========================================================
async def get_media_url(media_id: str):

    url = f"https://graph.facebook.com/v23.0/{media_id}"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}"
    }

    response = await client.get(url, headers=headers)

    data = response.json()

    return data["url"]


# =========================================================
# DOWNLOAD IMAGE BY URL
# =========================================================
async def download_media(media_url: str):

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}"
    }

    response = await client.get(media_url, headers=headers)

    return await response.aread()


# =========================================================
# SAVE IMAGE TO LOCAL STORAGE
# =========================================================
def save_image(image_bytes: bytes, sender: str):

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{sender}_{timestamp}.jpg"

    path = os.path.join(IMAGE_DIR, filename)

    with open(path, "wb") as f:
        f.write(image_bytes)

    return path


# =========================================================
# MAIN OCR PIPELINE
#
# Runs ONLY after receiving 2 images
# =========================================================
async def run_meter_pipeline(
    sender: str,
    image1: str,
    image2: str
):

    try:

        print("🚀 Starting OCR pipeline...")

        # =================================================
        # CALL MAIN OCR ENGINE
        # This comes from prototype.py
        # =================================================
        report_text = await process_meter_paths(
            image1,
            image2
        )

        print("✅ Report generated")

        # =================================================
        # SEND FINAL REPORT TO USER
        # =================================================
        await send_whatsapp_message(
            sender,
            report_text
        )

        print("📤 Final report sent")

    except Exception as e:

        print("❌ OCR pipeline failed:", e)

        await send_whatsapp_message(
            sender,
            f"❌ Error while generating report:\n{str(e)}"
        )

    finally:

        # Remove user from processing set
        processing_users.discard(sender)


# =========================================================
# PROCESS IMAGE MESSAGE
#
# 1. Download image
# 2. Save image
# 3. Store image path
# 4. Wait for second image
# 5. Start OCR
# =========================================================
async def process_image(
    media_id: str,
    sender: str,
    message_id: str
):

    try:

        # =================================================
        # STEP 1: GET IMAGE URL
        # =================================================
        media_url = await get_media_url(media_id)

        print("✅ Media URL received")

        # =================================================
        # STEP 2: DOWNLOAD IMAGE
        # =================================================
        image_bytes = await download_media(media_url)

        print("✅ Image downloaded")

        # =================================================
        # STEP 3: SAVE IMAGE LOCALLY
        # =================================================
        saved_path = save_image(image_bytes, sender)

        print(f"🖼️ Image saved: {saved_path}")

        # =================================================
        # STEP 4: STORE USER IMAGE
        # =================================================
        user_image_buffer[sender].append(saved_path)

        total_images = len(user_image_buffer[sender])

        print(f"📦 User now has {total_images} image(s)")

        # =================================================
        # WAIT UNTIL USER SENDS 2 IMAGES
        # =================================================
        if total_images < 2:
            print("⏳ Waiting for second image...")
            return

        # =================================================
        # PREVENT DUPLICATE PROCESSING
        # =================================================
        if sender in processing_users:
            print("⚠️ User already processing")
            return

        processing_users.add(sender)

        # =================================================
        # TAKE FIRST 2 IMAGES
        # =================================================
        image1, image2 = user_image_buffer[sender][:2]

        # =================================================
        # CLEAR USER BUFFER
        # =================================================
        user_image_buffer[sender] = []

        # =================================================
        # SHOW TYPING INDICATOR
        # =================================================
        await show_typing(message_id)

        await asyncio.sleep(1)

        # =================================================
        # SEND WAIT MESSAGE
        # =================================================
        await send_whatsapp_message(
            sender,
            "Thanks for sharing both images, now kindly wait, we are generating your report."
        )

        # =================================================
        # START OCR PIPELINE IN BACKGROUND
        #
        # NON-BLOCKING = FAST
        # =================================================
        asyncio.create_task(
            run_meter_pipeline(
                sender,
                image1,
                image2
            )
        )

    except Exception as e:
        print("❌ process_image failed:", e)


# =========================================================
# MAIN WEBHOOK
#
# Receives ALL WhatsApp messages
# =========================================================
@app.post("/webhook")
async def receive_message(req: Request):

    data = await req.json()

    print("📩 Incoming Webhook:\n", data)

    try:

        value = data["entry"][0]["changes"][0]["value"]

        # =================================================
        # Ignore status updates
        # =================================================
        if "messages" not in value:
            return {"status": "ignored"}

        # =================================================
        # GET MESSAGE OBJECT
        # =================================================
        msg = value["messages"][0]

        msg_type = msg["type"]

        sender = msg["from"]

        message_id = msg["id"]

        print(f"📨 {msg_type} message from {sender}")

        # =================================================
        # MARK MESSAGE AS READ
        # =================================================
        asyncio.create_task(
            mark_as_read(message_id)
        )

        # =================================================
        # TEXT MESSAGE
        # =================================================
        if msg_type == "text":

            text = msg["text"]["body"]

            print(f"💬 Text: {text}")

            # typing effect
            await show_typing(message_id)

            await asyncio.sleep(1)

            # demo reply
            await send_whatsapp_message(
                sender,
                f"You said:\n{text}"
            )

        # =================================================
        # IMAGE MESSAGE
        # =================================================
        elif msg_type == "image":

            media_id = msg["image"]["id"]

            print("🖼️ Image received")

            # =================================================
            # PROCESS IMAGE IN BACKGROUND
            #
            # NON-BLOCKING
            # =================================================
            asyncio.create_task(
                process_image(
                    media_id,
                    sender,
                    message_id
                )
            )

        # =================================================
        # OTHER MESSAGE TYPES
        # =================================================
        else:

            print(f"⚠️ Unsupported message type: {msg_type}")

        return {
            "status": "ok"
        }

    except Exception as e:

        print("❌ Webhook Error:", e)

        return {
            "status": "error",
            "details": str(e)
        }