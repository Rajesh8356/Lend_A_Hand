import pytesseract
from PIL import Image
from deep_translator import GoogleTranslator  # pip install deep-translator

# Path to Tesseract executable (Windows only, adjust if needed)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Open image
img = Image.open(r"C:\Users\nehak\Pictures\rc.jpg")

# Extract Kannada text
text = pytesseract.image_to_string(img, lang="kan")

# Save Kannada text to file
with open("kan_output.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("✅ Kannada text extracted and saved to 'kan_output.txt'")

# --- Translate full text to English ---
translator = GoogleTranslator(source="kn", target="en")
translated_text = translator.translate(text)

# Save English text to file
with open("eng_output.txt", "w", encoding="utf-8") as f:
    f.write(translated_text)

print("✅ English translation saved to 'eng_output.txt'")
print("\n🔹 Full English Translation:\n")
print(translated_text)
