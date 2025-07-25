from playwright.sync_api import sync_playwright
import os
from PIL import Image, ImageChops, ImageDraw
import requests

# --- CONFIG ---
URL = "https://ht-ctc.techponder.com"
SCREENSHOT_DIR = "screenshots"
NAME = "techponder"

# Ensure screenshot folder exists
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

prev_path = os.path.join(SCREENSHOT_DIR, f"{NAME}_prev.png")
curr_path = os.path.join(SCREENSHOT_DIR, f"{NAME}_curr.png")
diff_path = os.path.join(SCREENSHOT_DIR, f"{NAME}_diff_highlighted.png")

# --- TAKE SCREENSHOT ---
def take_screenshot(path):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle")
        page.screenshot(path=path, full_page=True)
        browser.close()

# --- COMPARE IMAGES ---
def compare_images(img1_path, img2_path):
    if not os.path.exists(img1_path) or not os.path.exists(img2_path):
        return False
    img1 = Image.open(img1_path)
    img2 = Image.open(img2_path)
    diff = ImageChops.difference(img1, img2)
    return diff.getbbox() is not None

# --- HIGHLIGHT DIFFERENCE ---
def highlight_difference(img1_path, img2_path, output_path):
    img1 = Image.open(img1_path)
    img2 = Image.open(img2_path)
    diff = ImageChops.difference(img1, img2)
    bbox = diff.getbbox()
    if bbox:
        annotated = img2.copy()
        draw = ImageDraw.Draw(annotated)
        draw.rectangle(bbox, outline="red", width=5)
        draw.text((bbox[0], bbox[1] - 20), "Change Detected", fill="red")
        annotated.save(output_path)
        print(f"📸 Saved diff image with highlight: {output_path}")

# --- SEND EMAIL ALERT VIA BREVO ---
def send_email_alert(subject, body):
    api_key = os.environ["BREVO_API_KEY"]
    recipient = os.environ["RECIPIENT_EMAIL"]

    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }

    data = {
        "sender": {"name": "Website Monitor", "email": "monitor@yourdomain.com"},
        "to": [{"email": recipient}],
        "subject": subject,
        "htmlContent": f"<p>{body}</p>"
    }

    response = requests.post("https://api.brevo.com/v3/smtp/email", json=data, headers=headers)

    if response.status_code == 201:
        print("📧 Email sent via Brevo!")
    else:
        print(f"❌ Failed to send email: {response.status_code} - {response.text}")

# --- SCRIPT FLOW ---

# Step 1: Move curr → prev if exists
if os.path.exists(curr_path):
    os.replace(curr_path, prev_path)

# Step 2: Take new screenshot
take_screenshot(curr_path)

# Step 3: Compare and take action
if os.path.exists(prev_path):
    if compare_images(prev_path, curr_path):
        print(f"⚠️  Change detected on {URL}")
        highlight_difference(prev_path, curr_path, diff_path)

        send_email_alert(
            subject=f"🔔 Change Detected on {URL}",
            body=f"A change was detected on <a href='{URL}'>{URL}</a>.<br>Check your GitHub repo for <b>{os.path.basename(diff_path)}</b>."
        )
    else:
        print("✅ No change detected.")
else:
    print("🆕 First screenshot captured.")
