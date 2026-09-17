<div align="center">

# ⚡ Smart Electricity Monitoring System

**Automated meter reading, usage analytics, and client-ready WhatsApp reports — powered by AI.**

![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)
![Google%20Sheets](https://img.shields.io/badge/Google%20Sheets-API-34A853?style=flat-square&logo=google-sheets&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-3%20Flash-4285F4?style=flat-square&logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

[Features](#-features) · [Architecture](#-architecture) · [Tech Stack](#-tech-stack) · [Getting Started](#-getting-started) · [API](#-api-endpoints) · [License](#-license)

</div>

---

## 📖 Overview

Smart Electricity Monitoring System is a full-stack application designed for electricity distribution management. It automates the entire workflow — from capturing meter readings via photos to generating professional usage reports — using computer vision, large language models, and cloud spreadsheets.

**The Problem:** Manual meter reading is slow, error-prone, and makes it difficult to track group billing limits in real time.

**The Solution:** Upload two meter photos → AI reads the digits → validates against active meters → updates Google Sheets → generates a WhatsApp-ready report with usage forecasting and billing analysis.

<img width="1902" height="944" alt="smart" src="https://github.com/user-attachments/assets/77233e28-7a10-48e6-8f73-f00b69440520" />

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Dual Meter OCR** | Detects meter displays using Roboflow object detection and extracts decimal readings via Gemini Vision LLM |
| ✅ **Smart Validation** | Automatically maps photos to correct active meters, even when uploaded in wrong order. Fixes OCR decimal shift errors. |
| 📊 **Usage Forecasting** | Multi-interval smoothing for stable daily averages, per-meter predictions, and end-of-month group totals |
| 📱 **WhatsApp Reports** | Generates client-ready formatted reports with usage stats, billing analysis, and actionable recommendations |
| 📋 **Google Sheets Sync** | Reads/writes meter data to Google Sheets with color-coded row logging (odd/even date highlighting) |
| 🔗 **WhatsApp Integration** | Receive meter photos directly via WhatsApp webhook, process automatically, and reply with reports |
| 🎯 **Group Billing** | Tracks 4 meters in 2 groups with 380-unit monthly limits, predicts overages before they happen |
| 🖼️ **Modern Dashboard** | Clean React UI with drag-drop upload, real-time processing states, and one-click copy |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                              │
│                                                                     │
│   ┌──────────────┐    ┌──────────────────┐    ┌─────────────────┐  │
│   │  React App   │    │  WhatsApp Bot     │    │  Direct API     │  │
│   │  (Vite :5173)│    │  (Webhook)        │    │  (Postman)      │  │
│   └──────┬───────┘    └────────┬─────────┘    └────────┬────────┘  │
│          │                     │                       │            │
└──────────┼─────────────────────┼───────────────────────┼────────────┘
           │                     │                       │
           ▼                     ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND (:8000)                        │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    PROCESSING PIPELINE                        │  │
│  │                                                              │  │
│  │  ┌─────────┐   ┌──────────┐   ┌───────────┐   ┌─────────┐ │  │
│  │  │  Upload  │──▶│   OCR    │──▶│ Validation│──▶│ Analysis│ │  │
│  │  │  Images  │   │ Engine   │   │  + Map    │   │ + LLM   │ │  │
│  │  └─────────┘   └──────────┘   └───────────┘   └─────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────┐    ┌─────────────────────┐                │
│  │   Google Sheets API  │    │   Gemini LLM API     │                │
│  │   (Read / Write)     │    │   (Vision + Text)    │                │
│  └─────────────────────┘    └─────────────────────┘                │
│                                                                     │
│  ┌─────────────────────┐    ┌─────────────────────┐                │
│  │   Roboflow API       │    │   WhatsApp Business   │                │
│  │   (Object Detection) │    │   API (Messaging)     │                │
│  └─────────────────────┘    └─────────────────────┘                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Frontend

| Technology | Purpose |
|------------|---------|
| React 19 | UI framework |
| Vite 7 | Build tool & dev server |
| Lucide React | Icon library |
| CSS3 | Custom styling with gradients & glass effects |

### Backend

| Technology | Purpose |
|------------|---------|
| Python 3.11+ | Core language |
| FastAPI | REST API framework |
| OpenCV | Image processing |
| Roboflow | Meter display detection (object detection) |
| Google Gemini 3 Flash | Vision OCR + Report generation |
| Pydantic AI | LLM agent framework |
| gspread | Google Sheets integration |
| uvicorn | ASGI server |

### APIs & Services

| Service | Purpose |
|---------|---------|
| Google Sheets API | Meter data storage & history |
| Google Gemini API | OCR digit extraction & report generation |
| Roboflow API | Meter display bounding box detection |
| WhatsApp Business API | Client messaging & photo intake |

---

## 📁 Project Structure

```
Smart-Electricity-Monitoring-System/
│
├── backend/
│   ├── prototype.py          # FastAPI app — main entry point
│   ├── main_ocr.py           # OCR engine (Roboflow + Gemini Vision)
│   ├── validator.py          # Meter validation & mapping logic
│   ├── analysis.py           # Usage forecasting & report generation
│   ├── sheet.py              # Google Sheets read/write operations
│   ├── whatsp.py             # WhatsApp webhook handler
│   ├── test_ocr.py           # OCR test utility
│   ├── requirements.txt      # Python dependencies
│   ├── .env                  # Environment variables (API keys)
│   ├── credentials.json      # Google service account credentials
│   ├── temp_uploads/         # Temporary image storage
│   └── test_images/          # Sample meter images for testing
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Main React application
│   │   └── styles.css        # Custom styles
│   ├── index.html            # HTML entry point
│   ├── package.json          # Node.js dependencies
│   ├── vite.config.js        # Vite config with API proxy
│   └── dist/                 # Production build output
│
├── .vscode/                  # VS Code settings
├── run_commands.txt          # Quick reference for running the app
└── README.md                 # This file
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+** with [Conda](https://docs.conda.io/) or virtualenv
- **Node.js 18+** with npm
- **Google Cloud** service account with Sheets API enabled
- **Roboflow** API key
- **Google Gemini** API key

### 1. Clone the Repository

```bash
git clone https://github.com/burhan-ahmd/Smart-Electricity-Monitoring-System.git
cd Smart-Electricity-Monitoring-System
```

### 2. Backend Setup

```bash
cd backend

# Create and activate conda environment
conda create -n meter_env python=3.11
conda activate meter_env

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API keys
# Edit .env and add your Google API key:
#   GOOGLE_API_KEY=your_api_key_here

# Place your Google service account credentials
# Save as backend/credentials.json

# Start the backend server
python -m uvicorn prototype:app --host 127.0.0.1 --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev -- --port 5173
```

### 4. Open the App

Navigate to **http://127.0.0.1:5173** in your browser.

---

## ⚙️ Environment Variables

### Backend `.env`

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Google Gemini API key for LLM operations | ✅ |

### Backend `credentials.json`

Google service account credentials file for Sheets API access.
[Learn more](https://developers.google.com/workspace/guides/create-credentials#service-account)

### Frontend `.env`

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_BASE_URL` | Backend API base URL | `/api` (proxied via Vite) |

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check — returns service status |
| `POST` | `/process-meters` | Upload 2 meter images, process OCR, validate, update sheets, return report |
| `GET` | `/latest-report` | Generate and return the latest analysis report |

### `POST /process-meters`

**Request:** `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `image1` | File | First meter photo |
| `image2` | File | Second meter photo |

**Response:** Plain text — formatted WhatsApp report

### Example cURL

```bash
curl -X POST http://127.0.0.1:8000/process-meters \
  -F "image1=@meter1.jpg" \
  -F "image2=@meter2.jpg"
```

---

## 🔄 How It Works

```
Step 1: UPLOAD          Step 2: OCR              Step 3: VALIDATE
User uploads 2         Roboflow detects         System maps OCR
meter photos           display region,          values to correct
via UI or WhatsApp     Gemini reads digits      active meters
     │                      │                       │
     ▼                      ▼                       ▼
Step 4: CALCULATE       Step 5: UPDATE           Step 6: REPORT
Compute usage,          Write new readings       Gemini generates
daily averages,         to Google Sheets         formatted report
and predictions         with color coding        with analysis
```

### Group Billing System

| Group | Meters | Monthly Limit |
|-------|--------|---------------|
| **Group A** | Meter 1 (M. Ramzan) + Meter 2 (Imran Shabbir) | 380 units |
| **Group B** | Meter 3 (Burhan Ahmed) + Meter 4 (Irfan Shabbir) | 380 units |

- Each individual meter has a **190-unit** soft limit
- The system predicts when each meter will cross 190 units
- Group-level forecasting shows expected end-of-month totals
- Recommendations are generated when usage approaches limits

---

## 🧪 Testing

```bash
cd backend

# Run OCR test with sample images
python -c "import asyncio; from main_ocr import process_two_meters; print(asyncio.run(process_two_meters('test_images/1.jpeg', 'test_images/3.jpeg')))"

# Start test HTTP server for image viewing
python test_ocr.py
# Visit http://127.0.0.1:9080/test_images/
```

---

## 📱 WhatsApp Integration

The system includes a WhatsApp Business API webhook for receiving meter photos directly via chat:

1. User sends 2 meter photos to the configured WhatsApp number
2. System downloads and saves images
3. After receiving the second image, OCR pipeline runs automatically
4. Report is sent back to the user as a WhatsApp message

**Setup:** Configure `whatsp.py` with your Meta WhatsApp Business credentials.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ by [Burhan Ahmed](https://github.com/burhan-ahmd)**

</div>
