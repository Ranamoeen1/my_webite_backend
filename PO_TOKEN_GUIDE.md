# How to Get YouTube PO Token & Visitor Data

Modern YouTube bot detection (2024+) often requires a "Proof of Origin" (PO) Token in addition to cookies.

## How to Get PO Token & Visitor Data

1.  **Open YouTube** in a new **Private/Incognito** window.
2.  **Open Developer Tools** (F12 or right-click -> Inspect).
3.  Go to the **Console** tab.
4.  Paste the following code and press Enter:

```javascript
(function() {
    console.log("--- COPY THE VALUES BELOW ---");
    console.log("PO_TOKEN: " + (window.yt?.config_?.VISITOR_DATA || "Not found (try reloading)"));
    console.log("VISITOR_DATA: " + (window.yt?.config_?.VISITOR_DATA || "Not found"));
    console.log("----------------------------");
})();
```

*Note: Sometimes `po_token` is generated via a complex script. If the above doesn't work, look for network requests to `v1/player` and check the payload for `poToken`.*

## Setting Environment Variables

### locally (.env) or Terminal

```bash
export PO_TOKEN="your_token_here"
export VISITOR_DATA="your_visitor_data_here"
```

### Hugging Face Spaces

1.  Go to **Settings** -> **Variables and Secrets**.
2.  Add a **New Variable**:
    *   Name: `PO_TOKEN`
    *   Value: (Paste your token)
3.  (Optional) Add another Variable:
    *   Name: `VISITOR_DATA`
    *   Value: (Paste visitor data)
4.  Restart the Space.

## Troubleshooting

*   **Token Expired**: PO Tokens are short-lived. You may need to refresh them daily or weekly.
*   **Still Blocked**: Ensure you are also using `cookies.txt` from the **same browser session**.
