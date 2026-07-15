from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import rembg
import requests
import edge_tts
from PIL import Image
import io
import os
import subprocess
import time
import nltk
from deep_translator import GoogleTranslator
from pydantic import BaseModel
app = FastAPI()

# Make sure an output directory exists
TEMP_DIR = "temp_audio"
os.makedirs(TEMP_DIR, exist_ok=True)

# Mount the temp_audio directory so files can be accessed via URL
app.mount("/temp_audio", StaticFiles(directory=TEMP_DIR), name="temp_audio")

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

class TranslationRequest(BaseModel):
    text: str

# Initialize NLTK safely
nltk_initialized = False
def init_nltk():
    global nltk_initialized
    if not nltk_initialized:
        try:
            nltk.data.find('tokenizers/punkt_tab')
            nltk.data.find('taggers/averaged_perceptron_tagger_eng')
        except LookupError:
            print("Downloading NLTK models...")
            nltk.download('punkt_tab')
            nltk.download('averaged_perceptron_tagger_eng')
        nltk_initialized = True

def transliterate_en_to_hi(word: str) -> str:
    try:
        url = f"https://inputtools.google.com/request?text={word}&itc=hi-t-i0-und&num=1&cp=0&cs=1&ie=utf-8&oe=utf-8"
        response = requests.get(url)
        data = response.json()
        if data[0] == 'SUCCESS':
            return data[1][0][1][0]
    except Exception:
        pass
    return word

@app.post("/translate-hinglish")
async def translate_to_hinglish(request: TranslationRequest):
    try:
        init_nltk()
        tokens = nltk.word_tokenize(request.text)
        tagged = nltk.pos_tag(tokens)
        
        placeholders = {}
        new_string = ""
        
        for word, tag in tagged:
            # NNP: Proper noun, NN: Noun, NNS: Noun plural, NNPS: Proper noun plural
            if tag in ['NN', 'NNS', 'NNP', 'NNPS']:
                ph = f" x{len(placeholders)}x "
                placeholders[ph.strip()] = word
                new_string += ph
            else:
                new_string += word + " "
                
        translator = GoogleTranslator(source='en', target='hi')
        translated = translator.translate(new_string)
        
        for ph, orig_word in placeholders.items():
            translated = translated.replace(ph, orig_word)
            
        return {"hinglish": translated, "original": request.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/new-tts")
async def generate_speech_edge(request: Request, text: str = Form(...), name: str = Form(...)):
    try:
        # File paths
        mp3_path = os.path.join(TEMP_DIR, f"{name}.mp3")
        m4a_path = os.path.join(TEMP_DIR, f"{name}.m4a")

        # Voice: hi-IN-SwaraNeural (female) or hi-IN-MadhurNeural (male)
        voice = "hi-IN-SwaraNeural"
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(mp3_path)
        
        # Convert .mp3 to .m4a using ffmpeg (overwrites if exists)
        ffmpeg_cmd = f'ffmpeg -y -i "{mp3_path}" -c:a aac -b:a 128k "{m4a_path}"'
        subprocess.run(ffmpeg_cmd, shell=True, check=True)

        # Clean up the temporary .mp3 file
        if os.path.exists(mp3_path):
            os.remove(mp3_path)
        
        # Get full absolute path
        full_local_path = os.path.abspath(m4a_path)
        
        # Construct the URL to the file
        base_url = str(request.base_url)
        file_url = f"{base_url}temp_audio/{name}.m4a"
        
        return {
            "message": "Audio generated successfully",
            "local_path": full_local_path,
            "url": file_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class DeleteMediaRequest(BaseModel):
    url: str

@app.post("/delete-media")
async def delete_media(request: DeleteMediaRequest):
    try:
        from urllib.parse import urlparse
        parsed_url = urlparse(request.url)
        path = parsed_url.path
        
        if not path.startswith("/temp_audio/"):
            raise HTTPException(status_code=400, detail="Invalid media URL")
            
        filename = path.replace("/temp_audio/", "")
        
        if "/" in filename or "\\" in filename or ".." in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
            
        file_path = os.path.join(TEMP_DIR, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return {"message": "File deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
