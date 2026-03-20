from pathlib import Path
import numpy as np
import soundfile as sf
import sherpa_onnx

root = Path(__file__).resolve().parent.parent
model_dir = root / "models" / "asr" / "sherpa" / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
wav = model_dir / "test_wavs" / "zh.wav"

samples, sample_rate = sf.read(str(wav), dtype="float32")

# 如果是多声道，转单声道
if samples.ndim == 2:
    samples = samples.mean(axis=1)

print("WAV:", wav)
print("sample_rate:", sample_rate)
print("shape:", samples.shape)
print("dtype:", samples.dtype)

recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
    model=str(model_dir / "model.int8.onnx"),
    tokens=str(model_dir / "tokens.txt"),
    num_threads=2,
    sample_rate=16000,
    feature_dim=80,
    decoding_method="greedy_search",
    debug=False,
    provider="cpu",
    language="auto",
    use_itn=True,
)

stream = recognizer.create_stream()
stream.accept_waveform(sample_rate, samples.tolist())
recognizer.decode_stream(stream)

print("TEXT:", stream.result.text)
