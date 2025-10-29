import pytesseract
from PIL import Image

# Path to Tesseract executable (Windows only, adjust if needed)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Open image
img = Image.open("C:\\Users\\nehak\\Pictures\\rtcc.png")


# Extract Kannada text
text = pytesseract.image_to_string(img, lang="kan")

# Save to file
with open("kannada_output.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("✅ Kannada text extracted and saved to 'kannada_output.txt'")