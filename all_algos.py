# -*- coding: utf-8 -*-
"""
====================================================================
  Монгол хэлний STT + Шифрлэлтийн гүйцэтгэлийн харьцуулалт
  AES-128 | AES-256 | ChaCha20 | RSA-2048
  Туршилтын файлууд: 1 мин, 5 мин, 10 мин (.mp3)
====================================================================
"""

import builtins
import cProfile
import os
import secrets
import statistics
import sys
import time
import timeit
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import speech_recognition as sr
from Crypto.Cipher import AES, ChaCha20, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad
from memory_profiler import memory_usage
from pydub import AudioSegment

# ════════════════════════════════════════════════════════════════════
#  ТОХИРГОО
# ════════════════════════════════════════════════════════════════════

AUDIO_FILES = {
    "1min":  "Record_1min.mp3",
    "5min":  "Record_5min.mp3",
    "9min":  "Record_9min.mp3",
}

REPEATS = {
    "1min":  {"symmetric": 500, "rsa": 10},
    "5min":  {"symmetric": 100, "rsa": 5},
    "9min":  {"symmetric": 50, "rsa": 3},
}

# Google STT chunk хэмжээ (секунд) — 60с-ийн хязгаараас доогуур
STT_CHUNK_SEC = 60

OUTPUT_DIR = Path("benchmark_results")
OUTPUT_DIR.mkdir(exist_ok=True)

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
        sep  = kwargs.get("sep", " ")
        end  = kwargs.get("end", "\n")
        file = kwargs.get("file", sys.stdout)
        text = sep.join(str(a) for a in args) + end
        buf  = getattr(file, "buffer", None)
        if buf:
            buf.write(text.encode("utf-8", errors="replace"))
        else:
            file.write(text.encode("ascii", errors="replace").decode("ascii"))

configure_console_encoding()
print = safe_print

#  SPEECH-TO-TEXT  (chunk-based, Google STT 60с хязгаарт тохирсон)

def recognize_wav_chunk(wav_path: str, recognizer: sr.Recognizer) -> str:
    """Нэг WAV chunk-ийг Google STT (mn-MN)-ээр текст болгоно."""
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio_data, language="mn-MN")
        return text
    except sr.UnknownValueError:
        print("    [АНХААРУУЛГА] Энэ chunk-д ойлгомжтой дуу байсангүй.")
        return ""
    except sr.RequestError as e:
        print(f"    [АЛДАА] Google API: {e}")
        return ""
    except Exception as e:
        print(f"    [АЛДАА] {e}")
        return ""


def split_and_transcribe(file_path: str, chunk_sec: int = STT_CHUNK_SEC) -> str | None:
    """
    MP3 файлыг chunk_sec секундын хэсгүүдэд хувааж,
    тус бүрийг Google STT-д илгээн нэгтгэсэн транскрипт буцаана.

    Яагаад chunk болгодог вэ?
      - speech_recognition-ийн recognize_google() дотооддоо ~60с хязгаартай.
      - Урт аудио илгээхэд алдаа эсвэл хэсэгчилсэн үр дүн гардаг.
      - Chunk болгосноор урт файлыг найдвартай, бүрэн шилжүүлнэ.
    """
    if not os.path.exists(file_path):
        print(f"  [АЛДАА] '{file_path}' файл олдсонгүй.")
        return None

    print(f"  --> '{file_path}' уншиж байна...")
    audio     = AudioSegment.from_mp3(file_path)
    total_sec = len(audio) / 1000
    print(f"  --> Нийт хугацаа: {total_sec:.1f}с  "
          f"({total_sec/60:.2f} мин)  |  Chunk хэмжээ: {chunk_sec}с")

    chunk_ms      = chunk_sec * 1000
    recognizer    = sr.Recognizer()
    full_parts    = []
    total_chunks  = (len(audio) + chunk_ms - 1) // chunk_ms

    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk      = audio[start: start + chunk_ms]
        chunk_path = str(OUTPUT_DIR / f"_chunk_{i}.wav")
        chunk.export(chunk_path, format="wav")

        chunk_dur = len(chunk) / 1000
        print(f"  --> Chunk {i+1}/{total_chunks}  "
              f"({start/1000:.0f}с – {(start + len(chunk))/1000:.0f}с, "
              f"{chunk_dur:.1f}с)", end="  ")

        text = recognize_wav_chunk(chunk_path, recognizer)
        if text:
            print(f"✓  {len(text)} тэмдэгт")
        else:
            print("–  (хоосон)")

        full_parts.append(text)

        # Түр файл устгах
        try:
            os.remove(chunk_path)
        except OSError:
            pass

    transcript = " ".join(p for p in full_parts if p).strip()

    if not transcript:
        print("  [АЛДАА] Транскрипт бүрэн хоосон байна.")
        return None

    return transcript

#  ШИФРЛЭЛТИЙН АЛГОРИТМУУД
#  secrets.token_bytes() — urandom-аас аюулгүй, криптографийн түлхүүр


def run_aes128(data: bytes) -> bytes:
    key = secrets.token_bytes(16)
    iv  = secrets.token_bytes(16)
    return AES.new(key, AES.MODE_CBC, iv).encrypt(pad(data, AES.block_size))

def run_aes256(data: bytes) -> bytes:
    key = secrets.token_bytes(32)
    iv  = secrets.token_bytes(16)
    return AES.new(key, AES.MODE_CBC, iv).encrypt(pad(data, AES.block_size))

def run_chacha20(data: bytes) -> bytes:
    return ChaCha20.new(key=secrets.token_bytes(32)).encrypt(data)

def run_rsa2048(data: bytes) -> bytes:
    # RSA OAEP зөвхөн ~214 байт хүртэлх өгөгдөл шифрлэдэг
    return PKCS1_OAEP.new(RSA.generate(2048).publickey()).encrypt(data[:190])

def run_all(data: bytes) -> None:
    run_aes128(data)
    run_aes256(data)
    run_chacha20(data)
    run_rsa2048(data)

#  АРГА 1 — Олон давталт + статистик

def method1_statistics(algos: dict, data: bytes, sym_runs: int, rsa_runs: int) -> dict:
    print(f"\n[АРГА 1]  Олон давталт + статистик")
    print(f"  Симметр: {sym_runs} давталт  |  RSA: {rsa_runs} давталт")
    print(f"  {'Алгоритм':10}  {'Дундаж':>12}  {'Медиан':>12}  "
          f"{'Min':>12}  {'Max':>12}  {'Std':>12}")
    print("  " + "─" * 65)

    result = {}
    for name, (func, n) in algos.items():
        times = []
        for _ in range(n):
            t0 = time.perf_counter()
            func(data)
            times.append(time.perf_counter() - t0)

        dev = statistics.stdev(times) if len(times) > 1 else 0.0
        m   = statistics.mean(times)
        med = statistics.median(times)
        result[name] = {
            "mean": m, "median": med,
            "min":  min(times), "max": max(times),
            "stdev": dev, "n": n, "raw": times,
        }
        print(f"  {name:10}  {m:>12.8f}  {med:>12.8f}  "
              f"{min(times):>12.8f}  {max(times):>12.8f}  {dev:>12.8f}  сек")

    return result

#  АРГА 2 — timeit

def method2_timeit(algos: dict, data: bytes) -> dict:
    print(f"\n[АРГА 2]  timeit")
    print(f"  {'Алгоритм':10}  {'Нийт (с)':>12}  {'Дундаж (с)':>14}  {'Давталт':>8}")
    print("  " + "─" * 50)

    result = {}
    for name, (func, n) in algos.items():
        total = timeit.timeit(lambda f=func: f(data), number=n)
        result[name] = {"total": total, "mean": total / n, "n": n}
        print(f"  {name:10}  {total:>12.4f}  {total/n:>14.8f}  {n:>8}")

    return result

#  АРГА 3 — cProfile

def method3_cprofile(data: bytes) -> None:
    print(f"\n[АРГА 3]  cProfile (нэг дамжуулалт)")
    profiler = cProfile.Profile()
    profiler.enable()
    run_all(data)
    profiler.disable()
    profiler.print_stats(sort="cumulative")

#  АРГА 4 — Санах ойн хэрэглээ

def method4_memory(algos: dict, data: bytes) -> dict:
    print(f"\n[АРГА 4]  Санах ойн хэрэглээ (Memory Profiler)")
    print(f"  {'Алгоритм':10}  {'Дээд хэрэглээ (MiB)':>20}")
    print("  " + "─" * 34)

    result = {}
    for name, (func, _) in algos.items():
        try:
            mem = memory_usage(
                (func, (data,)),
                interval=0.0001, max_usage=True, multiprocess=False
            )
            val = mem[0] if isinstance(mem, list) else mem
            result[name] = val
            print(f"  {name:10}  {val:>20.4f}")
        except Exception as e:
            print(f"  {name:10}  хэмжих боломжгүй — {e}")
            result[name] = None

    return result

#  АРГА 5 — Өгөгдлийн хэмжээ vs Саатал

def method5_size_vs_latency(data: bytes, sym_runs: int) -> dict:
    print(f"\n[АРГА 5]  Өгөгдлийн хэмжээний нөлөө")
    half  = max(64, len(data) // 2)
    sizes = sorted(set([64, 256, 1_024, half, len(data)]))

    print(f"  {'Хэмжээ':>10}  {'AES-128 (с)':>14}  "
          f"{'AES-256 (с)':>14}  {'ChaCha20 (с)':>14}")
    print("  " + "─" * 58)

    result = {}
    for sz in sizes:
        if sz <= len(data):
            chunk = data[:sz]
        else:
            rep   = (sz // len(data)) + 1
            chunk = (data * rep)[:sz]

        t128 = timeit.timeit(lambda c=chunk: run_aes128(c),   number=sym_runs) / sym_runs
        t256 = timeit.timeit(lambda c=chunk: run_aes256(c),   number=sym_runs) / sym_runs
        tcha = timeit.timeit(lambda c=chunk: run_chacha20(c), number=sym_runs) / sym_runs
        result[sz] = {"aes128": t128, "aes256": t256, "chacha20": tcha}

        label = (f"{sz/1024:.0f}KB" if sz >= 1024 else f"{sz}B")
        print(f"  {label:>10}  {t128:>14.8f}  {t256:>14.8f}  {tcha:>14.8f}")

    return result

#  АРГА 6 — График (3-panel + нэгтгэсэн харьцуулалт)

def method6_plot(data: bytes, file_label: str, method1_result: dict) -> str:
    """
    3 самбар:
      (a) Хэмжилтийн тархалт — Box plot (Арга 1-ийн raw өгөгдлөөс)
      (b) Дундаж хугацаа     — Bar chart
      (c) Хэмжээ vs Хурд     — Line chart (1KB–бодит хэмжээ)
    """
    print(f"\n[АРГА 6]  График үүсгэж байна — {file_label}...")

    algorithms = ["AES-128", "AES-256", "ChaCha20", "RSA-2048"]
    colors     = ["#4CAF50", "#2196F3", "#FF9800", "#F44336"]

    raw_times = [method1_result[a]["raw"]  for a in algorithms]
    means     = [method1_result[a]["mean"] for a in algorithms]

    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    fig.suptitle(
        f"Шифрлэлтийн гүйцэтгэлийн benchmark — {file_label}  "
        f"({len(data)/1024:.1f} KB)",
        fontsize=14, fontweight="bold"
    )

    # ── (a) Box plot: тархалт ────────────────────────────────────
    bp = axes[0].boxplot(
        raw_times, labels=algorithms, patch_artist=True,
        medianprops=dict(color="black", linewidth=2),
    )
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    axes[0].set_title("Хэмжилтийн тархалт (Арга 1)", fontweight="bold")
    axes[0].set_ylabel("Секунд")
    axes[0].set_yscale("log")
    axes[0].grid(True, alpha=0.3, axis="y")

    # ── (b) Bar chart: дундаж ────────────────────────────────────
    bars = axes[1].bar(
        algorithms, means, color=colors,
        edgecolor="black", linewidth=0.6, alpha=0.85
    )
    for bar, val in zip(bars, means):
        axes[1].text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() * 1.05,
            f"{val*1000:.4f}мс",
            ha="center", va="bottom", fontsize=9, fontweight="bold"
        )
    axes[1].set_title("Дундаж хугацаа", fontweight="bold")
    axes[1].set_ylabel("Секунд")
    axes[1].set_yscale("log")
    axes[1].grid(True, alpha=0.3, axis="y")

    # ── (c) Хэмжээ vs Хурд (symmetric алгоритмууд) ───────────────
    sizes = sorted(set([
        1_024, 10_240, 102_400, 1_048_576, max(len(data), 1_048_576)
    ]))
    aes128_t, aes256_t, chacha_t = [], [], []

    print("  Хэмжээний туршилт ажиллаж байна...")
    for sz in sizes:
        if sz <= len(data):
            s = data[:sz]
        else:
            rep = (sz // len(data)) + 1
            s   = (data * rep)[:sz]

        n = 5 if sz >= 1_048_576 else 20
        aes128_t.append(timeit.timeit(lambda d=s: run_aes128(d),   number=n) / n)
        aes256_t.append(timeit.timeit(lambda d=s: run_aes256(d),   number=n) / n)
        chacha_t.append(timeit.timeit(lambda d=s: run_chacha20(d), number=n) / n)

    sizes_mb = [s / 1_048_576 for s in sizes]
    axes[2].plot(sizes_mb, aes128_t, "o-", color="#4CAF50", label="AES-128", linewidth=2)
    axes[2].plot(sizes_mb, aes256_t, "s-", color="#2196F3", label="AES-256", linewidth=2)
    axes[2].plot(sizes_mb, chacha_t, "^-", color="#FF9800", label="ChaCha20", linewidth=2)
    axes[2].set_title("Өгөгдлийн хэмжээ vs Хурд", fontweight="bold")
    axes[2].set_xlabel("Хэмжээ (MB)")
    axes[2].set_ylabel("Секунд")
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = str(OUTPUT_DIR / f"benchmark_{file_label}.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  График хадгалагдлаа: {out_path}")
    return out_path

#  НЭГТГЭСЭН ХАРЬЦУУЛАЛТЫН ГРАФИК (бүх файл хамтад)

def plot_combined_summary(all_results: dict) -> str:
    """
    Бүх туршилтын файлуудын дундаж хугацааг нэг графикт харьцуулна.
    """
    algorithms = ["AES-128", "AES-256", "ChaCha20", "RSA-2048"]
    labels     = list(all_results.keys())
    colors     = ["#4CAF50", "#2196F3", "#FF9800", "#F44336"]

    x     = np.arange(len(labels))
    width = 0.2

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle(
        "Нэгтгэсэн харьцуулалт — файл хугацаагаар (медиан, сек)",
        fontsize=14, fontweight="bold"
    )

    # ── (a) Бүх алгоритм хамтад (RSA орно) ─────────────────────
    for i, (algo, color) in enumerate(zip(algorithms, colors)):
        vals = [all_results[lbl]["method1"][algo]["median"] for lbl in labels]
        axes[0].bar(x + i * width, vals, width, label=algo,
                    color=color, edgecolor="black", linewidth=0.5, alpha=0.85)

    axes[0].set_title("Бүх алгоритм (log масштаб)", fontweight="bold")
    axes[0].set_xticks(x + width * 1.5)
    axes[0].set_xticklabels(labels)
    axes[0].set_ylabel("Медиан хугацаа (сек)")
    axes[0].set_yscale("log")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3, axis="y")

    # ── (b) Симметр алгоритмууд (RSA-гүй, тодорхой харагдана) ──
    sym_algos  = ["AES-128", "AES-256", "ChaCha20"]
    sym_colors = ["#4CAF50", "#2196F3", "#FF9800"]
    x2 = np.arange(len(labels))

    for i, (algo, color) in enumerate(zip(sym_algos, sym_colors)):
        vals = [all_results[lbl]["method1"][algo]["median"] for lbl in labels]
        axes[1].bar(x2 + i * width, vals, width, label=algo,
                    color=color, edgecolor="black", linewidth=0.5, alpha=0.85)

    axes[1].set_title("Симметр алгоритмууд (шугаман масштаб)", fontweight="bold")
    axes[1].set_xticks(x2 + width)
    axes[1].set_xticklabels(labels)
    axes[1].set_ylabel("Медиан хугацаа (сек)")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    out_path = str(OUTPUT_DIR / "benchmark_combined.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nНэгтгэсэн график хадгалагдлаа: {out_path}")
    return out_path

def benchmark_one_file(label: str, data: bytes,
                       sym_runs: int, rsa_runs: int) -> dict:
    print(f"\n{'═'*65}")
    print(f"  ФАЙЛ: {label}  |  Өгөгдлийн хэмжээ: {len(data):,} байт "
          f"({len(data)/1024:.1f} KB)")
    print(f"{'═'*65}")

    algos = {
        "AES-128":  (run_aes128,   sym_runs),
        "AES-256":  (run_aes256,   sym_runs),
        "ChaCha20": (run_chacha20, sym_runs),
        "RSA-2048": (run_rsa2048,  rsa_runs),
    }

    results = {}
    results["method1"] = method1_statistics(algos, data, sym_runs, rsa_runs)
    results["method2"] = method2_timeit(algos, data)
    method3_cprofile(data)
    results["method3"] = "stdout-д хэвлэгдсэн"
    results["method4"] = method4_memory(algos, data)
    results["method5"] = method5_size_vs_latency(data, sym_runs)
    results["method6"] = method6_plot(data, label, results["method1"])

    return results

# ════════════════════════════════════════════════════════════════════
#  НЭГТГЭСЭН ТЕКСТэн ТАЙЛАН
# ════════════════════════════════════════════════════════════════════

def print_summary(all_results: dict) -> None:
    algorithms = ["AES-128", "AES-256", "ChaCha20", "RSA-2048"]
    labels     = list(all_results.keys())

    print(f"\n{'═'*75}")
    print("  НЭГТГЭСЭН ТАЙЛАН — Медиан хугацаа (секунд)")
    print(f"{'═'*75}")

    header = f"  {'Алгоритм':12}" + "".join(f"{l:>18}" for l in labels)
    print(header)
    print("  " + "─" * (12 + 18 * len(labels)))

    for algo in algorithms:
        row = f"  {algo:12}"
        for lbl in labels:
            val = all_results[lbl]["method1"][algo]["median"]
            row += f"{val:>18.8f}"
        print(row)

    # Хурдны харьцаа (ChaCha20 / AES-128 харьцуулалт)
    print(f"\n  {'─'*55}")
    print("  Хурдны харьцаа (ChaCha20 / AES-128, медиан):")
    for lbl in labels:
        r = (all_results[lbl]["method1"]["AES-128"]["median"] /
             all_results[lbl]["method1"]["ChaCha20"]["median"])
        print(f"    {lbl:6}:  ChaCha20 нь AES-128-аас "
              f"{'хурдан' if r > 1 else 'удаан'}  "
              f"({abs(r):.2f}x)")

    print(f"\n  {'─'*55}")
    print("  RSA-2048 нь симметр алгоритмуудаас хэд дахин удаан (медиан):")
    for lbl in labels:
        base = all_results[lbl]["method1"]["AES-256"]["median"]
        rsa  = all_results[lbl]["method1"]["RSA-2048"]["median"]
        print(f"    {lbl:6}:  RSA-2048 нь AES-256-аас {rsa/base:.1f}x удаан")

# ════════════════════════════════════════════════════════════════════
#  ҮНДСЭН
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    all_results: dict = {}

    for label, filepath in AUDIO_FILES.items():
        print(f"\n{'#'*65}")
        print(f"  Аудио файл боловсруулж байна: {filepath}  [{label}]")
        print(f"{'#'*65}")

        # Chunk-based STT — 9мин файлыг найдвартай буулгана
        transcript = split_and_transcribe(filepath, chunk_sec=STT_CHUNK_SEC)

        if transcript is None:
            print(f"  [АЛГАСАВ] '{filepath}' транскрипт гаргаж чадсангүй.\n")
            continue

        data_bytes = transcript.encode("utf-8")
        print(f"\n  Benchmark өгөгдөл: {len(data_bytes):,} байт")

        all_results[label] = benchmark_one_file(
            label       = label,
            data        = data_bytes,
            sym_runs    = REPEATS[label]["symmetric"],
            rsa_runs    = REPEATS[label]["rsa"],
        )

    if all_results:
        print_summary(all_results)
        plot_combined_summary(all_results)
        print(f"\n{'#'*65}")
        print(f"  БҮРЭН ШИНЖИЛГЭЭ ДУУСЛАА.")
        print(f"  Графикууд: {OUTPUT_DIR}/  хавтаст хадгалагдлаа.")
        print(f"{'#'*65}")
    else:
        print("\n[АНХААРУУЛГА] Benchmark-д боловсруулах өгөгдөл байсангүй.")
