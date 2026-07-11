from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import rembg
from PIL import Image
import io
import os
import subprocess
import time

app = FastAPI()

# Make sure an output directory exists
TEMP_DIR = "temp_audio"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.get("/")
def read_root():
    return {"status": "Hawkeye API is running"}

@app.post("/remove-bg")
async def remove_background(file: UploadFile = File(...)):
    try:
        image_data = await file.read()
        input_image = Image.open(io.BytesIO(image_data))
        output_image = rembg.remove(input_image)
        
        img_byte_arr = io.BytesIO()
        output_image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return StreamingResponse(img_byte_arr, media_type="image/png")
    except Exception as e:
        return {"error": str(e)}

@app.post("/tts")
async def generate_speech(text: str = Form(...), name: str = Form(...)):
    try:
        # File paths
        wav_path = os.path.join(TEMP_DIR, f"{name}.wav")
        m4a_path = os.path.join(TEMP_DIR, f"{name}.m4a")
        model_path = "hi_IN-priyamvada-medium.onnx"

        if not os.path.exists(model_path):
            raise HTTPException(status_code=500, detail="Voice model not found on server")

        # 1. Generate the .wav using Piper
        piper_cmd = f'echo "{text}" | ./piper/piper -m {model_path} -f {wav_path}'
        subprocess.run(piper_cmd, shell=True, check=True)

        # 2. Convert .wav to .m4a using ffmpeg (overwrites if exists)
        ffmpeg_cmd = f'ffmpeg -y -i {wav_path} -c:a aac -b:a 128k {m4a_path}'
        subprocess.run(ffmpeg_cmd, shell=True, check=True)

        # 3. Clean up the large .wav file to save server space
        if os.path.exists(wav_path):
            os.remove(wav_path)

        # Return the generated .m4a file
        return FileResponse(m4a_path, media_type="audio/mp4", filename=f"{name}.m4a")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
