import sqlite3
import os

class DatabaseConnection:
    def __init__(self, db_path):
        # Initialize the database connection with the provided database path
        self.db_path = db_path

    def __enter__(self):
        # Establish and return the database connection when entering the context
        self.conn = sqlite3.connect(self.db_path)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Close the database connection when exiting the context
        self.conn.close()


class DatabaseManager:
    def __init__(self, db_path, overwrite_translations, file_path, index_range=None):
        # Initialize the database manager with configurations for database path,
        # whether to overwrite translations, the file path, and an optional index range
        self.overwrite_translations = overwrite_translations
        self.db_path = db_path
        self.file_path = file_path
        self.index_range = index_range

    def create_table(self):
        # Create a translations table if it doesn't exist
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
            print(f"Error creating table: {e}")

    def check_if_table_exists(self):
        # Check if the translations table exists
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='translations'")
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error checking table: {e}")

    def check_if_data_exists(self):
        # Check if any data exists in the translations table
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM translations')
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            print(f"Error checking data: {e}")

    def save_to_db(self, subtitle_index, timestamp, original_text):
        # Save subtitle data to the database
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO translations (subtitle_index, timestamp, original_text)
                    VALUES (?, ?, ?);
                ''', (str(subtitle_index), str(timestamp), str(original_text)))
                conn.commit()
        except Exception as e:
            print(f"Error saving data to database: {e}")

    def save_translations_to_srt(self, translations_folder, target_lang):
        # Save translated subtitles to an SRT file
        base_name = os.path.splitext(os.path.basename(self.file_path))[0]
        new_file_name = f"{base_name}.{target_lang}.srt"
        translated_file_path = os.path.join(translations_folder, new_file_name)

        try:
            with DatabaseConnection(self.db_path) as conn, open(translated_file_path, 'w', encoding='utf-8') as file:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT subtitle_index, timestamp, translated_text FROM translations ORDER BY subtitle_index')
                rows = cursor.fetchall()

                for subtitle_index, timestamp, translated_text in rows:
                    file.write(f"{subtitle_index}\n{timestamp}\n{translated_text}\n\n")

            print(f"Translated subtitles saved to file: {translated_file_path}")
        except Exception as e:
            print(f"Error saving translations to file: {e}")

    def fetch_rows_to_translate(self, start_index, end_index, overwrite_translations):
        # Fetch rows that need to be translated from the database
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
            print(f"Error fetching data: {e}")

    def get_translation_from_index(self, index):
        # Retrieve a translation from the database by its index
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
            print(f"Error retrieving data: {e}")

    def get_last_translated_index(self):
        # Get the index of the last translated subtitle
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT MIN(subtitle_index) FROM translations WHERE translated_text IS NULL')
                result = cursor.fetchone()
                return result[0] if result[0] is not None else 1
        except Exception as e:
            print(f"Error retrieving last translated index: {e}")

    def get_max_subtitle_index(self):
        # Retrieve the highest subtitle index in the database
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT MAX(subtitle_index) FROM translations')
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Error retrieving max subtitle index: {e}")
            return None

    def update_database(self, translations, update_translations):
        # Update the database with new translations. If update_translations is True, existing translations will be overwritten.
        # If False, only empty (NULL) translation fields will be updated, leaving any existing translations untouched.
        try:
            with DatabaseConnection(self.db_path) as conn:
                cursor = conn.cursor()
                for subtitle_index, translated_text in translations:
                    if update_translations:
                        # Overwrite the translated_text field for the given subtitle_index
                        cursor.execute('''
                            UPDATE translations
                            SET translated_text = ?
                            WHERE subtitle_index = ?;
                        ''', (translated_text, subtitle_index))
                    else:
                        # Only update the translated_text field where it is currently NULL, to avoid overwriting existing translations
                        cursor.execute('''
                            UPDATE translations
                            SET translated_text = ?
                            WHERE subtitle_index = ? AND translated_text IS NULL;
                        ''', (translated_text, subtitle_index))
                conn.commit()
        except Exception as e:
            print(f"Error updating database: {e}")
