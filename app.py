from flask import Flask, request
from PIL import Image, ImageDraw, ImageFont
import logging
import os
import re
import requests

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + os.sep
BOT_TOKEN = "056560555:AAEtAYTD3yOJV3xLCUo-0UjUgfd0HqS1LDI"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
ALLOWED_CHAT_ID = -4776282039

@app.route("/")
def home():
    return "Barcabot is alive!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update or "message" not in update:
        return "no message", 200

    message = update["message"]
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if chat_id != ALLOWED_CHAT_ID or not re.match(r"^\d+,", text):
        return "ignored", 200

    if text.lower() in ["/start", "hi"]:
        send_message(chat_id, "Welcome to Barcabot! Send me a formation like:\n1,2-3-4,5-6")
        return "ok", 200

    try:
        output_file = generate_formation_image(text)
        send_photo(chat_id, output_file)
        delete_jersey_images()
        return "sent", 200
    except Exception as e:
        send_message(chat_id, f"Oops: {str(e)}")
        return "error", 200

def parse_formation_input(input_str):
    rows = input_str.strip().split(",")
    return [row.strip().split("-") for row in rows]

def create_jersey_image(number, template_path=BASE_DIR + "jersey.png", font_path=BASE_DIR + "font.otf", output_folder=BASE_DIR):
    jersey = Image.open(template_path).convert("RGBA")
    txt_layer = Image.new("RGBA", jersey.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)

    font = ImageFont.truetype(font_path, size=450)

    bbox = draw.textbbox((0, 0), str(number), font=font)
    x_pos = (jersey.width - (bbox[2] - bbox[0])) // 2
    draw.text((x_pos, 180), str(number), font=font, fill=(255, 204, 0, 255))

    result = Image.alpha_composite(jersey, txt_layer)
    output_path = f"{output_folder}jersey_{number}.png"
    result.save(output_path)
    return output_path

def place_jerseys_on_background(formation, background_path=BASE_DIR + "bkg.jpg", output_path=BASE_DIR + "final_formation.png", jersey_folder=BASE_DIR):
    background = Image.open(background_path).convert("RGBA")
    canvas_width, canvas_height = background.size
    row_height = canvas_height // len(formation)

    for r, row in enumerate(formation):
        cell_width = canvas_width // len(row)
        for c, number in enumerate(row):
            jersey_path = f"{jersey_folder}jersey_{number}.png"
            if os.path.exists(jersey_path):
                jersey_img = Image.open(jersey_path).convert("RGBA")
                pos_x = (c * cell_width) + (cell_width - jersey_img.width) // 2
                pos_y = (r * row_height) + (row_height - jersey_img.height) // 2
                background.alpha_composite(jersey_img, (pos_x, pos_y))

    background.save(output_path)
    return output_path

def generate_formation_image(formation_str, output_path=BASE_DIR + "final_formation.png"):
    formation = parse_formation_input(formation_str)
    all_numbers = [num for row in formation for num in row]
    for num in all_numbers:
        create_jersey_image(num)
    return place_jerseys_on_background(formation, output_path=output_path)

def delete_jersey_images(folder=BASE_DIR):
    for filename in os.listdir(folder):
        if filename.startswith("jersey_") and filename.endswith(".png"):
            os.remove(os.path.join(folder, filename))

def send_photo(chat_id, filepath):
    with open(filepath, "rb") as f:
        files = {"document": f}
        data = {"chat_id": chat_id}
        requests.post(f"{BASE_URL}/sendDocument", files=files, data=data)

def send_message(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", data={"chat_id": chat_id, "text": text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
