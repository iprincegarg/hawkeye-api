# Hawkeye API — Local Setup Guide

A FastAPI service exposing two endpoints:

| Endpoint | Description |
|---|---|
| `POST /remove-bg` | Removes image background using **rembg** |
| `POST /tts` | Converts text to Hindi speech (`.m4a`) via **Piper TTS** + **ffmpeg** |

---

## Prerequisites

Make sure the following are installed on your system before you begin.

| Tool | Install |
|---|---|
| **Python 3.10+** | [python.org](https://www.python.org/downloads/) |
| **pip** | Comes with Python |
| **ffmpeg** | See step below |
| **Linux / WSL** *(for Piper binary)* | Piper ships a Linux x86_64 binary |

> **Windows users:** The included `piper` binary is a Linux binary. Run the service inside **WSL 2** (Windows Subsystem for Linux) or a Linux VM/container. All commands below assume a Linux/WSL shell.

---

## Step 1 — Install ffmpeg

**Ubuntu / Debian / WSL:**
```bash
sudo apt update && sudo apt install -y ffmpeg
```

**Verify:**
```bash
ffmpeg -version
```

---

## Step 2 — Clone / Download the Project

If you downloaded the project as a folder, navigate into it:

```bash
cd /path/to/tts
```

Your project root should look like:

```
tts/
├── main.py
├── requirements.txt
├── hi_IN-priyamvada-medium.onnx
├── hi_IN-priyamvada-medium.onnx.json
└── piper/
    ├── piper              ← Linux binary
    ├── libonnxruntime.so.1.14.1
    ├── libespeak-ng.so.1.52.0.1
    ├── libpiper_phonemize.so.1.2.0
    └── espeak-ng-data/
```

---

## Step 3 — Create a Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Step 4 — Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note:** `rembg` downloads an AI model (~170 MB) on its **first run**. Ensure you have an internet connection and enough disk space.

---

## Step 5 — Make the Piper Binary Executable

```bash
chmod +x ./piper/piper
```

Verify it works:

```bash
./piper/piper --help
```

---

## Step 6 — Verify the Voice Model is Present

Confirm these two files exist in the project root:

```bash
ls -lh hi_IN-priyamvada-medium.onnx
ls -lh hi_IN-priyamvada-medium.onnx.json
```

Both files are required for the `/tts` endpoint.

---

## Step 7 — Run the API Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

Open your browser and visit: **http://localhost:8000**

Expected response:
```json
{"status": "Hawkeye API is running"}
```

---

## Using the Endpoints

### `/remove-bg` — Remove Image Background

**Method:** `POST`  
**Content-Type:** `multipart/form-data`

#### curl example
```bash
curl -X POST http://localhost:8000/remove-bg \
  -F "file=@/path/to/your/image.jpg" \
  --output result.png
```

The response is a **PNG image** with the background removed.

---

### `/tts` — Text-to-Speech (Hindi)

**Method:** `POST`  
**Content-Type:** `multipart/form-data`

| Field | Type | Description |
|---|---|---|
| `text` | string | The Hindi text to convert to speech |
| `name` | string | Output filename (without extension) |

#### curl example
```bash
curl -X POST http://localhost:8000/tts \
  -F "text=नमस्ते, आप कैसे हैं?" \
  -F "name=greeting" \
  --output greeting.m4a
```

The response is an **M4A audio file** (AAC, 128 kbps).

#### Swagger UI
You can also test both endpoints interactively at:  
**http://localhost:8000/docs**

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `piper: Permission denied` | Run `chmod +x ./piper/piper` |
| `ffmpeg: command not found` | Install ffmpeg: `sudo apt install -y ffmpeg` |
| `Voice model not found on server` | Ensure `hi_IN-priyamvada-medium.onnx` is in the project root |
| `rembg` slow on first request | It downloads the U2Net model (~170 MB) once — subsequent calls are fast |
| `error loading shared library` | Make sure you are on Linux/WSL; the piper binary is Linux x86_64 only |
| Port 8000 already in use | Change port: `uvicorn main:app --port 8001` |

---

## Project Structure

```
tts/
├── main.py                              # FastAPI application
├── requirements.txt                     # Python dependencies
├── hi_IN-priyamvada-medium.onnx        # Piper Hindi voice model
├── hi_IN-priyamvada-medium.onnx.json   # Model config
├── piper/                               # Piper TTS Linux binary + libs
│   ├── piper
│   ├── libonnxruntime.so.1.14.1
│   ├── libespeak-ng.so.1.52.0.1
│   ├── libpiper_phonemize.so.1.2.0
│   └── espeak-ng-data/
└── temp_audio/                          # Auto-created; stores generated audio
```

---

## Quick Reference

```bash
# 1. Activate environment
source venv/bin/activate

# 2. Start server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 3. Test remove-bg
curl -X POST http://localhost:8000/remove-bg -F "file=@photo.jpg" --output photo_no_bg.png

# 4. Test tts
curl -X POST http://localhost:8000/tts -F "text=नमस्ते" -F "name=hello" --output hello.m4a
```
