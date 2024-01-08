import os
from dotenv import load_dotenv
from translator import Translator


def main():
    load_dotenv()
    file_path = r"C:\Users\Juuso\Desktop\Python\Tekstitykset\Testi\testi.srt"
    target_lang = "fin"

    translator = Translator(file_path, target_lang)
    default_index_range = translator.index_range
    index_range, batch_size, update_translations = translator.get_user_input(default_index_range)
    translator.set_parameters(index_range, batch_size, update_translations)
    translator.process_srt()


if __name__ == "__main__":
    main()