import deepl
from dotenv import load_dotenv
import os
from db_func import DatabaseManager

load_dotenv()

auth_key = os.getenv("DEEPL_API_KEY")
translator = deepl.Translator(auth_key)

#result = translator.translate_text("Hello, world!", target_lang="FR", preserve_formatting=True)
#print(result.text)  # "Bonjour, le monde !"


def translate(original_text, target_lang):

    result = translator.translate_text(original_text, target_lang=target_lang, preserve_formatting=True)

    return result
