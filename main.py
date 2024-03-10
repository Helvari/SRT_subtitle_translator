import os
from dotenv import load_dotenv
from translator_class import Translator


def main():
    load_dotenv()

    file_path = os.getenv('FILE_PATH')
    target_lang = "fi"
    print(file_path)

    translator = Translator(file_path, target_lang)
    translator.select_translation_service()
    default_index_range = translator.index_range
    index_range, batch_size, overwrite_translations = translator.get_user_input(default_index_range)
    translator.set_parameters(index_range, batch_size, overwrite_translations)
    translator.process_srt(overwrite_translations)


if __name__ == "__main__":
    while True:
        main()
        if input("Type 'quit' to exit: ").lower() == 'quit':
            break
