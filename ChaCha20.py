import speech_recognition as sr
from pydub import AudioSegment
from Crypto.Cipher import AES, ChaCha20
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
        try:
            text = recognizer.recognize_google(audio_data, language="mn-MN")
            return text
        except Exception as e:
            print(f"Алдаа: {e}")
            return None

def run_chacha20(data):
    key = os.urandom(32)  # 256 bit key
    cipher = ChaCha20.new(key=key)

    start_time = time.perf_counter()
    encrypted_data = cipher.encrypt(data)
    end_time = time.perf_counter()

    print(f"ChaCha20 Cost: {end_time - start_time:.8f} сек")
    return encrypted_data

# Транскрипт авах
transcript = get_transcript_from_file("Record.mp3") or "Монгол хэлний ярианаас бичвэр буулгах системийн нууцлал."

print(f"Текст: {transcript}")
print("=" * 50)

# UTF-8 байт руу хөрвүүлэх
data_bytes = transcript.encode('utf-8')

# ChaCha20 шифрлэх
encrypted_chacha = run_chacha20(data_bytes)
print(f"ChaCha20 Шифрлэгдсэн өгөгдөл: {encrypted_chacha.hex()}")
print("=" * 50)
