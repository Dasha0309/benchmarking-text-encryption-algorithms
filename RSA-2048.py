import speech_recognition as sr
from pydub import AudioSegment
from Crypto.Cipher import AES, ChaCha20, PKCS1_OAEP
from Crypto.PublicKey import RSA
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

def run_rsa2048(data):
    key = RSA.generate(2048)
    public_key = key.publickey()
    cipher = PKCS1_OAEP.new(public_key)

    # Текст хэт урт бол эхний 100 байтыг жишээ болгож хэмжье
    test_chunk = data[:100]

    start_time = time.perf_counter()
    encrypted_data = cipher.encrypt(test_chunk)
    end_time = time.perf_counter()

    print(f"RSA-2048 Cost (per small chunk): {end_time - start_time:.8f} сек")
    return encrypted_data

# ── Транскрипт авах ──────────────────────────────────
transcript = get_transcript_from_file("Record.mp3") or "Монгол хэлний ярианаас бичвэр буулгах системийн нууцлал."

print(f"Текст: {transcript}")
print("=" * 55)

data_bytes = transcript.encode('utf-8')


# RSA-2048
encrypted_rsa = run_rsa2048(data_bytes)
print(f"RSA-2048 Шифрлэгдсэн өгөгдөл: {encrypted_rsa.hex()}")
print("=" * 55)
