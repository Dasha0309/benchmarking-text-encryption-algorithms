import speech_recognition as sr
from pydub import AudioSegment
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import time
import os

def get_transcript_from_file(file_path):
    # MP3 -> WAV хөрвүүлэх (Google API-д зориулж)
    if file_path.endswith(".mp3"):
        sound = AudioSegment.from_mp3(file_path)
        file_path = "converted.wav"
        sound.export(file_path, format="wav")
    
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio_data = recognizer.record(source)
        try:
            # Монгол хэлээр таних
            text = recognizer.recognize_google(audio_data, language="mn-MN")
            return text
        except Exception as e:
            print(f"Алдаа: {e}")
            return None

def run_aes128(data):
    key = os.urandom(16)  # 128 bit key
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    
    start_time = time.perf_counter()
    encrypted_data = cipher.encrypt(pad(data, AES.block_size))
    end_time = time.perf_counter()
    
    print(f"AES-128 Cost: {end_time - start_time:.8f} сек")
    return encrypted_data

# Транскрипт авах
transcript = get_transcript_from_file("test.mp3") or "Монгол хэлний ярианаас бичвэр буулгах системийн нууцлал."

# UTF-8 байт руу хөрвүүлэх
data_bytes = transcript.encode('utf-8')

# AES-128 шифрлэх
encrypted = run_aes128(data_bytes)
print(f"Шифрлэгдсэн өгөгдөл: {encrypted.hex()}")