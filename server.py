"""
Social Media Video Downloader - Backend Server
Author: Rana Moeen

Flask backend server with yt-dlp integration for downloading videos
from various social media platforms.
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import time
import hashlib
from pathlib import Path
import logging
import shutil

# Initialize Flask app
app = Flask(__name__, static_url_path='', static_folder='.')
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Enable CORS for all API routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# DNS FIX: Monkeypatch socket.getaddrinfo
# ==========================================
import dns.resolver
import socket

def configure_dns():
    """Force use of Google DNS to bypass container issues"""
    try:
        # Create a resolver that uses Google DNS
        res = dns.resolver.Resolver()
        res.nameservers = ['8.8.8.8', '8.8.4.4']
        
        _original_getaddrinfo = socket.getaddrinfo
        
        def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            # If it's an IP address, use original
            try:
                socket.inet_aton(host)
                return _original_getaddrinfo(host, port, family, type, proto, flags)
            except:
                pass
                
            try:
                # Try to resolve using our custom resolver
                answers = res.resolve(host)
                ip = answers[0].address
                logger.info(f"DNS Fix: Resolved {host} to {ip}")
                return _original_getaddrinfo(ip, port, family, type, proto, flags)
            except Exception as e:
                # Fallback to original if custom resolution fails
                logger.warning(f"DNS Fix failed for {host}: {e}, falling back to system DNS")
                return _original_getaddrinfo(host, port, family, type, proto, flags)
                
        socket.getaddrinfo = patched_getaddrinfo
        logger.info("DNS Monkeypatch applied successfully")
    except Exception as e:
        logger.error(f"Failed to apply DNS monkeypatch: {e}")

# Apply the fix
configure_dns()

# Configuration
DOWNLOAD_FOLDER = 'downloads'
MAX_FILE_AGE = 3600  # Delete files older than 1 hour (in seconds)

# Create downloads folder if it doesn't exist
Path(DOWNLOAD_FOLDER).mkdir(exist_ok=True)


def check_ffmpeg():
    """Check if ffmpeg is installed and available in PATH"""
    return shutil.which('ffmpeg') is not None


def cleanup_old_files():
    """Remove downloaded files older than MAX_FILE_AGE seconds"""
    try:
        current_time = time.time()
        for filename in os.listdir(DOWNLOAD_FOLDER):
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > MAX_FILE_AGE:
                    os.remove(filepath)
                    logger.info(f"Deleted old file: {filename}")
    except Exception as e:
        logger.error(f"Error cleaning up files: {str(e)}")


def get_video_info(url):
    """
    Extract video information without downloading
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'success': True,
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'platform': info.get('extractor', 'Unknown'),
                'uploader': info.get('uploader', 'Unknown'),
            }
    except Exception as e:
        logger.error(f"Error extracting info: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def download_video(url, quality='best'):
    """
    Download video from URL using yt-dlp
    
    Args:
        url: Video URL
        quality: Video quality (best, worst, or specific format)
    
    Returns:
        dict: Download result with filepath and metadata
    """
    # Generate unique filename based on URL hash
    url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
    timestamp = int(time.time())
    
    # Check for FFmpeg
    has_ffmpeg = check_ffmpeg()
    if not has_ffmpeg:
        logger.warning("FFmpeg not found! Falling back to 'best' format (single file) to avoid merging error.")
    
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'{url_hash}_{timestamp}.%(ext)s'),
        # If ffmpeg exists, allow merging. Otherwise, fallback to best single file
        'format': 'bestvideo*+bestaudio/best' if has_ffmpeg else 'best',
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Mode': 'navigate',
        },
        'impersonate': 'chrome', # Mimic Chrome's TLS fingerprint and headers
        'force_ipv4': True,  # Force IPv4 to fix DNS issues on some platforms
    }
    
    # Add cookie file if it exists (to bypass bot detection)
    cookie_file = os.environ.get('COOKIE_FILE', 'cookies.txt')
    if os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file
        logger.info(f"Using cookie file: {cookie_file}")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info and download
            info = ydl.extract_info(url, download=True)
            
            # AGGRESSIVE FILE FINDING STRATEGY
            # 1. Try expected filename
            expected_filename = ydl.prepare_filename(info)
            filename = expected_filename
            
            # 2. If not found or empty, look for ANY file with our hash prefix
            if not os.path.exists(filename) or os.path.getsize(filename) == 0:
                prefix = f"{url_hash}_{timestamp}"
                candidates = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.startswith(prefix)]
                
                if candidates:
                    # Pick the largest file (likely the video)
                    candidates.sort(key=lambda x: os.path.getsize(os.path.join(DOWNLOAD_FOLDER, x)), reverse=True)
                    filename = os.path.join(DOWNLOAD_FOLDER, candidates[0])
                    logger.info(f"Found alternative file via prefix: {filename}")
            
            # 3. Last resort: Look for the most recently created file in downloads
            if not os.path.exists(filename) or os.path.getsize(filename) == 0:
                files = [os.path.join(DOWNLOAD_FOLDER, f) for f in os.listdir(DOWNLOAD_FOLDER)]
                if files:
                    latest_file = max(files, key=os.path.getctime)
                    # Only use if it was created in the last 60 seconds
                    if time.time() - os.path.getctime(latest_file) < 60:
                        filename = latest_file
                        logger.info(f"Found file via timestamp: {filename}")

            # Final check
            if not os.path.exists(filename) or os.path.getsize(filename) == 0:
                return {
                    'success': False,
                    'error': 'Download failed: File not found or empty'
                }
            
            # Get file info
            file_size = os.path.getsize(filename)
            
            return {
                'success': True,
                'filepath': filename,
                'filename': os.path.basename(filename),
                'title': info.get('title', 'Unknown'),
                'platform': info.get('extractor', 'Unknown'),
                'duration': info.get('duration', 0),
                'file_size': file_size,
            }
    
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@app.route('/api/info', methods=['POST'])
def get_info():
    """
    Get video information without downloading
    POST /api/info
    Body: { "url": "video_url" }
    """
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'URL is required'
            }), 400
        
        info = get_video_info(url)
        return jsonify(info)
    
    except Exception as e:
        logger.error(f"Error in /api/info: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/download', methods=['POST'])
def download():
    """
    Download video from URL
    POST /api/download
    Body: { "url": "video_url", "quality": "best" }
    """
    try:
        # Clean up old files before processing new download
        cleanup_old_files()
        
        data = request.get_json()
        url = data.get('url')
        quality = data.get('quality', 'best')
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'URL is required'
            }), 400
        
        logger.info(f"Downloading video from: {url}")
        
        # Download the video
        result = download_video(url, quality)
        
        if result['success']:
            return jsonify({
                'success': True,
                'filename': result['filename'],
                'title': result['title'],
                'platform': result['platform'],
                'duration': result['duration'],
                'file_size': result['file_size'],
                'download_url': f"/api/file/{result['filename']}"
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
    
    except Exception as e:
        logger.error(f"Error in /api/download: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/file/<filename>', methods=['GET'])
def get_file(filename):
    """
    Serve downloaded file
    GET /api/file/<filename>
    """
    try:
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        logger.error(f"Error serving file: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    GET /api/health
    """
    return jsonify({
        'status': 'healthy',
        'service': 'video-downloader-backend',
        'version': '1.0.0'
    })



@app.route('/')
def index():
    """
    Health check at root
    """
    return health_check()


if __name__ == '__main__':
    logger.info("Starting Video Downloader Backend Server...")
    logger.info("Author: Rana Moeen")
    
    # Get port from environment variable (Hugging Face uses 7860 by default)
    port = int(os.environ.get("PORT", 7860))
    logger.info(f"Server running on port {port}")
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )
