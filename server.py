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
import random
import requests
import concurrent.futures

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


def get_auto_proxy():
    """
    Fetch a working HTTP/HTTPS proxy from public lists.
    Returns: Proxy URL or None
    """
    try:
        logger.info("Fetching auto-proxy list...")
        # Source: TheSpeedX/PROXY-List (HTTP/HTTPS)
        url = "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            proxies = response.text.strip().split('\n')
            # Filter for decent looking proxies (simple check)
            proxies = [p.strip() for p in proxies if ':' in p]
            if proxies:
                # Pick a random one
                chosen = random.choice(proxies)
                full_proxy = f"http://{chosen}"
                logger.info(f"Auto-Proxy selected: {full_proxy}")
                return full_proxy
    except Exception as e:
        logger.error(f"Failed to fetch auto-proxy: {e}")
    
    return None


def download_video(url, quality='best'):
    """
    Download video from URL using yt-dlp with smart fallbacks
    """
    url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
    timestamp = int(time.time())
    
    has_ffmpeg = check_ffmpeg()

    # Base yt-dlp options for all strategies
    base_ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': f"{quality}video+{quality}audio/best" if has_ffmpeg else 'best',
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(id)s_%(epoch)s.%(ext)s',
        'noplaylist': True,
        'socket_timeout': 5,   
        'retries': 1,          
        'fragment_retries': 1,
        'concurrent_fragments': 5, # Speed up download significantly
        # Geo-bypass defaults
        'geo_bypass': True,
        'geo_bypass_country': 'US',
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'force_ipv4': True,
        'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}] if has_ffmpeg else [],
    }

    # Define strategies - Optimized Order: Default -> iOS -> Android -> Chrome
    strategies = [
        {
            'name': 'Default Client (Standard)',
            'opts': {}
        },
        {
            'name': 'iOS Client (Mobile)',
            'opts': {
                'extractor_args': {'youtube': {'player_client': ['ios']}},
            }
        },
        {
            'name': 'Android Client (Mobile)',
            'opts': {
                'extractor_args': {'youtube': {'player_client': ['android']}},
            }
        },
        {
            'name': 'Impersonate Chrome (Browser)',
            'opts': {
                'impersonate': 'chrome',
            }
        }
    ]

    last_error = None

    def find_downloaded_file(ydl, info, url_hash, timestamp):
        """Helper to find the best matching file after download"""
        expected_filename = ydl.prepare_filename(info)
        if os.path.exists(expected_filename) and os.path.getsize(expected_filename) > 0:
            return expected_filename
            
        # Try prefix find
        prefix = f"{url_hash}_{timestamp}"
        candidates = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.startswith(prefix)]
        if candidates:
            candidates.sort(key=lambda x: os.path.getsize(os.path.join(DOWNLOAD_FOLDER, x)), reverse=True)
            candidate_path = os.path.join(DOWNLOAD_FOLDER, candidates[0])
            if os.path.getsize(candidate_path) > 0:
                return candidate_path
        
        # Try timestamp find (last 60s)
        files = [os.path.join(DOWNLOAD_FOLDER, f) for f in os.listdir(DOWNLOAD_FOLDER)]
        if files:
            latest_file = max(files, key=os.path.getctime)
            if time.time() - os.path.getctime(latest_file) < 60:
                 if os.path.getsize(latest_file) > 0:
                     return latest_file
        
        return None

    for strategy in strategies:
        strategy_name = strategy['name']
        logger.info(f"Attempting download with strategy: {strategy_name}")

        # Start with base options and deep copy to avoid mutations
        import copy
        ydl_opts = copy.deepcopy(base_ydl_opts)
        
        # Set unique output template for this run
        ydl_opts['outtmpl'] = os.path.join(DOWNLOAD_FOLDER, f'{url_hash}_{timestamp}.%(ext)s')

        # Apply strategy options
        ydl_opts.update(strategy['opts'])

        # Add PO Token/Visitor Data
        po_token = os.environ.get('PO_TOKEN')
        visitor_data = os.environ.get('VISITOR_DATA')
        
        if po_token or visitor_data:
            if 'extractor_args' not in ydl_opts:
                ydl_opts['extractor_args'] = {}
            if 'youtube' not in ydl_opts['extractor_args']:
                ydl_opts['extractor_args']['youtube'] = {}
            
            if po_token:
                ydl_opts['extractor_args']['youtube']['po_token'] = [f'web+{po_token}']
            if visitor_data:
                ydl_opts['extractor_args']['youtube']['visitor_data'] = [visitor_data]

        # Add cookie file if it exists
        cookie_file = os.environ.get('COOKIE_FILE', 'cookies.txt')
        if os.path.exists(cookie_file):
            ydl_opts['cookiefile'] = cookie_file

        # Proxy support
        # 1. Check environment variable
        proxy = os.environ.get('PROXY')
        if proxy:
            ydl_opts['proxy'] = proxy

        # 2. Check for manual strategy proxy (if we add one later)
        if 'proxy' in strategy.get('opts', {}):
             ydl_opts['proxy'] = strategy['opts']['proxy']

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                filename = find_downloaded_file(ydl, info, url_hash, timestamp)
                if not filename:
                     raise Exception("File not found after download")

                logger.info(f"Download SUCCESS with strategy: {strategy_name}")
                return {
                    'success': True,
                    'filepath': filename,
                    'filename': os.path.basename(filename),
                    'title': info.get('title', 'Unknown'),
                    'platform': info.get('extractor', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'file_size': os.path.getsize(filename),
                }

        except Exception as e:
            error_str = str(e)
            logger.warning(f"Strategy {strategy_name} failed: {error_str}")
            
            # Check for Geo-Restriction Detection
            if "unavailable in your country" in error_str or "uploader has not made this video available" in error_str:
                logger.info("❌ Geo-Restriction detected! Attempting Auto-Proxy...")
                
                # Fetch a proxy dynamically
                auto_proxy = get_auto_proxy()
                if auto_proxy:
                    # Create a new dynamic strategy for this proxy
                    proxy_strategy = {
                        'name': f'Auto-Proxy ({auto_proxy})',
                        'opts': {
                            'proxy': auto_proxy,
                            'geo_bypass_country': 'CA' # Try Canada by default
                        }
                    }
                    # Insert this strategy immediately after the current one to try next
                    # But we are iterating over a list. Modifying it while iterating is risky.
                    # Instead, let's just run a "sub-attempt" right here.
                    
                    logger.info(f"🔁 Retrying with Auto-Proxy: {auto_proxy}")
                    # Update opts for this specific retry
                    retry_opts = ydl_opts.copy()
                    retry_opts['proxy'] = auto_proxy
                    retry_opts['geo_bypass_country'] = 'CA'
                    
                    try:
                        with yt_dlp.YoutubeDL(retry_opts) as ydl_retry:
                            info = ydl_retry.extract_info(url, download=True)
                            
                            filename = find_downloaded_file(ydl_retry, info, url_hash, timestamp)
                            
                            if filename:
                                logger.info(f"✅ Auto-Proxy SUCCEEDED!")
                                return {
                                    'success': True,
                                    'filepath': filename,
                                    'filename': os.path.basename(filename),
                                    'title': info.get('title', 'Unknown'),
                                    'platform': info.get('extractor', 'Unknown'),
                                    'duration': info.get('duration', 0),
                                    'file_size': os.path.getsize(filename),
                                }
                    except Exception as proxy_error:
                         logger.warning(f"Auto-Proxy attempt failed: {proxy_error}")

            last_error = error_str
            continue

    # If we get here, all strategies failed
    logger.error("All download strategies failed.")
    return {
        'success': False,
        'error': f"All attempts failed. Last error: {last_error}"
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
        
        # Download the video with a 50-second timeout
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(download_video, url, quality)
            try:
                result = future.result(timeout=50) # Strict 50s limit
            except concurrent.futures.TimeoutError:
                logger.error(f"Download TIMEOUT for URL: {url}")
                return jsonify({
                    'success': False,
                    'error': 'The download is taking too long (over 50 seconds). Large videos might need more time than the server allows. Please try a shorter video or try again later.'
                }), 504
        
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
        'version': '1.1.0'
    })



@app.route('/')
def index():
    """
    Health check at root
    """
    return health_check()


@app.route('/api/test-proxy', methods=['GET'])
def test_proxy():
    """Test if the configured proxy is working and return the external IP"""
    proxy = os.environ.get('PROXY')
    results = {
        "proxy_configured": bool(proxy),
        "proxy_url": proxy[:15] + "..." if proxy else None,
        "direct_ip": None,
        "proxy_ip": None,
        "error": None
    }
    
    try:
        # Get direct IP
        results["direct_ip"] = requests.get('https://api.ipify.org', timeout=5).text
        
        # Get proxy IP if configured
        if proxy:
            proxies = {'http': proxy, 'https': proxy}
            results["proxy_ip"] = requests.get('https://api.ipify.org', proxies=proxies, timeout=10).text
            
            if results["proxy_ip"] == results["direct_ip"]:
                results["status"] = "Proxy configured but NOT being used (IPs match)"
            else:
                results["status"] = "Proxy is WORKING (IPs differ)"
        else:
            results["status"] = "No proxy configured"
            
    except Exception as e:
        results["error"] = str(e)
        results["status"] = "Error testing proxy"
        
    return jsonify(results)

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
