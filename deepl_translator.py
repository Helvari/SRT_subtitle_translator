import deepl
from dotenv import load_dotenv
import os

load_dotenv()

auth_key = os.getenv("DEEPL_API_KEY")
translator = deepl.Translator(auth_key)


def translate_deepl(original_text, target_lang):
    try:
        result = translator.translate_text(original_text, target_lang=target_lang, preserve_formatting=True)
        return result.text  # Assuming you want to return the translated text
    except Exception as e:
        print(f"Error during translation with DeepL: {e}")
        return None
