#!/bin/bash

# Cookie Extraction Script for Instagram/Social Media Downloads
# Author: Rana Moeen

echo "================================================"
echo "  Cookie Extraction Tool"
echo "  For Instagram & Social Media Authentication"
echo "================================================"
echo ""

# Detect available browsers
BROWSERS=()
if command -v firefox &> /dev/null; then
    BROWSERS+=("firefox")
fi
if command -v google-chrome &> /dev/null || command -v chromium &> /dev/null; then
    BROWSERS+=("chrome")
fi
if command -v chromium-browser &> /dev/null; then
    BROWSERS+=("chromium")
fi

if [ ${#BROWSERS[@]} -eq 0 ]; then
    echo "❌ No supported browsers found (Firefox, Chrome, or Chromium)"
    echo "Please install one of these browsers first."
    exit 1
fi

echo "🌐 Detected browsers: ${BROWSERS[@]}"
echo ""
echo "Which browser do you want to extract cookies from?"
echo ""
for i in "${!BROWSERS[@]}"; do
    echo "  $((i+1)). ${BROWSERS[$i]}"
done
echo ""
read -p "Enter choice (1-${#BROWSERS[@]}): " choice

# Validate choice
if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt ${#BROWSERS[@]} ]; then
    echo "❌ Invalid choice"
    exit 1
fi

SELECTED_BROWSER="${BROWSERS[$((choice-1))]}"
echo ""
echo "✅ Selected: $SELECTED_BROWSER"
echo ""

# Instructions
echo "📝 IMPORTANT STEPS TO BYPASS BOT DETECTION:"
echo "   1. Open $SELECTED_BROWSER"
echo "   2. Log in to Instagram and YouTube"
echo "   3. Visit a few videos/posts to ensure cookies are active"
echo "   4. Close the browser (some browsers lock the cookie database)"
echo ""
read -p "Press Enter when you have CLOSED the browser..."
echo ""

# Extract cookies
echo "🔄 Extracting cookies from $SELECTED_BROWSER..."
echo ""

yt-dlp --cookies-from-browser "$SELECTED_BROWSER" --cookies cookies.txt --no-download "https://www.instagram.com/" 2>&1 | grep -E "(Extracted|cookies|ERROR)" || true

# Check if cookies.txt was created
if [ -f "cookies.txt" ]; then
    COOKIE_COUNT=$(wc -l < cookies.txt)
    echo ""
    echo "================================================"
    echo "  ✅ SUCCESS!"
    echo "================================================"
    echo ""
    echo "  📁 Cookie file created: cookies.txt"
    echo "  🍪 Total entries: $COOKIE_COUNT"
    echo ""
    echo "  The server will now automatically use these cookies"
    echo "  for Instagram and other platform downloads."
    echo ""
    echo "================================================"
else
    echo ""
    echo "❌ Failed to create cookies.txt"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Make sure you're logged into Instagram in $SELECTED_BROWSER"
    echo "  2. Try closing and reopening your browser"
    echo "  3. Try a different browser"
    echo "  4. Use the manual browser extension method (see COOKIES_GUIDE.md)"
    echo ""
    exit 1
fi
