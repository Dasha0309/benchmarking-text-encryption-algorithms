import speech_recognition as sr
from pydub import AudioSegment
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import time
import os

def get_transcript_from_file(file_path):
    if not os.path.exists(file_path):
        print(f"'{file_path}' файл олдсонгүй. Үндсэн текст ашиглана.")
        return None

    if file_path.endswith(".mp3"):
        sound = AudioSegment.from_mp3(file_path)
        file_path = "converted.wav"
        sound.export(file_path, format="wav")

    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio_data = recognizer.record(source)
        print(f"Audio файл амжилттай уншигдлаа: {file_path}")
        try:
            text = recognizer.recognize_google(audio_data, language="mn-MN")
            return text
        except Exception as e:
            print(f"Алдаа: {e}")
            return None
        
def run_aes256(data):
    key = os.urandom(32)  # 256 bit key
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)

    start_time = time.perf_counter()
    encrypted_data = cipher.encrypt(pad(data, AES.block_size))
    end_time = time.perf_counter()

    print(f"AES-256 Cost: {end_time - start_time:.8f} сек")
    return encrypted_data

# Транскрипт авах
transcript = get_transcript_from_file("Record.mp3") or "Монгол хэлний ярианаас бичвэр буулгах системийн нууцлал."

print(f"Текст: {transcript}")
print("-" * 50)

# UTF-8 байт руу хөрвүүлэх
data_bytes = transcript.encode('utf-8')

print("-" * 50)

# AES-256 шифрлэх
encrypted_256 = run_aes256(data_bytes)
print(f"AES-256 Шифрлэгдсэн өгөгдөл: {encrypted_256.hex()}")
