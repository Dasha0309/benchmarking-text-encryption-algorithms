import requests
import speech_recognition as sr
from pydub import AudioSegment
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import time
import os

CHIMEGE_TOKEN = "71f23379a67951cd63e81c29b320376af35bc8b12f6c9b7972c6dc374f1f50da"  

def convert_to_wav(file_path):
    """MP3 -> WAV хөрвүүлэх"""
    if file_path.endswith(".mp3"):
        sound = AudioSegment.from_mp3(file_path)
        wav_path = "converted.wav"
        sound.export(wav_path, format="wav")
        return wav_path
    return file_path

def get_transcript_chimege(file_path):
    """Chimege API ашиглан яриаг бичвэр болгох"""
    wav_path = convert_to_wav(file_path)
    
    with open(wav_path, 'rb') as f:
        audio_data = f.read()
    
    headers = {
        'Content-Type': 'application/octet-stream',
        'Token': CHIMEGE_TOKEN,
        'Punctuate': 'true',  
    }
    
    response = requests.post(
        "https://api.chimege.com/v1.2/transcribe",
        data=audio_data,
        headers=headers
    )
    
    if response.status_code == 200:
        return response.content.decode("utf-8")
    else:
        error_code = response.headers.get("Error-Code", "Unknown")
        print(f"Алдаа {response.status_code}, Error-Code: {error_code}")
        return None

def run_aes128(data):
    key = os.urandom(16)
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    
    start_time = time.perf_counter()
    encrypted_data = cipher.encrypt(pad(data, AES.block_size))
    end_time = time.perf_counter()
    
    print(f"AES-128 Cost: {end_time - start_time:.8f} сек")
    return encrypted_data

# Транскрипт авах
transcript = get_transcript_chimege("Record.mp3") or "Монгол хэлний ярианаас бичвэр буулгах системийн нууцлал."
print(f"Транскрипт: {transcript}")

# UTF-8 байт руу хөрвүүлэх
data_bytes = transcript.encode('utf-8')

# AES-128 шифрлэх
encrypted = run_aes128(data_bytes)
print(f"Шифрлэгдсэн өгөгдөл: {encrypted.hex()}")