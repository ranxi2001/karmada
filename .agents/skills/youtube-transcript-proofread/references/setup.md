# Local Setup

## Recommended stack

- Python 3.10-3.12
- `yt-dlp`
- `faster-whisper`
- optional FFmpeg for media inspection or external clipping
- NVIDIA CUDA-capable GPU for `float16`, or CPU for `int8`

Create a dedicated environment:

```powershell
py -3.12 -m venv "$HOME/.codex/venvs/youtube-transcript-proofread"
& "$HOME/.codex/venvs/youtube-transcript-proofread/Scripts/python.exe" -m pip install --upgrade pip
& "$HOME/.codex/venvs/youtube-transcript-proofread/Scripts/python.exe" -m pip install yt-dlp faster-whisper
```

On Linux/macOS:

```bash
python3.12 -m venv ~/.codex/venvs/youtube-transcript-proofread
~/.codex/venvs/youtube-transcript-proofread/bin/python -m pip install --upgrade pip
~/.codex/venvs/youtube-transcript-proofread/bin/python -m pip install yt-dlp faster-whisper
```

The script finds `yt-dlp` next to the active Python interpreter when it is not on `PATH`.

## Model selection

| Need | Model | Device / compute type |
| --- | --- | --- |
| Technical Chinese/English meeting | `large-v3-turbo` | CUDA / `float16` |
| Maximum accuracy when time permits | `large-v3` | CUDA / `float16` |
| CPU preview | `small` or `medium` | CPU / `int8` |

Model names are resolved by `faster-whisper` and may trigger a one-time Hugging Face download. A local model directory can be passed instead. Verify the model card and license before redistributing weights; do not copy model files into a project repository.

## CUDA check

```powershell
python -c "import ctranslate2; print(ctranslate2.get_cuda_device_count())"
```

If CUDA initialization fails, rerun with `--device cpu --compute-type int8`. Do not silently claim GPU execution after a fallback.

## FFmpeg

The bundled transcription script downloads a directly decodable audio format and `faster-whisper` uses PyAV, so FFmpeg is not required for the normal path. Install FFmpeg when external probing, conversion, or waveform inspection is needed.

## Private or restricted videos

Do not automatically read browser cookies. Ask the user before using authenticated access, and avoid logging cookie values or tokens. This skill does not bypass access controls.
