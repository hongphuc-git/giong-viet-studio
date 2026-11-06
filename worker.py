"""Generate narration with the same VieNeu CPU route as the original script."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time


def report(path: Path, message: str, percent: int) -> None:
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps({'status': 'running', 'message': message, 'percent': percent}, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('request', type=Path)
    args = parser.parse_args()
    config = json.loads(args.request.read_text(encoding='utf-8'))
    root = args.request.parents[2]
    state = args.request.with_name('progress.json')
    os.environ['HF_HOME'] = str(root / 'models')
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
    os.environ['PATH'] = str(root / 'bin') + os.pathsep + os.environ.get('PATH', '')
    import numpy as np
    import soundfile as sf
    from vieneu import Vieneu
    report(state, 'Đang nạp mô hình giọng đọc…', 3)
    tts = Vieneu(mode='v3turbo', backend='onnx', device='cpu', precision='int8', threads=6)
    paragraphs = [part.strip() for part in re.split(r'\n\s*\n', config['text']) if part.strip()]
    audio_parts: list[np.ndarray] = []
    started = time.monotonic()
    for index, paragraph in enumerate(paragraphs):
        report(state, f'Đang đọc đoạn {index + 1}/{len(paragraphs)}…', 5 + round(index / len(paragraphs) * 85))
        audio = tts.infer(text=paragraph, ref_audio=config['reference'], denoise=True, batch_size=1)
        if audio.size == 0 or not np.isfinite(audio).all():
            raise ValueError(f'Đoạn {index + 1} chưa tạo được âm thanh hợp lệ.')
        if audio_parts:
            audio_parts.append(np.zeros(round(config['pause'] * tts.sample_rate), dtype=np.float32))
        audio_parts.append(audio)
    raw = args.request.with_name('raw.wav')
    sf.write(str(raw), np.concatenate(audio_parts), tts.sample_rate, subtype='PCM_16')
    report(state, 'Đang cân âm lượng và xuất file…', 93)
    output = root / 'outputs' / config['output']
    command = [str(root / 'bin' / 'ffmpeg.exe'), '-hide_banner', '-loglevel', 'error', '-y', '-i', str(raw), '-af', f"atempo={config['speed']},loudnorm=I=-16:TP=-1.5:LRA=11,adelay=700:all=1,apad=pad_dur=1.4"]
    command += ['-c:a', 'libmp3lame', '-b:a', '192k'] if config['format'] == 'mp3' else ['-c:a', 'pcm_s16le']
    subprocess.run(command + [str(output)], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    duration = len(np.concatenate(audio_parts)) / tts.sample_rate / config['speed'] + 2.1
    result = {'status': 'completed', 'message': 'Đã tạo xong âm thanh', 'percent': 100, 'output': output.name, 'duration': duration, 'generation_seconds': round(time.monotonic() - started, 1)}
    temporary = state.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    temporary.replace(state)


if __name__ == '__main__':
    main()
