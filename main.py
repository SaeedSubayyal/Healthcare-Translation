from fastapi import FastAPI, UploadFile, Form, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from openai import OpenAI
from gtts import gTTS
from cryptography.fernet import Fernet
import tempfile
import os
import logging
import json
from datetime import datetime
from typing import Optional
import hashlib

app = FastAPI()

# Security Configuration
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")
api_keys = {"Fstky2e4mdt3_"}  # Store securely in production

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Logging with PHI considerations
class PHISanitizer:
    @staticmethod
    def sanitize(text):
        # Implement PHI detection and redaction
        return text

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("healthcare_translation")

# Initialize OpenAI
openai_client = OpenAI(api_key=os.getenv("REACT_APP_Open_AI_key"))

# Encryption setup
encryption_key = Fernet.generate_key()
cipher = Fernet(encryption_key)

# Medical terminology enhancement
MEDICAL_CONTEXT = """
You are processing healthcare communication. Pay special attention to:
- Medical terminology and abbreviations
- Symptoms and conditions
- Treatment descriptions
- Medication names
- Dosage instructions
Maintain high accuracy while preserving the original medical meaning.
"""

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if api_key not in api_keys:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@app.post("/speech-to-text/")
async def speech_to_text(
    audio: UploadFile,
    api_key: str = Depends(verify_api_key)
):
    try:
        # Secure file handling
        audio_path = tempfile.NamedTemporaryFile(delete=False).name
        with open(audio_path, "wb") as f:
            content = await audio.read()
            f.write(content)
        
        # Use OpenAI Whisper with medical context
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=open(audio_path, "rb"),
            prompt=MEDICAL_CONTEXT
        )
        
        os.remove(audio_path)
        
        # Enhanced medical term processing
        enhanced_transcript = await enhance_medical_terms(transcript.text)
        
        return JSONResponse({
            "success": True,
            "transcription": enhanced_transcript
        })
    except Exception as e:
        logger.error(f"Speech-to-text error: {PHISanitizer.sanitize(str(e))}")
        raise HTTPException(status_code=500, detail="Speech-to-text processing failed")

async def enhance_medical_terms(text: str) -> str:
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": MEDICAL_CONTEXT},
                {"role": "user", "content": f"Enhance medical accuracy: {text}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Medical term enhancement error: {str(e)}")
        return text

@app.post("/translate/")
async def translate_text(
    text: str = Form(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    api_key: str = Depends(verify_api_key)
):
    try:
        # Use GPT for medical-aware translation
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"{MEDICAL_CONTEXT}\nTranslate from {source_lang} to {target_lang} maintaining medical accuracy."},
                {"role": "user", "content": text}
            ]
        )
        
        translated_text = response.choices[0].message.content
        
        # Generate audio with encryption
        audio_file = await generate_secure_audio(translated_text, target_lang)
        
        return JSONResponse({
            "success": True,
            "translated_text": translated_text,
            "audio_path": audio_file
        })
    except Exception as e:
        logger.error(f"Translation error: {PHISanitizer.sanitize(str(e))}")
        raise HTTPException(status_code=500, detail="Translation failed")

async def generate_secure_audio(text: str, lang: str) -> str:
    try:
        tts = gTTS(text, lang=lang)
        audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        tts.save(audio_file)
        
        # Encrypt audio
        with open(audio_file, "rb") as file:
            encrypted_data = cipher.encrypt(file.read())
        with open(audio_file, "wb") as file:
            file.write(encrypted_data)
            
        return audio_file
    except Exception as e:
        logger.error(f"Audio generation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Audio generation failed")

# Add health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
