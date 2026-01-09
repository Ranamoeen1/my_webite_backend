# 🔧 Quick Fix for Instagram Download Error

## The Error You're Seeing

```
❌ ERROR: Requested content is not available, rate-limit reached or login required
```

## Why This Happens

Instagram requires authentication (login cookies) to download videos. Without cookies, Instagram blocks the download to prevent bots.

## ✅ EASIEST SOLUTION - Use the Automated Script

### Step 1: Run the Cookie Extractor
```bash
cd backend
./extract_cookies.sh
```

### Step 2: Follow the Prompts
1. Select your browser (Firefox, Chrome, or Chromium)
2. Make sure you're logged into Instagram in that browser
3. Press Enter to extract cookies

### Step 3: Restart Your Server
The `cookies.txt` file will be automatically used by the server.

---

## 🔄 Alternative Method - Manual Browser Extension

If the automated script doesn't work, use a browser extension:

### 1. Install Extension
- **Chrome/Edge**: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
- **Firefox**: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

### 2. Export Cookies
1. Log into Instagram in your browser
2. Click the extension icon while on instagram.com
3. Click "Export" to download `cookies.txt`

### 3. Place the File
Save `cookies.txt` to: `/home/rana/SE docs/Practice/backend/cookies.txt`

---

## 🔐 Security Notes

- ⚠️ **Keep cookies.txt private** - it contains your login session
- 🔄 **Cookies expire** - re-export if downloads stop working
- 🔒 **Never commit cookies.txt** to Git (already in .gitignore)

---

## ✅ Verify It's Working

After adding cookies, test with an Instagram URL:
```bash
cd backend
python3 server.py
```

Then try downloading an Instagram video through your frontend.

---

## 📚 More Information

See `COOKIES_GUIDE.md` for detailed documentation.
