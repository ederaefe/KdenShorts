# Technical Documentation: KdenShorts for Kdenlive

> Repository: https://github.com/ederaefe/KdenShorts

A robust, GPU-free command-line automation tool designed for Windows that converts long-form recordings (sermons, podcasts, keynote speeches) into pre-cut 9:16 vertical video projects ready for Kdenlive.

---

## 1. System Architecture

```
                       +---------------------------+
                       |   Source Media (.mp4)     |
                       +-------------+-------------+
                                     |
                       [ffprobe: FPS, Duration, Dim]
                                     |
                      [ffmpeg: Audio Extraction]
                      (16kHz mono MP3, 128 kbps)
                                     |
                     [ffmpeg: 20-Minute Segmenting]
                                     |
                +--------------------+--------------------+
                |                    |                    |
          [Chunk 0: 00:00]     [Chunk 1: 20:00]     [Chunk 2: 40:00]
                |                    |                    |
                +--------------------+--------------------+
                                     |
                        [Gemini Files API Upload]
                                     |
                        [State Polling: ACTIVE]
                                     |
                        [Single-Pass Structured Prompt]
                        (Transcript + Hook Extraction)
                                     |
                        [Pydantic Schema Validation]
                        (Offset-Adjusted Timestamps)
                                     |
                         [Clip Bounds & Filtering]
                                     |
                          [MLT XML Builder]
                     (1080x1920 9:16 Project Profile)
                                     |
                                     v
                       [Generated .kdenlive Project]
```

---

## 2. Core Modules

| Module | Purpose |
|---|---|
| `clip_harvester.cli` | Command-line parsing, pre-flight environment checks, progress reporting |
| `clip_harvester.media.probe` | Video metadata extraction (`ffprobe` wrapper for rational framerate, duration, dimensions) |
| `clip_harvester.media.audio` | Audio track extraction and deterministic 20-minute chunking via `ffmpeg` |
| `clip_harvester.ai.client` | Google GenAI SDK interface, Files API lifecycle management, polling, and cleanup |
| `clip_harvester.ai.models` | Pydantic data schemas enforcing strict JSON generation from Gemini |
| `clip_harvester.ai.prompts` | Prompt assembly with offset compensation and profile injection |
| `clip_harvester.ai.validator`| Timestamp validation, hallucination detection, pre-roll padding, and clip ranking |
| `clip_harvester.kdenlive.timecode`| Bi-directional translation between timecodes, seconds, and integer frame numbers |
| `clip_harvester.kdenlive.xml_builder`| Synthesizes valid MLT XML conforming to Kdenlive project requirements |

---

## 3. Engineering Decisions & Failsafes

1. **20-Minute Chunking**: Multimodal audio models exhibit cumulative temporal drift on uninterrupted 1-2+ hour audio streams. Slicing into 20-minute segments resets the alignment window while maintaining sufficient context for complete thought extraction.
2. **Global Offset Accounting**: Each chunk prompt is explicitly injected with its global time offset (e.g. `00:40:00`), instructing the model to output global timecodes directly.
3. **Transcript Anchoring**: The model generates a timestamped transcript in the same inference pass as clip detection. The post-processor validates that proposed clip boundaries correspond to actual transcript points.
4. **Pre-roll Padding**: Automatically applies 1.5 seconds of head padding before the detected speech boundary, preventing premature audio clipping of the opening syllable.
5. **Remote File Hygiene**: Remote audio resources uploaded to Google's Files API are explicitly deleted via guaranteed `finally:` blocks immediately after inference finishes.
6. **Frame-Accurate XML**: Kdenlive/MLT XML uses integer frame numbers ($F = \lfloor \text{seconds} \times \text{FPS} \rfloor$). Rational frame rates (e.g. `30000/1001` for 29.97 FPS) are calculated with high precision.

---

## 4. Usage Reference

### Interactive Wizard (Zero Flags)
Run without any arguments to enter the interactive terminal wizard with file path drag-and-drop:
```powershell
python -m clip_harvester
```

### Direct CLI Execution
```powershell
# Set API Key (Required)
$env:GEMINI_API_KEY="your-api-key"

# Basic Sermon Extraction using friendly model alias
python -m clip_harvester "C:\Videos\Sunday_Sermon.mp4" --profile sermon --max-clips 5 --model flash-latest

# Auto-Approve without Interactive Curation Loop (--yes)
python -m clip_harvester "C:\Videos\Sunday_Sermon.mp4" --profile sermon --yes

# Custom Duration & Output Path
python -m clip_harvester "C:\Videos\Podcast_Ep12.mp4" `
    --profile podcast `
    --max-clips 3 `
    --min-duration 30 `
    --max-duration 60 `
    --output "C:\Edits\Podcast_Shorts.kdenlive"
```

### Interactive Clip Curation Panel
Before generating the `.kdenlive` XML file, the terminal displays an interactive review table:
- `[A]` Approve current selection and generate Kdenlive project
- `[T]` Toggle which clips to include/exclude (e.g. `1, 3` or `all`)
- `[E]` Edit start/end timecodes of any clip with live duration recalculation
- `[Q]` Abort without creating the project file

### Minimalist Terminal Aesthetics:
- **Palette**: Deep slate monochrome (`grey50`, `white`) with an electric-cyan accent (`bold cyan`).
- **Typography & Glyphs**: Clean box-drawing headers (`box.ROUNDED`), borderless data tables (`box.SIMPLE_HEAD`), and clean ASCII badges (`[OK]`, `[WARN]`, `[ERR]`, `[X]`). No emojis.


### Model Aliases Supported:
- `flash` or `flash-latest`: Automatically maps to active Flash release (`gemini-2.5-flash`).
- `pro` or `pro-latest`: Automatically maps to active Pro release (`gemini-2.5-pro`).
- Explicit IDs: You can also pass any full model string directly (e.g. `--model gemini-3.0-flash`).

---

## 5. Background Dependency Downloader & Concurrent Onboarding

To provide a friction-free experience for users on new machines without system dependencies (`ffmpeg` or `kdenlive`):

1. **Non-Blocking Background Thread**: If `ffmpeg` or `ffprobe` is not found on the active `PATH`, `DependencyDownloader` immediately spawns a background daemon thread that streams official static release builds into `%LOCALAPPDATA%\KdenShorts\bin\`.
2. **Zero Idling / Active Onboarding**: While the ~90MB archive downloads in the background, the user is never stuck waiting at an empty progress screen. Instead, the interactive onboarding wizard executes concurrently:
   - Validates or prompts for `GEMINI_API_KEY` with a live ping to Google AI Studio.
   - Allows drag-and-drop ingestion of the target media file with path sanitization.
   - Configures the selection profile (`sermon`, `podcast`, `general`).
   - Presents educational guidance for editing 9:16 vertical video in Kdenlive (canvas scaling, face centering, motion tracking, auto-subtitles).
3. **Barrier Synchronization**: Once user configuration is complete, the wizard checks the background downloader state. If the archive is still in-flight, it displays a compact Rich percentage bar until extraction finishes and runtime `PATH` is updated.
4. **Zero Overhead for Configured Systems**: When `ffmpeg` and credentials already exist, all background mechanisms are bypassed entirely for an instantaneous 0ms startup.

