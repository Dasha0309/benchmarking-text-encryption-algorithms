
# Оношлох код
from pydub import AudioSegment
from pydub.utils import mediainfo

# MP3 мэдээлэл харах
print("=== MP3 мэдээлэл ===")
print(mediainfo("Record.mp3"))

# WAV руу хөрвүүлэх
sound = AudioSegment.from_mp3("Record.mp3")
sound = sound.set_channels(1)
sound = sound.set_frame_rate(16000)
sound = sound.set_sample_width(2)
sound.export("converted.wav", format="wav")

# Хөрвөсөн WAV мэдээлэл харах
print("\n=== Хөрвөсөн WAV мэдээлэл ===")
print(mediainfo("converted.wav"))

# Хэмжээ харах
import os
print(f"\nMP3 хэмжээ: {os.path.getsize('Record.mp3') / 1024:.2f} KB")
print(f"WAV хэмжээ: {os.path.getsize('converted.wav') / 1024:.2f} KB")
