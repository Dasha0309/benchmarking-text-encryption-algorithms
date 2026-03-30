# -*- coding: utf-8 -*-
import builtins
import cProfile
import os
import statistics
import sys
import time
import timeit

import matplotlib.pyplot as plt
import numpy as np
import speech_recognition as sr
from Crypto.Cipher import AES, ChaCha20, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad
from memory_profiler import memory_usage
from pydub import AudioSegment

DEFAULT_AUDIO_FILE = "Record.mp3"
CONVERTED_WAV_FILE = "converted.wav"
DEFAULT_TRANSCRIPT = "Монгол хэлний ярианаас бичвэр буулгах системийн нууцлал."


def configure_console_encoding():
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except ValueError:
                pass


def safe_print(*args, **kwargs):
    try:
        builtins.print(*args, **kwargs)
    except UnicodeEncodeError:
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        file = kwargs.get("file", sys.stdout)
        flush = kwargs.get("flush", False)
        text = sep.join(str(arg) for arg in args) + end
        buffer = getattr(file, "buffer", None)
        if buffer is not None:
            buffer.write(text.encode("utf-8", errors="replace"))
        else:
            file.write(text.encode("ascii", errors="replace").decode("ascii"))
        if flush and hasattr(file, "flush"):
            file.flush()


configure_console_encoding()

# Route all output through Unicode-safe printing for Windows consoles.
print = safe_print


def get_transcript_from_file(file_path):
    if not os.path.exists(file_path):
        print(f"'{file_path}' file not found. Falling back to the default text.")
        return None

    source_path = file_path
    if file_path.lower().endswith(".mp3"):
        sound = AudioSegment.from_mp3(file_path)
        source_path = CONVERTED_WAV_FILE
        sound.export(source_path, format="wav")

    recognizer = sr.Recognizer()
    with sr.AudioFile(source_path) as source:
        audio_data = recognizer.record(source)

    try:
        return recognizer.recognize_google(audio_data, language="mn-MN")
    except sr.UnknownValueError:
        print("Speech recognition could not understand the audio. Falling back to the default text.")
    except sr.RequestError as error:
        print(f"Speech recognition request failed: {error}. Falling back to the default text.")
    except Exception as error:
        print(f"Unexpected transcription error: {error}. Falling back to the default text.")

    return None


def run_aes128(data):
    key = os.urandom(16)
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data, AES.block_size))

def run_aes256(data):
    key = os.urandom(32)
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data, AES.block_size))

def run_chacha20(data):
    key = os.urandom(32)
    cipher = ChaCha20.new(key=key)
    return cipher.encrypt(data)

def run_rsa2048(data):
    key = RSA.generate(2048)
    cipher = PKCS1_OAEP.new(key.publickey())
    return cipher.encrypt(data[:100])

def run_all(data):
    run_aes128(data)
    run_aes256(data)
    run_chacha20(data)
    run_rsa2048(data)


def method1_statistics(data, runs=500):
    print("\n" + "=" * 60)
    print("АРГА 1: Олон давталт + статистик шинжилгээ")
    print("=" * 60)

    algorithms = {
        "AES-128": run_aes128,
        "AES-256": run_aes256,
        "ChaCha20": run_chacha20,
        "RSA-2048": run_rsa2048,
    }

    for name, func in algorithms.items():
        iterations = 10 if name == "RSA-2048" else runs
        times = []

        for _ in range(iterations):
            start = time.perf_counter()
            func(data)
            end = time.perf_counter()
            times.append(end - start)

        deviation = statistics.stdev(times) if len(times) > 1 else 0.0
        print(f"\n  [{name}] ({iterations} давталт)")
        print(f"    Дундаж:           {statistics.mean(times):.8f} сек")
        print(f"    Медиан:           {statistics.median(times):.8f} сек")
        print(f"    Хамгийн бага:     {min(times):.8f} сек")
        print(f"    Хамгийн их:       {max(times):.8f} сек")
        print(f"    Стандарт хазайлт: {deviation:.8f} сек")


def method2_timeit(data, runs=500):
    print("\n" + "=" * 60)
    print("АРГА 2: timeit хэмжилт")
    print("=" * 60)

    aes128_total = timeit.timeit(lambda: run_aes128(data), number=runs)
    aes256_total = timeit.timeit(lambda: run_aes256(data), number=runs)
    chacha_total = timeit.timeit(lambda: run_chacha20(data), number=runs)
    rsa_total = timeit.timeit(lambda: run_rsa2048(data), number=10)

    print(f"  AES-128  ({runs} удаа): нийт {aes128_total:.4f}s -> дундаж {aes128_total / runs:.8f}s")
    print(f"  AES-256  ({runs} удаа): нийт {aes256_total:.4f}s -> дундаж {aes256_total / runs:.8f}s")
    print(f"  ChaCha20 ({runs} удаа): нийт {chacha_total:.4f}s -> дундаж {chacha_total / runs:.8f}s")
    print(f"  RSA-2048 (10  удаа):   нийт {rsa_total:.4f}s -> дундаж {rsa_total / 10:.8f}s")


def method3_cprofile(data):
    print("\n" + "=" * 60)
    print("АРГА 3: cProfile - функц бүрийн задаргаа")
    print("=" * 60)

    profiler = cProfile.Profile()
    profiler.enable()
    run_all(data)
    profiler.disable()
    profiler.print_stats(sort="cumulative")


def method4_memory(data):
    print("\n" + "=" * 60)
    print("АРГА 4: Санах ойн хэрэглээ (memory_profiler)")
    print("=" * 60)

    algorithms = {
        "AES-128": lambda: run_aes128(data),
        "AES-256": lambda: run_aes256(data),
        "ChaCha20": lambda: run_chacha20(data),
        "RSA-2048": lambda: run_rsa2048(data),
    }

    for name, func in algorithms.items():
        try:
            mem = memory_usage(func, interval=0.0001, max_usage=True, multiprocess=False)
            print(f"  {name:10}: {mem:.4f} MiB")
        except (PermissionError, OSError) as error:
            print(f"  Memory profiling is unavailable in this environment: {error}")
            return


def method5_by_size(sizes=None):
    if sizes is None:
        sizes = [64, 256, 1024, 4096, 16384]

    print("\n" + "=" * 60)
    print("АРГА 5: Өгөгдлийн хэмжээгээр харьцуулах")
    print("=" * 60)
    print(f"  {'Хэмжээ':>8} | {'AES-128':>12} | {'AES-256':>12} | {'ChaCha20':>12}")
    print("  " + "-" * 52)

    for size in sizes:
        data = os.urandom(size)
        aes128_avg = timeit.timeit(lambda: run_aes128(data), number=200) / 200
        aes256_avg = timeit.timeit(lambda: run_aes256(data), number=200) / 200
        chacha_avg = timeit.timeit(lambda: run_chacha20(data), number=200) / 200
        print(f"  {size:>6}B  | {aes128_avg:>12.8f} | {aes256_avg:>12.8f} | {chacha_avg:>12.8f}")


def method6_plot(data, runs=300):
    print("\n" + "=" * 60)
    print("АРГА 6: Matplotlib харагдац")
    print("=" * 60)

    algorithms = {
        "AES-128": run_aes128,
        "AES-256": run_aes256,
        "ChaCha20": run_chacha20,
        "RSA-2048": run_rsa2048,
    }

    results = {}
    for name, func in algorithms.items():
        iterations = 10 if name == "RSA-2048" else runs
        times = []

        for _ in range(iterations):
            start = time.perf_counter()
            func(data)
            end = time.perf_counter()
            times.append(end - start)

        results[name] = times

    colors = ["#4CAF50", "#2196F3", "#FF9800", "#F44336"]
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle("Шифрлэлтийн алгоритмуудын benchmark харьцуулалт", fontsize=14)

    axes[0].boxplot(results.values(), tick_labels=results.keys(), patch_artist=True, boxprops=dict(facecolor="#E3F2FD"))
    axes[0].set_title("Хугацааны тархалт")
    axes[0].set_ylabel("Секунд")
    axes[0].set_yscale("log")
    axes[0].grid(True, alpha=0.3)

    means = [np.mean(values) for values in results.values()]
    bars = axes[1].bar(results.keys(), means, color=colors, edgecolor="black", linewidth=0.5)
    axes[1].set_title("Дундаж хугацаа")
    axes[1].set_ylabel("Секунд")
    axes[1].set_yscale("log")
    axes[1].grid(True, alpha=0.3, axis="y")

    for bar, value in zip(bars, means):
        axes[1].text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.6f}s",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    sizes = [64, 256, 1024, 4096, 16384]
    aes128_by_size = []
    aes256_by_size = []
    chacha_by_size = []

    for size in sizes:
        sample = os.urandom(size)
        aes128_by_size.append(timeit.timeit(lambda: run_aes128(sample), number=100) / 100)
        aes256_by_size.append(timeit.timeit(lambda: run_aes256(sample), number=100) / 100)
        chacha_by_size.append(timeit.timeit(lambda: run_chacha20(sample), number=100) / 100)

    axes[2].plot(sizes, aes128_by_size, "o-", color="#4CAF50", label="AES-128")
    axes[2].plot(sizes, aes256_by_size, "s-", color="#2196F3", label="AES-256")
    axes[2].plot(sizes, chacha_by_size, "^-", color="#FF9800", label="ChaCha20")
    axes[2].set_title("Өгөгдлийн хэмжээ vs хурд")
    axes[2].set_xlabel("Байт")
    axes[2].set_ylabel("Секунд")
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("benchmark_result.png", dpi=150)
    if "agg" not in plt.get_backend().lower():
        plt.show()
    plt.close(fig)
    print("График хадгалагдлаа: benchmark_result.png")


if __name__ == "__main__":
    transcript = get_transcript_from_file(DEFAULT_AUDIO_FILE) or DEFAULT_TRANSCRIPT
    print(f"\nТекст: {transcript}")

    data_bytes = transcript.encode("utf-8")
    method1_statistics(data_bytes)
    method2_timeit(data_bytes)
    method3_cprofile(data_bytes)
    method4_memory(data_bytes)
    method5_by_size()
    method6_plot(data_bytes)
