import telebot
from telebot import types
from deep_translator import GoogleTranslator
import whisper
from gtts import gTTS
import pytesseract
from PIL import Image
from docx import Document
import PyPDF2
import os
import tempfile

# --------------------------------
#         BOT TOKEN
# --------------------------------
TOKEN = "8363490190:AAH-lpaDi20cH3CCqCqj1RdBfwLdgcX4dBY"   # <<< TOKENNI SHU YERGA QO'YING
bot = telebot.TeleBot(TOKEN)

# --------------------------------
#      WHISPER STT MODELI
# --------------------------------
print("Whisper modeli yuklanmoqda...")
model = whisper.load_model("base")
print("Whisper yuklandi.")

# --------------------------------
#       TARJIMA FUNKSIYALARI (TUZATILGAN)
# --------------------------------

def uz_to_cn(text):
    return GoogleTranslator(source='uz', target='zh-CN').translate(text)

def cn_to_uz(text):
    return GoogleTranslator(source='zh-CN', target='uz').translate(text)

def is_chinese(text):
    return any('\u4e00' <= ch <= '\u9fff' for ch in text)

def auto_translate(text):
    if is_chinese(text):
        return cn_to_uz(text)
    else:
        return uz_to_cn(text)

# --------------------------------
#         OCR FUNKSIYASI
# --------------------------------

def ocr_image(path):
    try:
        text = pytesseract.image_to_string(Image.open(path), lang="chi_sim+eng")
        return text.strip()
    except:
        return ""

# --------------------------------
#     AUDIO → MATN (WHISPER)
# --------------------------------

def speech_to_text(path):
    try:
        result = model.transcribe(path)
        return result["text"].strip()
    except Exception as e:
        return f"[Xatolik] {e}"

# --------------------------------
#  MATN → XITOYCHA OVOZ (gTTS)
# --------------------------------

def text_to_speech(text, out_path):
    tts = gTTS(text=text, lang='zh-CN')
    tts.save(out_path)
    return out_path

# --------------------------------
#        PDF MATN OQISH
# --------------------------------

def extract_text_from_pdf(path):
    text = ""
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text.strip()

# --------------------------------
#       DOCX MATN OQISH
# --------------------------------

def extract_text_from_docx(path):
    doc = Document(path)
    return "\n".join([p.text for p in doc.paragraphs]).strip()

# --------------------------------
#             START
# --------------------------------

@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message,
    "🇨🇳🇺🇿 Salom! Men Uzbek ↔ Xitoy tarjimon botman.\n\n"
    "Menga:\n"
    "• Matn yuboring → Tarjima + Xitoycha ovoz\n"
    "• Ovoz yuboring → Ovozdan matn qilib tarjima\n"
    "• Rasm yuboring → OCR + tarjima\n"
    "• PDF / DOCX yuboring → tarjima\n"
    "/tts <matn> → xitoycha ovoz yaratish"
    )

# --------------------------------
#       /tts — Matn → Ovoz
# --------------------------------

@bot.message_handler(commands=["tts"])
def tts_command(message):
    text = message.text.replace("/tts", "").strip()
    if not text:
        bot.reply_to(message, "Foydalanish:\n/tts Salom")
        return

    tmp = tempfile.mktemp(suffix=".mp3")
    text_to_speech(text, tmp)
    bot.send_voice(message.chat.id, open(tmp, "rb"))
    os.remove(tmp)

# --------------------------------
#     MATN TARJIMASI + OVOZ
# --------------------------------

@bot.message_handler(func=lambda msg: msg.text is not None and not msg.text.startswith("/"))
def translate_text(message):
    text = message.text.strip()
    translated = auto_translate(text)

    # Matnni yuborish
    bot.reply_to(message, translated)

    # Tarjima ovozini yuborish
    tmp = tempfile.mktemp(suffix=".mp3")
    text_to_speech(translated, tmp)
    bot.send_voice(message.chat.id, open(tmp, "rb"))
    os.remove(tmp)

# --------------------------------
#      VOICE MESSAGE (OGG)
# --------------------------------

@bot.message_handler(content_types=["voice"])
def voice_handler(message):
    file_info = bot.get_file(message.voice.file_id)
    ogg_path = tempfile.mktemp(suffix=".ogg")
    downloaded = bot.download_file(file_info.file_path)

    with open(ogg_path, "wb") as f:
        f.write(downloaded)

    text = speech_to_text(ogg_path)
    translated = auto_translate(text)

    bot.reply_to(message, f"Matn:\n{text}\n\nTarjima:\n{translated}")

    # Tarjima ovozi
    tmp = tempfile.mktemp(suffix=".mp3")
    text_to_speech(translated, tmp)
    bot.send_voice(message.chat.id, open(tmp, "rb"))

    os.remove(tmp)
    os.remove(ogg_path)

# --------------------------------
#      AUDIO FILE (.mp3, .wav)
# --------------------------------

@bot.message_handler(content_types=["audio"])
def audio_handler(message):
    file_info = bot.get_file(message.audio.file_id)
    ext = os.path.splitext(message.audio.file_name)[1]
    path = tempfile.mktemp(suffix=ext)
    downloaded = bot.download_file(file_info.file_path)

    with open(path, "wb") as f:
        f.write(downloaded)

    text = speech_to_text(path)
    translated = auto_translate(text)

    bot.reply_to(message, translated)

    # Xitoycha ovoz
    tmp = tempfile.mktemp(suffix=".mp3")
    text_to_speech(translated, tmp)
    bot.send_voice(message.chat.id, open(tmp, "rb"))

    os.remove(tmp)
    os.remove(path)

# --------------------------------
#         RASM (OCR)
# --------------------------------

@bot.message_handler(content_types=["photo"])
def photo_handler(message):
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)

    img_path = tempfile.mktemp(suffix=".jpg")
    downloaded = bot.download_file(file_info.file_path)

    with open(img_path, "wb") as f:
        f.write(downloaded)

    text = ocr_image(img_path)
    translated = auto_translate(text)

    bot.reply_to(message, f"🖼 Matn:\n{text}\n\nTarjima:\n{translated}")

    # Tarjima ovoz
    tmp = tempfile.mktemp(suffix=".mp3")
    text_to_speech(translated, tmp)
    bot.send_voice(message.chat.id, open(tmp, "rb"))

    os.remove(tmp)
    os.remove(img_path)

# --------------------------------
#       PDF / DOCX TARJIMASI
# --------------------------------

@bot.message_handler(content_types=["document"])
def document_handler(message):
    doc = message.document
    file_info = bot.get_file(doc.file_id)

    ext = os.path.splitext(doc.file_name)[1].lower()
    path = tempfile.mktemp(suffix=ext)
    downloaded = bot.download_file(file_info.file_path)

    with open(path, "wb") as f:
        f.write(downloaded)

    if ext == ".pdf":
        text = extract_text_from_pdf(path)
    elif ext == ".docx":
        text = extract_text_from_docx(path)
    else:
        bot.reply_to(message, "Faqat PDF yoki DOCX tarjima qilaman.")
        return

    translated = auto_translate(text)
    bot.reply_to(message, translated[:4000])

    # Tarjima ovozi
    tmp = tempfile.mktemp(suffix=".mp3")
    text_to_speech(translated[:500], tmp)  # juda uzun bo‘lmasligi uchun 500 ta belgi
    bot.send_voice(message.chat.id, open(tmp, "rb"))

    os.remove(tmp)
    os.remove(path)

# --------------------------------
#        BOTNI ISHGA TUSHIRISH
# --------------------------------

bot.infinity_polling()
