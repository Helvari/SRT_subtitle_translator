import openai
from dotenv import load_dotenv
import os
from database import DatabaseConnection, DatabaseManager

load_dotenv()
client = openai.OpenAI()


class Translator:
    def __init__(self, file_path, target_lang=None, index_range=None, batch_size=5,
                 update_translations=False):

        folder_path = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        self.db_path = os.path.join(folder_path, base_name + ".db")
        self.movie_name = base_name.replace('.', ' ')

        self.file_path = file_path
        self.target_lang = target_lang
        self.update_translations = update_translations
        self.index_range = index_range
        self.batch_size = batch_size
        self.failed_translations = []

        # Luo DatabaseManager-olio ja tarkista tietokannan olemassaolo
        self.database_manager = DatabaseManager(self.db_path)

        if not self.database_manager.check_if_table_exists():
            # Luo tietokanta ja taulu, jos sitä ei ole vielä olemassa
            self.database_manager.create_table()
            # Lue ja tallenna tiedoston sisältö tietokantaan, koska tietokanta luotiin juuri
            self.read_and_store_srt(file_path)
        else:
            # Jos tietokanta on jo olemassa, ei tarvitse lukea tiedostoa uudelleen
            pass

        # Aseta oletusarvoinen indeksiväli, jos sitä ei ole annettu
        if index_range is None:
            start_index, end_index = self.calculate_default_index_range()
            self.index_range = f"{start_index}-{end_index}" if start_index is not None else "1-50"
        else:
            self.index_range = index_range

    def read_srt(self, file_path):
        try:
            with open(file_path, 'r', encoding='ISO-8859-1') as file:
                return file.read()
        except FileNotFoundError:
            print("File not found:", file_path)
            return None

    def read_and_store_srt(self, file_path):
        # Tarkista, onko tietokannassa jo tietoja tästä tiedostosta
        if self.database_manager.check_if_data_exists():
            print("Tietokannassa on jo tiedot tästä tiedostosta. Lukemista ei suoriteta uudelleen.")
            return

        srt_content = self.read_srt(file_path)
        if srt_content is None:
            return

        for line in srt_content.split('\n\n'):
            if line.strip():
                parts = line.split('\n')
                subtitle_index = parts[0]
                timestamp = parts[1]
                original_text = '\n'.join(parts[2:])

                # Tallenna tiedot tietokantaan
                self.database_manager.save_to_db(subtitle_index, timestamp, original_text)

    def is_translation_valid(self, original, translated):
        original_blocks = original.split('\n\n')
        translated_blocks = translated.split('\n\n')

        # Tarkista blokkien määrä
        if len(original_blocks) != len(translated_blocks):
            return False

        # Tarkista rivien määrä blokeissa
        for trans_block in translated_blocks:
            trans_line_count = trans_block.count('\n')
            if trans_line_count > 2:  # Kolme riviä, koska rivinvaihtoja on aina yksi vähemmän kuin rivejä
                return False

        return True

    def translate(self, original_text, subtitle_index):
        max_attempts = 3
        context = self.database_manager.get_translation_from_index(subtitle_index - 1)  # Hae viimeisin käännetty teksti

        for attempt in range(max_attempts):
            try:
                prompt = (
                    f"Translate the following subtitles from their original language into {self.target_lang} for the movie '{self.movie_name}', "
                    f"while preserving the context between sentences. Ensure that your translation is accurate, "
                    f"maintains the same meaning and emotion as the original text, and is natural for {self.target_lang} speakers. "
                    f"Keep the structure, tone, and letter casing as in the original. Pay special attention to the context and flow between sentences, "
                    f"ensuring that the translated subtitles reflect the continuity of dialogue and narrative. "
                    f"Translate each subtitle block separately, keeping the same number of blocks, newlines, and character sizes as in the original subtitles."
                    f"Previous translation (for context): {context}\n\n"
                )
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": original_text}
                    ]
                )
                translated_text = response.choices[0].message.content

                if self.is_translation_valid(original_text, translated_text):
                    return translated_text
                else:
                    if attempt < max_attempts:
                        print(f"Käännösyritys {attempt + 1} tekstille: {original_text[:30]}...")  # Seuraava yritys
                    else:
                        if attempt == max_attempts:
                            self.store_failed_translation(subtitle_index)
                            print("Translation has too many lines or does not match the original. Skipping...")
                            break  # Exit the loop if max attempts are reached

            except openai.APIError as e:
                print(f"OpenAI API returned an API Error: {e}")
                return None

    def store_failed_translation(self, subtitle_index):
        if subtitle_index not in self.failed_translations:
            self.failed_translations.append(subtitle_index)

    def calculate_default_index_range(self):
        start_index = self.database_manager.get_last_translated_index()
        max_index = self.database_manager.get_max_subtitle_index()

        if max_index is None:
            end_index = start_index + 49
        else:
            end_index = min(start_index + 49, max_index)

        return start_index, end_index

    def create_translated_srt(self):
        translated_file_name = f"{self.movie_name}_{self.target_lang.upper() + 'SUB'}.srt"
        translated_file_path = os.path.join(os.path.dirname(self.db_path), translated_file_name)

        with DatabaseConnection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT subtitle_index, timestamp, translated_text FROM translations')
            rows = cursor.fetchall()

        with open(translated_file_path, 'w', encoding='utf-8') as file:
            for subtitle_index, timestamp, translated_text in rows:
                file.write(f"{subtitle_index}\n{timestamp}\n{translated_text}\n\n")

        print(f"Käännetyt tekstitykset tallennettu tiedostoon: {translated_file_path}")

    def get_user_input(self, default_index_range):
        while True:
            index_range_input = input(
                f"Enter index range in format 'start-end' (default {default_index_range}): ").strip()
            batch_size_input = input("Enter the batch size (default 5): ").strip()
            update_translations_input = input("Do you want to update already translated texts? (y/n): ").lower()

            # Asetetaan oletusarvot, jos syötettä ei annettu
            index_range = index_range_input if index_range_input else default_index_range
            batch_size = int(batch_size_input) if batch_size_input.isdigit() else 5
            update_translations = update_translations_input == 'y'

            if '-' in index_range:
                # Jos käyttäjän antama arvo on indeksiväli, kutsutaan process_index_range-funktiota.
                valid, start_index, end_index = self.check_index_range(index_range)
                if valid:
                    index_range = f"{start_index}-{end_index}"  # Aseta uusi end_index
                    break
            else:
                # Jos käyttäjän antama arvo on yksittäinen indeksi, kutsutaan process_single_index-funktiota.
                if self.check_single_index(index_range):
                    break

        return index_range, batch_size, update_translations

    def check_index_range(self, index_range):
        max_index = self.database_manager.get_max_subtitle_index()

        try:
            start_index, end_index = map(int, index_range.split('-'))
            if end_index > max_index:
                end_index = max_index
                print(f"End_index is too big, setting default to {max_index}")
            elif start_index > end_index or start_index < 0:
                raise ValueError
            return True, start_index, end_index  # Indeksiväli on kelvollinen
        except ValueError:
            print("Invalid index range. Please enter a valid range like 'x-y', where x <= y.")
            return False

    def check_single_index(self, index_range):
        max_index = self.database_manager.get_max_subtitle_index()

        try:
            single_index = int(index_range)
            if single_index < 0 or single_index > max_index:
                raise ValueError
            return True  # Yksittäinen indeksi on kelvollinen
        except ValueError:
            print("Invalid index. Please enter a valid single index.")
            return False

    def set_parameters(self, index_range, batch_size, update_translations):
        self.index_range = []
        for part in index_range.split(','):
            part = part.strip()
            if '-' in part:
                self.index_range.append(part)  # Lisää indeksiväli suoraan
            else:
                try:
                    single_index = int(part)
                    self.index_range.append(
                        f"{single_index}-{single_index}")  # Muunna yksittäinen indeksi indeksiväliksi
                except ValueError:
                    print(f"Invalid index: {part}")

        self.batch_size = batch_size
        self.update_translations = update_translations



    def commit_translations_to_db(self, translations_to_update):
        # Kutsu yleistä päivitysmetodia update_database
        self.database_manager.update_database(translations_to_update, self.update_translations)

    def process_and_translate_range(self, start_index, end_index, batch_size):
        current_index = start_index
        commit_interval = 50
        translations_count = 0
        translations_to_update = []

        while current_index <= end_index:
            next_index = min(current_index + batch_size - 1, end_index)
            print(f"Käännös riveille {current_index}-{next_index}...")

            # Hae rivit riippuen update_translations-arvosta
            rows_to_translate = self.database_manager.fetch_rows_to_translate(current_index, next_index)

            # Suorita käännökset ja kerää niiden tiedot
            for subtitle_index, original_text in rows_to_translate:
                translated_text = self.translate(original_text, subtitle_index)
                translations_to_update.append((subtitle_index, translated_text))

                translations_count += 1
                if translations_count >= commit_interval or next_index == end_index:
                    self.commit_translations_to_db(translations_to_update)
                    translations_to_update = []  # Tyhjennä lista uusia käännöksiä varten
                    translations_count = 0

            current_index = next_index + 1

        # Päivitä jäljelle jäävät käännökset
        if translations_to_update:
            self.commit_translations_to_db(translations_to_update)

    def process_srt(self):
        print("\nAloitetaan kääntäminen...\n")

        try:
            # 1. Tarkista indeksiväli
            if not self.index_range:
                # Laske oletusarvoinen indeksiväli, jos sitä ei ole annettu
                start_index, end_index = self.calculate_default_index_range(self.db_path)
                self.index_range = [f"{start_index}-{end_index}"]  # Lisää oletusarvoinen indeksiväli listaan

            # 2. Käännä ja päivitä tietokanta erittäin annetun indeksivälin ja batch_size:n mukaan
            for index_range in self.index_range:
                start_index, end_index = map(int, index_range.split('-'))
                print(f"Käsitellään indeksiväliä {start_index}-{end_index}...\n")
                self.process_and_translate_range(start_index, end_index,
                                                 self.batch_size)

            # 3. Luo uusi .srt-tiedosto käännetyillä tekstityksillä
            self.create_translated_srt()

            print("Virheelliset käännökset: " + ', '.join(self.failed_translations))

        except ValueError:
            print("Virheellinen syöte.")
