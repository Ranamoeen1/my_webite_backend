# How to Export Cookies for Video Downloader

To bypass bot detection on YouTube, Instagram, and other platforms, you need to provide browser cookies from a logged-in session.

## Method 1: Using Browser Extension (Easiest)

1. Install the **"Get cookies.txt LOCALLY"** extension:
   - [Chrome/Edge](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - [Firefox](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

2. Log into the platform (YouTube, Instagram, etc.) in your browser

3. Click the extension icon and click "Export" to download `cookies.txt`

4. Upload `cookies.txt` to your Hugging Face Space:
   - Go to your Space: https://huggingface.co/spaces/ranamoeen1/vedio_downloader
   - Click "Files" tab
   - Upload the `cookies.txt` file to the root directory

## Method 2: Via yt-dlp Command (Advanced)

```bash
yt-dlp --cookies-from-browser chrome --cookies cookies.txt https://www.youtube.com/watch?v=test
```

## Important Notes

- ⚠️ Keep `cookies.txt` private - it contains your login session
- 🔄 Cookies expire - you may need to re-export periodically
- 🔒 Never share your cookies file publicly
- ✅ Once uploaded, the backend will automatically use it

## How It Works

The backend checks for a `cookies.txt` file and uses it for authentication:
- If found: Downloads work with authentication (bypasses bot detection)
- If not found: Downloads work for public/unrestricted content only
