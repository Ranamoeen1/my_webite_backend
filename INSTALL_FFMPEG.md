# How to Install FFmpeg

FFmpeg is a powerful tool used to process video and audio. Our downloader uses it to merge high-quality video and audio streams into a single file.

## 🐧 Linux (Ubuntu/Debian)

Run the following command in your terminal:

```bash
sudo apt update
sudo apt install ffmpeg
```

To verify:
```bash
ffmpeg -version
```

## 🪟 Windows

1. Download the latest build from [Gyan.dev](https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z).
2. Extract the folder to a location like `C:\ffmpeg`.
3. Add the `bin` folder (e.g., `C:\ffmpeg\bin`) to your **System PATH**:
    - Search for "Edit the system environment variables".
    - Click "Environment Variables".
    - Under "System variables", find "Path" and click "Edit".
    - Click "New" and paste the path to the `bin` folder.
4. Restart your terminal/command prompt.

To verify:
```cmd
ffmpeg -version
```

## 🍎 macOS

If you have [Homebrew](https://brew.sh/) installed, run:

```bash
brew install ffmpeg
```

To verify:
```bash
ffmpeg -version
```

---

## ✅ Why install FFmpeg?

- **Higher Quality**: Without FFmpeg, you might only get 720p or lower because higher resolutions often require merging separate video and audio streams.
- **Better Compatibility**: FFmpeg ensures the final file is in a standard format (like MP4) that plays everywhere.
