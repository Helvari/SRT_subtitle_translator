import sqlite3


class DatabaseConnection:
    def __init__(self, db_path):
        self.db_path = db_path

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()


class DatabaseManager:
    def __init__(self, db_path, overwrite_translations):
        self.overwrite_translations = overwrite_translations
        self.db_path = db_path

    def create_table(self):
        try:
            with DatabaseConnection(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS translations (
                        subtitle_index INTEGER PRIMARY KEY,
                        timestamp TEXT,
                        original_text TEXT,
                        translated_text TEXT
                    );
                ''')
        except Exception as e:
            print(f"Virhe taulun luonnissa: {e}")

    def check_if_table_exists(self):
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='translations'")
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"Virhe taulun tarkistamisessa: {e}")

    def check_if_data_exists(self):
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM translations')
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            print(f"Virhe datan tarkistamisessa: {e}")

    def save_to_db(self, subtitle_index, timestamp, original_text):
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO translations (subtitle_index, timestamp, original_text)
                    VALUES (?, ?, ?);
                ''', (subtitle_index, timestamp, original_text))
                conn.commit()
        except Exception as e:
            print(f"Virhe datan tallentamisessa tietokantaan: {e}")

    def fetch_rows_to_translate(self, start_index, end_index, overwrite_translations):
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                if overwrite_translations:
                    cursor.execute('''
                        SELECT subtitle_index, original_text
                        FROM translations
                        WHERE subtitle_index >= ? AND subtitle_index <= ?
                    ''', (start_index, end_index))
                else:
                    cursor.execute('''
                        SELECT subtitle_index, original_text
                        FROM translations
                        WHERE subtitle_index >= ? AND subtitle_index <= ? AND translated_text IS NULL
                    ''', (start_index, end_index))
                return cursor.fetchall()
        except Exception as e:
            print(f"Virhe datan hakemisessa: {e}")

    def get_translation_from_index(self, index):
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT translated_text FROM translations
                    WHERE subtitle_index = ? AND translated_text IS NOT NULL
                ''', (index,))
                result = cursor.fetchone()
                return result[0] if result else ""
        except Exception as e:
            print(f"Virhe datan hakemisessa: {e}")

    def get_last_translated_index(self):
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT MIN(subtitle_index) FROM translations WHERE translated_text IS NULL')
                result = cursor.fetchone()
                return result[0] if result[0] is not None else 1
        except Exception as e:
            print(f"Virhe datan hakemisessa: {e}")

    def get_max_subtitle_index(self):
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT MAX(subtitle_index) FROM translations')
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Virhe haettaessa max_subtitle_index: {e}")
            return None

    def update_database(self, translations, update_translations):
        # print(f"Updating database with update_translations={update_translations}")
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                for subtitle_index, translated_text in translations:
                    if update_translations:
                        # print(f"Updating subtitle_index={subtitle_index} with new translation")
                        # Päivitetään kaikki käännökset
                        cursor.execute('''
                            UPDATE translations
                            SET translated_text = ?
                            WHERE subtitle_index = ?;
                        ''', (translated_text, subtitle_index))
                    else:
                        # print(f"Writing new translation only for subtitle_index={subtitle_index}")
                        # Päivitetään vain uudet käännökset
                        cursor.execute('''
                            UPDATE translations
                            SET translated_text = ?
                            WHERE subtitle_index = ? AND translated_text IS NULL;
                        ''', (translated_text, subtitle_index))
                conn.commit()
        except Exception as e:
            print(f"Virhe tietokannan päivittämisessä: {e}")