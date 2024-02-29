import openai
from dotenv import load_dotenv
import os
from db_func import DatabaseConnection, DatabaseManager
import re
from openai_translator import translate
from colorama import Fore, Style, init

init(autoreset=True)

load_dotenv()
client = openai.OpenAI()

failed_translations = []


def read_srt(file_path):
    try:
        with open(file_path, 'r', encoding='ISO-8859-1') as file:
            return file.read()
    except FileNotFoundError:
        print("File not found:", file_path)
        return None


def is_translation_valid(original, translated):
    original_blocks = original.split('\n\n')
    translated_blocks = translated.split('\n\n')

    if len(original_blocks) != len(translated_blocks):
        return False

    for trans_block in translated_blocks:
        trans_line_count = trans_block.count('\n')
        if trans_line_count > 2:
            return False

    return True


class Translator:
    def __init__(self, file_path, target_lang=None, index_range=None, batch_size=5, overwrite_translations=False):

        folder_path = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        self.db_path = os.path.join(folder_path, base_name + ".db")
        self.movie_name = base_name.replace('.', ' ')

        self.file_path = file_path
        self.target_lang = target_lang
        self.overwrite_translations = overwrite_translations
        self.index_range = index_range
        self.batch_size = batch_size

        self.database_manager = DatabaseManager(self.db_path, self.overwrite_translations, self.file_path)

        if not self.database_manager.check_if_table_exists():
            self.database_manager.create_table()
            self.read_and_store_srt(file_path)
        else:
            pass

        if index_range is None:
            start_index, end_index = self.calculate_default_index_range()
            self.index_range = f"{start_index}-{end_index}" if start_index is not None else "1-50"
        else:
            self.index_range = index_range

    def read_and_store_srt(self, file_path):
        if self.database_manager.check_if_data_exists():
            print("Tietokannassa on jo tiedot tästä tiedostosta. Lukemista ei suoriteta uudelleen.")
            return

        srt_content = read_srt(file_path)
        if srt_content is None:
            return

        for line in srt_content.split('\n\n'):
            if line.strip():
                parts = line.split('\n')
                subtitle_index = parts[0]
                timestamp = parts[1]
                original_text = '\n'.join(parts[2:])

                self.database_manager.save_to_db(subtitle_index, timestamp, original_text)

    def translate_with_openai(self, original_text, subtitle_index):
        # Käytä 'self.target_lang' kohdekieleen ja 'self.movie_name' elokuvan nimeen
        # 'context' voidaan hakea tietokannasta tai jättää tyhjäksi alustavasti
        context = self.database_manager.get_translation_from_index(subtitle_index - 1)

        # Kutsu 'translate' funktiota 'openai_translator.py' tiedostosta
        translated_text = translate(
            original_text=original_text,
            target_lang=self.target_lang,
            movie_name=self.movie_name,
            context=context
        )

        return translated_text

    def translate_with_deepl(self, original_text):

        translated_text = translate(original_text, self.target_lang)

        return translated_text

    def calculate_default_index_range(self):
        start_index = self.database_manager.get_last_translated_index()
        max_index = self.database_manager.get_max_subtitle_index()

        if max_index is None:
            end_index = start_index + 49
        else:
            end_index = min(start_index + 49, max_index)

        return start_index, end_index

    def create_translated_srt(self):
        # Oletetaan, että self.movie_name sisältää tiedostonimen ilman .srt päätettä
        # Etsitään mahdollinen kielikoodi tiedostonimen lopusta
        pattern = re.compile(r"(.+?)(?:\.([a-z]{2}))?\.srt$", re.IGNORECASE)
        match = pattern.match(self.movie_name)

        if match:
            # Otetaan tiedoston perusnimi ja mahdollinen kielikoodi
            base_name, current_lang = match.groups()
            # Jos alkuperäisessä tiedostonimessä ei ole kielikoodia, current_lang on None
            new_file_name = f"{base_name}.{self.target_lang}.srt"
        else:
            # Jos tiedostonimi ei vastaa odotettua muotoa, käytetään alkuperäistä logiikkaa
            new_file_name = f"{self.movie_name}.{self.target_lang}.srt"

        translated_file_path = os.path.join(os.path.dirname(self.db_path), new_file_name)

        with DatabaseConnection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT subtitle_index, timestamp, translated_text FROM translations')
            rows = cursor.fetchall()

        with open(translated_file_path, 'w', encoding='utf-8') as file:
            for subtitle_index, timestamp, translated_text in rows:
                file.write(f"{subtitle_index}\n{timestamp}\n{translated_text}\n\n")

        print(f"Käännetyt tekstitykset tallennettu tiedostoon: {translated_file_path}")

    def get_user_input(self, default_index_range):
        load_dotenv()
        default_file_path = os.getenv('FILE_PATH', None)

        '''file_path_input = input(
            f"Enter the file path or press Enter to use the default ({default_file_path}): ").strip()
        file_path = file_path_input if file_path_input else default_file_path
        print(f"Using file path: {file_path}\n")

        while True:
            action_choice = input("Press 1 to adjust timing, 2 to start translation: ").strip()
            if action_choice in ['1', '2']:
                break
            else:
                print("Invalid choice, please press 1 or 2.")'''

        while True:
            index_range_input = input(
                f"Enter index range in format 'start-end' (default {default_index_range}): ").strip()
            index_range = index_range_input if index_range_input else default_index_range
            print(f"Setting index_range to {index_range}\n")

            batch_size_input = input("Enter the batch size (default 5): ").strip()
            batch_size = int(batch_size_input) if batch_size_input.isdigit() else 5
            print(f"Setting batch_size to {batch_size}\n")

            overwrite_translations_input = input("Do you want to update already translated texts? (y/n): ").lower()
            overwrite_translations = overwrite_translations_input == 'y'
            print(f"Setting overwrite_translations to {overwrite_translations}\n")

            if '-' in index_range:
                valid, start_index, end_index = self.check_index_range(index_range)
                if valid:
                    index_range = f"{start_index}-{end_index}"
                    break
            else:
                if self.check_single_index(index_range):
                    break

        return index_range, batch_size, overwrite_translations

    def check_index_range(self, index_range):
        max_index = self.database_manager.get_max_subtitle_index()

        try:
            start_index, end_index = map(int, index_range.split('-'))
            if end_index > max_index:
                end_index = max_index
                print(f"End_index is too big, setting default to {max_index}")
            elif start_index > end_index or start_index < 0:
                raise ValueError
            return True, start_index, end_index
        except ValueError:
            print("Invalid index range. Please enter a valid range like 'x-y', where x <= y.")
            return False

    def check_single_index(self, index_range):
        max_index = self.database_manager.get_max_subtitle_index()

        try:
            single_index = int(index_range)
            if single_index < 0 or single_index > max_index:
                raise ValueError
            return True
        except ValueError:
            print("Invalid index. Please enter a valid single index.")
            return False

    def set_parameters(self, index_range, batch_size, overwrite_translations):
        self.index_range = []
        for part in index_range.split(','):
            part = part.strip()
            if '-' in part:
                self.index_range.append(part)
            else:
                try:
                    single_index = int(part)
                    self.index_range.append(
                        f"{single_index}-{single_index}")
                except ValueError:
                    print(f"Invalid index: {part}")

        self.batch_size = batch_size
        self.overwrite_translations = overwrite_translations

    def process_and_translate_range(self, start_index, end_index, batch_size, overwrite_translations):
        current_index = start_index
        commit_interval = 50
        translations_count = 0
        translations_to_update = []
        global failed_translations

        while current_index <= end_index:
            next_batch_index = min(current_index + batch_size - 1, end_index)
            print(f"Käännös riveille {current_index}-{next_batch_index}...")

            rows_to_translate = self.database_manager.fetch_rows_to_translate(current_index, next_batch_index,
                                                                              self.overwrite_translations)
            batch_text = '\n\n'.join([row[1] for row in rows_to_translate])

            # print(batch_text)

            translated_text = None
            attempts = 0
            max_attempts = 5
            while attempts < max_attempts:
                translated_text = self.translate_with_openai(batch_text, current_index)
                attempts += 1

                # print(translated_text)

                if translated_text and is_translation_valid(batch_text, translated_text):
                    print(
                        f"Käännösyritys {attempts} " + Fore.GREEN + "onnistui" + Style.RESET_ALL + f" riveille {current_index}-{next_batch_index}.")
                    translated_blocks = translated_text.split('\n\n')

                    for i, block in enumerate(translated_blocks):
                        subtitle_index = rows_to_translate[i][0]
                        translations_to_update.append((subtitle_index, block))

                    translations_count += len(rows_to_translate)
                    if translations_count >= commit_interval or next_batch_index == end_index:
                        self.database_manager.update_database(translations_to_update, overwrite_translations)
                        translations_to_update = []
                        translations_count = 0
                    break
                else:
                    print(
                        f"Käännösyritys {attempts} " + Fore.RED + "epäonnistui" + Style.RESET_ALL + f" riveille {current_index}-{next_batch_index}.")

                if attempts == max_attempts:
                    print(
                        f"Kaikki käännösyritykset " + Fore.RED + "epäonnistuivat" + Style.RESET_ALL + f" riveille {current_index}-{next_batch_index}. Lisätään epäonnistuneiden listaan."
                    )
                    failed_translations.extend([row[0] for row in rows_to_translate])

            current_index = next_batch_index + 1

        if translations_to_update:
            self.database_manager.update_database(translations_to_update, overwrite_translations)

    def process_srt(self, overwrite_translations):
        print("\nAloitetaan kääntäminen...\n")

        try:
            for index_range in self.index_range:
                start_index, end_index = map(int, index_range.split('-'))
                print(f"Käsitellään indeksiväliä {start_index}-{end_index}...\n")
                self.process_and_translate_range(start_index, end_index, self.batch_size, overwrite_translations)

            self.create_translated_srt()

            if failed_translations:
                print(f"Epäonnistuneiden käännösten indeksit ennen uudelleenkäännöksiä: {failed_translations}")
                temp_failed_translations = failed_translations[:]
                failed_translations.clear()  # Tyhjennä alkuperäinen lista ennen uudelleenkäännöksiä

                retry = input("Haluatko yrittää uudelleen epäonnistuneiden käännösten kääntämistä? (k/e): ")
                if retry.lower() == 'k':
                    for index in temp_failed_translations:
                        self.process_and_translate_range(index, index, 1, overwrite_translations)

                if failed_translations:
                    print(f"Epäonnistuneiden käännösten indeksit uudelleenkäännösten jälkeen: {failed_translations}")
                else:
                    print("Kaikki uudelleenkäännökset onnistuivat, epäonnistuneiden lista on nyt tyhjä.")

        except ValueError:
            print("Virheellinen syöte.")
