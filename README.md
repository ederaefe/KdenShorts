# KdenShorts

> **Autonomous AI-Assisted YouTube Shorts & Reels Harvester for Kdenlive**  
> *Transform 2-hour sermons, podcasts, keynotes, and interviews into pre-cut, vertical 9:16 Kdenlive timeline projects in minutes — completely GPU-free, privacy-preserving, and optimized for free-tier cloud AI.*

---

## Visual Preview

### 1. Interactive Terminal Setup Wizard
![Terminal Wizard](docs/images/01_terminal_wizard.png)

### 2. Live Interactive Candidate Curation Table
![Interactive Curation Table](docs/images/02_curation_table.png)

### 3. Pre-Cut 9:16 Vertical Timeline in Kdenlive
![Kdenlive 9:16 Timeline](docs/images/03_kdenlive_timeline.png)

---

## Table of Contents

- [1. Executive Summary](#1-executive-summary)
- [2. Why KdenShorts? (Architectural Comparison)](#2-why-kdenshorts-architectural-comparison)
- [3. Complete End-to-End Pipeline Architecture](#3-complete-end-to-end-pipeline-architecture)
- [4. System Requirements & Windows Prerequisites](#4-system-requirements--windows-prerequisites)
- [5. Installation Guide](#5-installation-guide)
- [6. Quickstart Guide](#6-quickstart-guide)
  - [Interactive Mode (Zero Arguments)](#interactive-mode-zero-arguments)
  - [Headless / CLI Mode](#headless--cli-mode)
- [7. Terminal Curation Interface (TUI)](#7-terminal-curation-interface-tui)
- [8. Content Selection Profiles](#8-content-selection-profiles)
- [9. Technical Deep-Dive: MLT XML Synthesis](#9-technical-deep-dive-mlt-xml-synthesis)
- [10. Complete Kdenlive Post-Production Workflow](#10-complete-kdenlive-post-production-workflow)
- [11. CLI Command-Line Reference](#11-cli-command-line-reference)
- [12. Troubleshooting & Diagnostics](#12-troubleshooting--diagnostics)
- [13. Automated Test Suite](#13-automated-test-suite)
- [14. License & Credits](#14-license--credits)

---

## 1. Executive Summary

Long-form spoken video (church sermons, multi-speaker podcasts, conference talks, educational lectures) contains high-impact moments ideal for YouTube Shorts, Instagram Reels, and TikTok. However, manually listening to a 2-hour recording, noting timecodes, trimming clips, reframing horizontal video into vertical 9:16, and color grading can consume 3 to 5 hours per episode.

**KdenShorts** automates the entire ingestion, speech analysis, and timeline-cutting pipeline:
1. It extracts and downsamples audio locally into speech-optimized 16kHz mono MP3 chunks.
2. It uploads small audio segments to Google's Gemini Flash model via the Files API.
3. It performs single-pass transcription and semantic highlight detection using strict Pydantic JSON schemas.
4. It presents an interactive terminal curation table where you can review, approve, toggle, or tweak timecodes.
5. It compiles a native `.kdenlive` (MLT XML) project file configured to a 1080x1920 (9:16 vertical) canvas.
6. When opened in Kdenlive, your source footage is already cut into pre-spaced clips on the timeline. You retain 100% creative control over visual framing, face tracking, dynamic subtitles, color grading, and final render settings.

---

## 2. Why KdenShorts? (Architectural Comparison)

| Feature | Cloud SaaS (Opus Clip, Munch) | Local Neural Clippers (Whisper/Torch) | KdenShorts |
|---|---|---|---|
| **Hardware Requirement** | Any (runs on cloud servers) | High-End GPU (8GB - 16GB+ VRAM) | Standard CPU Laptop / Desktop |
| **Video Upload Bandwidth** | Uploads entire multi-gigabyte video | Zero (100% local processing) | Zero video uploaded (Audio-only ~15MB) |
| **Privacy & Storage** | Full video stored on 3rd-party cloud | 100% Local | Audio chunks deleted immediately after inference |
| **Ongoing Cost** | \$15 - \$50 / month recurring | Free (high electricity & hardware cost) | Free (uses Google AI Studio Free Tier) |
| **Timeline Flexibility** | Export baked MP4s (hard to re-edit) | Export baked MP4s | Native `.kdenlive` project file (fully editable) |
| **Face Tracking & Framing** | Automated (often crops incorrectly) | Auto-crop (rigid) | Kdenlive Motion Tracker / Transform effect |
| **Render Quality** | Lossy cloud re-compression | Local re-encode | Lossless timeline referencing master raw video |

---

## 3. Complete End-to-End Pipeline Architecture

```
                                [Master Video File]
                              (C:\Footage\Episode.mp4)
                                         |
                                         v
                     +---------------------------------------+
                     | Stage 1: Media Inspection (ffprobe)   |
                     | - Exact Rational FPS (e.g. 30000/1001)|
                     | - Duration & Dimensions (1920x1080)   |
                     +-------------------+-------------------+
                                         |
                                         v
                     +---------------------------------------+
                     | Stage 2: Audio Extraction (ffmpeg)    |
                     | - Downsample to 16kHz Mono MP3 (128k) |
                     | - Segment into 20-min chunks (1200s)  |
                     | - Reset timestamps per segment file   |
                     +-------------------+-------------------+
                                         |
                     +-------------------+-------------------+
                     |                   |                   |
               [chunk_000.mp3]     [chunk_001.mp3]     [chunk_002.mp3]
               (00:00 - 20:00)     (20:00 - 40:00)     (40:00 - 60:00)
                     |                   |                   |
                     +-------------------+-------------------+
                                         |
                                         v
                     +---------------------------------------+
                     | Stage 3: Gemini Audio Understanding   |
                     | - Upload via Files API                |
                     | - Poll state until ACTIVE             |
                     | - Inject Absolute Offset (e.g. 20:00) |
                     | - Single-pass: Transcribe + Hook Pick |
                     | - Strict Pydantic JSON Schema         |
                     | - Guaranteed remote file deletion     |
                     +-------------------+-------------------+
                                         |
                                         v
                     +---------------------------------------+
                     | Stage 4: Validation Engine            |
                     | - Timestamp bounds check              |
                     | - Transcript grounding verification   |
                     | - Duration filter (30s - 80s)         |
                     | - Pre-roll padding (+1.5s start head) |
                     | - Overlap deduplication & ranking     |
                     +-------------------+-------------------+
                                         |
                                         v
                     +---------------------------------------+
                     | Stage 5: Interactive Curation TUI     |
                     | - Rich Table visualization            |
                     | - [A] Approve / [T] Toggle / [E] Edit |
                     +-------------------+-------------------+
                                         |
                                         v
                     +---------------------------------------+
                     | Stage 6: Kdenlive MLT XML Synthesis   |
                     | - 9:16 Profile (1080x1920)            |
                     | - Source Video Producer               |
                     | - Main Bin Folder ("Shorts Clips")    |
                     | - Timeline Playlist with 50-frame gaps|
                     +-------------------+-------------------+
                                         |
                                         v
                           [Episode_Shorts.kdenlive]
                                         |
                                         v
                     +---------------------------------------+
                     | Stage 7: Kdenlive Post-Production     |
                     | - Face reframing (Transform / Tracker)|
                     | - Color grading & Audio mastering     |
                     | - Dynamic auto-subtitles              |
                     | - Batch render to 9:16 vertical MP4s  |
                     +---------------------------------------+
```

---

## 4. System Requirements & Windows Prerequisites

KdenShorts is built natively for Windows 10/11 (and supports Linux/macOS):

### 1. Python 3.10, 3.11, or 3.12
Check your Python installation:
```powershell
python --version
```

### 2. FFmpeg & FFprobe
KdenShorts uses `ffmpeg` for audio slicing and `ffprobe` for frame-accurate metadata discovery.

> [!NOTE]
> **Automatic Zero-Config Downloader:** If you don't have FFmpeg pre-installed, KdenShorts handles it for you automatically! When started without local binaries, a background worker streams and unpacks official portable static builds into `%LOCALAPPDATA%\KdenShorts\bin\` while you interactively validate your API key, select your source video, and review Kdenlive vertical editing tips.

If you prefer to install system-wide FFmpeg manually:
- **Via Windows Package Manager (Winget - Recommended):**
  ```powershell
  winget install Gyan.FFmpeg
  ```
- **Via Scoop:**
  ```powershell
  scoop install ffmpeg
  ```
- **Via Chocolatey:**
  ```powershell
  choco install ffmpeg
  ```

### 3. Google Gemini API Key
KdenShorts uses the official `google-genai` SDK.
1. Visit [Google AI Studio](https://aistudio.google.com/) and create a free API key.
2. In PowerShell, set your environment variable:
   ```powershell
   $env:GEMINI_API_KEY="your-api-key-here"
   ```
3. To persist this permanently across all PowerShell sessions:
   ```powershell
   [System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'your-api-key-here', 'User')
   ```

---

## 5. Installation Guide

Clone this repository and install dependencies in your Python environment:

```powershell
git clone https://github.com/ederaefe/KdenShorts.git
cd KdenShorts
pip install -r requirements.txt
```

### Dependencies Installed:
- `google-genai`: Official unified Python SDK for Gemini multimodal models.
- `pydantic`: Schema validation and type enforcement for structured AI outputs.
- `rich`: Minimalist, high-performance terminal UI layout and progress spinners.
- `pytest`: Automated test harness.

---

## 6. Quickstart Guide

### Interactive Mode (Zero Arguments)
The simplest way to use KdenShorts:
```powershell
python kdenshorts.py
```
- The interactive wizard prompts you to enter or drag-and-drop your video file path.
- Select your profile (`sermon`, `podcast`, `general`).
- The pipeline processes the video and presents the candidate curation table.

---

### Headless / CLI Mode
Specify options directly via flags:

```powershell
# 1. Process Sunday sermon and extract the top 5 clips
python kdenshorts.py "C:\Footage\Sunday_Service.mp4" --profile sermon --max-clips 5

# 2. Extract podcast highlights between 30 and 60 seconds
python kdenshorts.py "C:\Podcasts\Episode_10.mp4" `
    --profile podcast `
    --max-clips 4 `
    --min-duration 30 `
    --max-duration 60 `
    --output "C:\Edits\Episode_10_Shorts.kdenlive"

# 3. Use the latest Pro model for deep theological reasoning
python kdenshorts.py "C:\Footage\Conference.mp4" --profile sermon --model pro-latest

# 4. Automated batch processing (bypasses interactive review table)
python kdenshorts.py "C:\Footage\Interview.mp4" --profile general --yes
```

---

## 7. Terminal Curation Interface (TUI)

When Gemini completes the audio analysis, KdenShorts pauses and renders the **Interactive Clip Curation Panel**:

### Table Legend:
- `SEL`: `[X]` indicates the clip is selected for project export. `[ ]` indicates excluded.
- `#`: Sequential clip index.
- `TITLE & HOOK`: Catchy title and verbatim opening sentence identified by AI.
- `TIMECODE`: Global absolute start and end times (`HH:MM:SS -> HH:MM:SS`).
- `DUR`: Exact spoken duration including 1.5s pre-roll syllable padding.
- `TYPE`: Content classification (`theological_revelation`, `bold_claim`, `story`, `curiosity_gap`).
- `CONF`: Model confidence rating (`HIGH`, `MEDIUM`, `LOW`).

### Available Commands:
- `[A]` **Approve & Build**: Exports all currently selected `[X]` clips into the `.kdenlive` XML file and exits.
- `[T]` **Toggle Selection**:
  - Type `2` to toggle clip #2.
  - Type `1, 3` to toggle multiple clips at once.
  - Type `all` to invert the entire selection.
- `[E]` **Edit Timecode**:
  - Enter the clip index (e.g. `1`).
  - Enter new `HH:MM:SS` start or end boundaries.
  - Duration is recalculated live.
- `[Q]` **Abort**: Safely exits without writing any `.kdenlive` project file.

---

## 8. Content Selection Profiles

Prompt profiles govern how the Gemini model evaluates spoken audio. Profiles are located in `clip_harvester/profiles/`:

### 1. `sermon.txt` (Default)
- **Target Highlights**: Transformational theological insights, emotional conviction, counter-intuitive biblical reframings, personal testimonies with moral takeaways.
- **Strict Exclusions**: Announcements, greetings, offering collections, scripture readings without interpretive commentary, phrases referencing earlier sermon sections.

### 2. `podcast.txt`
- **Target Highlights**: Provocative hot takes, counter-intuitive opinions, high-energy breakthroughs, humorous punchlines, sudden conversational shifts.
- **Strict Exclusions**: Podcast intro theme music, sponsor reads, audio checks, rambling small talk, greetings ("Thanks for having me").

### 3. `general.txt`
- **Target Highlights**: Universal life lessons, leadership insights, memorable quotes, inspiring anecdotes.
- **Strict Exclusions**: Logistics, administrative remarks, incomplete thoughts.

### Creating a Custom Profile
To create a specialized profile (e.g. `standup_comedy.txt` or `legal_debate.txt`):
1. Create `clip_harvester/profiles/my_profile.txt`.
2. Add target criteria and negative constraints.
3. Call with `--profile my_profile`.

---

## 9. Technical Deep-Dive: MLT XML Synthesis

Kdenlive saves projects in **MLT (Media Lovin' Toolkit) XML** format. Rather than forcing you to manually import and slice video in the GUI, KdenShorts programmatically generates this XML from scratch:

### Mathematical Frame Calculation
In MLT, timecodes must be converted into integer frame indices:
$$\text{Frame} = \text{round}(\text{Seconds} \times \text{FPS})$$

For NTSC footage at 29.97 FPS ($\frac{30000}{1001}$), rational arithmetic prevents timeline audio drift:
```python
in_frame = round(clip.start_seconds * (fps_num / fps_den))
out_frame = round(clip.end_seconds * (fps_num / fps_den))
```

### Generated XML Layout:
1. `<profile>`: Defines the canvas as `width="1080"`, `height="1920"`, `display_aspect_num="9"`, `display_aspect_den="16"`.
2. `<producer id="producer_raw_source">`: Directly references your original master video on your hard drive via the `avformat` engine.
3. `<playlist id="main_bin">`: Places the master video inside a virtual Project Bin folder named `Shorts Clips`.
4. `<playlist id="playlist_v1">`: Chains all approved clips sequentially onto Track Video 1.
5. `<blank length="50"/>`: Inserts an exact 50-frame gap between each clip so you can easily distinguish and edit each short independently.

---

## 10. Complete Kdenlive Post-Production Workflow

Once KdenShorts writes your `<filename>_shorts.kdenlive` project file:

### Step 1: Open Project
Double-click the generated `.kdenlive` file or open it inside Kdenlive. You will see:
- Track V1 contains all pre-cut clips.
- Audio waveforms are immediately visible.
- The project monitor is formatted to a 9:16 vertical rectangle.

### Step 2: Vertical Framing (Face Centering)
Because your original footage is likely horizontal 16:9 (1920x1080), the speaker may be off-center in the 9:16 window:
1. Select the clip on Track V1.
2. In the **Effects** panel, search for **Transform** (or **Position and Zoom**).
3. Drag the effect onto the clip.
4. Adjust the **X-Offset** slider until the speaker is centered in the 9:16 frame.

### Step 3: Automated Face Tracking (Optional)
If the speaker paces or moves across a stage:
1. Search for **Motion Tracker** in the Effects tab.
2. Place the tracking box over the speaker's face and click **Analyze**.
3. Link the motion track data to a **Transform** effect so the 9:16 window automatically follows the speaker.

### Step 4: Generating Dynamic Captions / Subtitles
Short-form content thrives on animated subtitles:
1. Go to **Project -> Subtitles -> Speech Recognition**.
2. Run Kdenlive's built-in subtitle generator (powered by Whisper or VOSK).
3. Style your subtitles: select a bold font (e.g. Montserrat, The Bold Font), yellow/white fill with a dark outline.

### Step 5: Exporting Individual Shorts
1. Set the Timeline In/Out guide zone (`I` and `O` keys) over Clip #1.
2. Press **Render** (`Ctrl + Return`).
3. Select **MP4 (H264/AAC)**.
4. Check **Selected Zone** and click **Render to File**.
5. Repeat for each short on the timeline.

---

## 11. CLI Command-Line Reference

```
usage: kdenshorts [-h] [--profile {sermon,podcast,general}]
                  [--max-clips MAX_CLIPS] [--min-duration MIN_DURATION]
                  [--max-duration MAX_DURATION] [--output OUTPUT]
                  [--model MODEL] [--chunk-duration CHUNK_DURATION]
                  [--yes] [--open] [--keep-temp]
                  [media_path]

positional arguments:
  media_path            Path to source video or audio file on disk (optional).

options:
  -h, --help            Show this help message and exit.
  --profile, -p         Content evaluation profile (default: sermon).
  --max-clips, -n       Maximum number of clips to select (default: 5).
  --min-duration        Minimum clip length in seconds (default: 30).
  --max-duration        Maximum clip length in seconds (default: 80).
  --output, -o          Custom path for generated .kdenlive file.
  --model               Model identifier or alias: 'flash', 'flash-latest', 'pro' (default: gemini-2.5-flash).
  --chunk-duration      Audio segment length in seconds (default: 1200 / 20 min).
  --yes, -y             Bypass interactive TUI and auto-approve all detected clips.
  --open, -O            Automatically launch Kdenlive with the compiled project loaded.
  --keep-temp           Preserve temporary audio chunk files in temp directory.
```

---

## 12. Troubleshooting & Diagnostics

### Problem: `ffmpeg is not installed or not on Windows PATH`
**Solution**: Make sure FFmpeg is installed. In PowerShell, run:
```powershell
winget install Gyan.FFmpeg
```
Close and reopen PowerShell so your environment variables refresh.

### Problem: `GEMINI_API_KEY environment variable is not set`
**Solution**: Set the environment variable in your terminal session:
```powershell
$env:GEMINI_API_KEY="your-api-key"
```

### Problem: `No clips satisfied the duration and confidence criteria`
**Solution**: 
1. Check your duration bounds. Some powerful statements are shorter or longer:
   ```powershell
   python kdenshorts.py video.mp4 --min-duration 20 --max-duration 90
   ```
2. Try a different profile: `--profile podcast` or `--profile general`.
3. Test using the Pro model for deeper rhetorical context: `--model pro-latest`.

### Problem: Video audio sounds clipped on the opening word
**Solution**: KdenShorts automatically applies a **1.5-second pre-roll head-pad** to every clip. In Kdenlive, you can drag the left edge of the clip to reveal even more buffer because the entire source video is linked natively.

---

## 13. Automated Test Suite

KdenShorts includes an automated test suite with 36 unit and integration tests covering:
- Rational FPS fraction parsing (`30000/1001` -> `29.97`).
- Timecode-to-frame arithmetic and timestamp boundary validation.
- XML syntactic well-formedness and Kdenlive schema compatibility.
- Hallucination rejection, duration filters, and pre-roll padding.
- Interactive input sanitizers, table rendering, and executable discovery.

Run the test suite at any time:
```powershell
python -m pytest tests/ -v
```

---

## 14. License & Credits

- **License**: Apache License 2.0. See `LICENSE` for details. Free for personal, commercial, and church media use.
- **Engine**: Powered by Google Gemini Multimodal Audio API, FFmpeg, and the MLT Multimedia Framework.

