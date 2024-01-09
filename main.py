import os
from dotenv import load_dotenv
from translator import Translator


def main():
    # Lataa .env-tiedoston ympäristömuuttujat
    load_dotenv()

    # Hae file_path .env-tiedostosta
    file_path = os.getenv('FILE_PATH')
    target_lang = "fin"

    translator = Translator(file_path, target_lang)
    default_index_range = translator.index_range
    index_range, batch_size, overwrite_translations = translator.get_user_input(default_index_range)
    translator.set_parameters(index_range, batch_size, overwrite_translations)
    translator.process_srt(overwrite_translations)


if __name__ == "__main__":
    main()