# Vinted Wardrobe Exporter

![License](https://img.shields.io/badge/License-MIT-blue)

A Python utility to export your entire Vinted wardrobe, including item details, images, and statistics.

## Features

- Exports all items from a Vinted user's wardrobe
- Downloads all item photos in full resolution
- Saves detailed metadata, human-readable summaries, and statistics
- Packages everything into a convenient ZIP archive
- Works with any Vinted country domain (vinted.fr, vinted.de, vinted.cz, etc.)

## ⚡️ Why use this vs. Official Data Export?

While Vinted offers an [official account data export](https://www.vinted.co.uk/help/1374), this tool offers several distinct advantages (and disadvantages) depending on your needs:

| Feature | This Exporter Tool | Official Vinted Export |
| :--- | :--- | :--- |
| **Speed** | **Instant.** No waiting time. | Can take days to be sent to you. |
| **Image Quality** | **Higher Quality.** Downloads less compressed images. | Compressed. |
| **Access** | **Any Public Profile.** Can backup accounts even without login credentials (if public). | Only accessible if you can log in. |
| **Scope** | **Listings Only.** Focuses on items, photos, and descriptions. | Includes private messages, settings, and logs. |
| **Stability** | **Fragile.** Relies on web scraping; may break if site changes. | Guaranteed structure. |

**Summary:** Use this tool if you need an instant backup of your *listings* and *photos* (e.g., for migrating accounts), or if you need to recover data from a public profile you can no longer access. Use the official export for legal data requests or private account history.

## Warning ⚠️

**Use at your own risk.** While this tool uses publicly available endpoints, it is not an official Vinted tool. Vinted might consider automated access against their Terms of Service. Users carry full responsibility for any consequences, which could potentially include account restrictions or bans.

This tool is intended for personal data backup purposes only.

## Use Case: Account Country Migration

Vinted doesn't provide functionality to change your account's country. According to [their official help article](https://www.vinted.com/help/1231-how-can-i-change-my-country-on-vinted), they recommend creating a new account if you've moved to a different country.

However, Vinted has been known to automatically detect and ban duplicate accounts. This tool can help with a safer migration process:

1. Download your wardrobe data using this tool
2. Verify the export contains all your listings
3. Back up the ZIP file safely
4. Delete all your listings from your old account
5. Delete your old account
6. Create a new account in your new country
7. Upload your items to the new account

This workflow helps minimize the risk of being detected as a duplicate account while following Vinted's recommendation to create a new account for a different country.

## Prerequisites

- Python 3.7 or higher
- Chrome/Firefox with Developer Tools for cookie extraction

## Installation

1. Clone this repository:
   ```bash
   git clone [https://github.com/yourusername/vinted-wardrobe-exporter.git](https://github.com/yourusername/vinted-wardrobe-exporter.git)
   cd vinted-wardrobe-exporter
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   or
   ```bash
   pip install requests beautifulsoup4 tqdm
   ```

## Usage

### 1. Get your Vinted cookies

1. Log in to your Vinted account in Chrome or Firefox
2. Open Developer Tools (F12 or right-click → Inspect)
3. Go to the Network tab
4. Filter for "items?" (API request)
5. Select any request to this endpoint
6. Go to the Cookies tab
7. Right click anywhere in Request Cookies and select Copy All
8. Save them to a file named `cookies.json` in the same directory as the script

Example cookies.json format:

```json
{
  "Request Cookies": {
    "__cf_bm": "YOUR_VALUE_HERE",
    "__podscribe_did": "YOUR_VALUE_HERE",
    "__podscribe_vinted_landing_url": "YOUR_VALUE_HERE",
    "__podscribe_vinted_referrer": "YOUR_VALUE_HERE",
    "_dd_s": "YOUR_VALUE_HERE",
    "_ga": "YOUR_VALUE_HERE",
    "_vinted_fr_session": "YOUR_VALUE_HERE",
    "access_token_web": "YOUR_VALUE_HERE",
    "anon_id": "YOUR_VALUE_HERE",
    "cf_clearance": "YOUR_VALUE_HERE",
    "datadome": "YOUR_VALUE_HERE",
    "refresh_token_web": "YOUR_VALUE_HERE",
    "v_sid": "YOUR_VALUE_HERE",
    "v_uid": "YOUR_VALUE_HERE"
  }
}

```

Note: Your cookies.json will contain more fields than shown in this example. The important cookies are `_vinted_fr_session`, `access_token_web`, and `refresh_token_web`.

### 2. Run the script

```bash
python3 vinted-wardrobe-exporter.py

```

### 3. Follow the prompts

* Enter your Vinted profile URL (e.g., vinted.fr/member/12345-username)
* Specify a filename for the ZIP archive (or accept the default)

### 4. Wait for the export to complete

The script will:

* Scan your wardrobe
* Download all item details and photos
* Create a ZIP archive with everything

## Output Format

The export creates a ZIP file with the following structure:

```
wardrobe_12345.zip
├── 123456/
│   ├── metadata.json         # Full item metadata
│   ├── summary.txt           # Human-readable item details
│   ├── stats.txt             # Views and favorites
│   ├── 7654321.jpg           # Item photo 1
│   ├── 7654322.jpg           # Item photo 2
│   └── ...
├── 123457/
│   └── ...
└── ...

```

## Limitations

* The script can only export items from public wardrobes
* You must be logged in (with valid cookies) to access most information
* Rate limiting may affect exports of very large wardrobes
* Closed/sold listings are skipped by default

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is not affiliated with, endorsed by, or connected to Vinted in any way. Use it responsibly and at your own risk.
