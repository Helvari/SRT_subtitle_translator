from dotenv import load_dotenv
import os
from db_func import DatabaseManager
import re
from openai_translator import translate_openai
from deepl_translator import translate_deepl
from colorama import Fore, Style, init

# Automatically reset styling after each print statement
init(autoreset=True)

# Load environment variables from .env file
load_dotenv()

# A list to keep track of indices of translations that failed
failed_translations = []


def read_srt(file_path):
    try:
        # Open the SRT file with the specified encoding
        with open(file_path, 'r', encoding='ISO-8859-1') as file:
            return file.read()
    except FileNotFoundError:
        # Print an error message if the file is not found
        print("File not found:", file_path)
        return None


def is_translation_valid(original, translated):
    # Split the original and translated text by double newlines to get blocks
    original_blocks = original.split('\n\n')
    translated_blocks = translated.split('\n\n')

    # Check if the number of blocks in both texts are equal
    if len(original_blocks) != len(translated_blocks):
        return False

    # Ensure that each translated block has no more than two newlines
    for trans_block in translated_blocks:
        trans_line_count = trans_block.count('\n')
        if trans_line_count > 2:
            return False

    # Return True if the translation is considered valid
    return True


def clean_html_tags(text):
    # Use regular expressions to remove HTML tags from the text
    clean_text = re.sub(r'<[^>]+>', '', text)
    return clean_text


class Translator:
    def __init__(self, file_path, target_lang=None, index_range=None, batch_size=5, overwrite_translations=False):

        # Get the folder path and base name of the file
        folder_path = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]

        # Remove any language suffix from the file name
        base_name = re.sub(r'\.[a-z]{2,3}$', '', base_name)

        # Define the new folder path for the database and translations
        subtitle_db_folder = os.path.join(folder_path, "Subtitle Database")
        translation_folder = os.path.join(folder_path, "Translations")

        # Create the folders if they do not exist
        if not os.path.exists(subtitle_db_folder):
            os.makedirs(subtitle_db_folder)
        if not os.path.exists(translation_folder):
            os.makedirs(translation_folder)

        # Update db_path and translations_path to point to the new folders
        self.db_path = os.path.join(subtitle_db_folder, base_name + ".db")
        self.translations_path = translation_folder
        self.movie_name = base_name

        # Initialize the rest of the variables
        self.file_path = file_path
        self.target_lang = target_lang
        self.overwrite_translations = overwrite_translations
        self.index_range = index_range
        self.batch_size = batch_size
        self.translation_service = None

        # Create a database manager instance
        self.database_manager = DatabaseManager(self.db_path, self.overwrite_translations, self.file_path)

        # Check if the translations table exists, create it if not, and read/store the SRT file
        if not self.database_manager.check_if_table_exists():
            self.database_manager.create_table()
            self.read_and_store_srt(file_path)

        # Set the default index range if not specified
        if index_range is None:
            start_index, end_index = self.calculate_default_index_range()
            self.index_range = f"{start_index}-{end_index}" if start_index is not None else "1-50"
        else:
            self.index_range = index_range

    def read_and_store_srt(self, file_path):
        # Check if the database already has data for this file to avoid re-reading
        if self.database_manager.check_if_data_exists():
            print("The database already has information on this file. Reading will not be performed again.")
            return

        # Read the content of the SRT file
        srt_content = read_srt(file_path)
        # If the file couldn't be read, return without doing anything
        if srt_content is None:
            return

        # Split the content into subtitle blocks and process each one
        for line in srt_content.split('\n\n'):
            # Make sure the line is not just whitespace
            if line.strip():
                parts = line.split('\n')
                subtitle_index = parts[0]  # The first line is the subtitle index
                timestamp = parts[1]  # The second line is the subtitle timestamp
                original_text = '\n'.join(parts[2:])  # The rest is the subtitle text
                # Clean the text of any HTML tags
                cleaned_text = clean_html_tags(original_text)

                # Save the cleaned text into the database
                self.database_manager.save_to_db(subtitle_index, timestamp, cleaned_text)

    def select_translation_service(self):
        # Prompt the user to select between OpenAI and DeepL translation services
        print("Select the translation service:")
        print("1. OpenAI")
        print("2. DeepL")
        choice = input("Enter your choice (1/2): ")

        # Set the translation service based on user input
        if choice == '1':
            self.translation_service = 'openai'
        elif choice == '2':
            self.translation_service = 'deepl'
        else:
            # Default to DeepL if the choice is invalid
            print("Invalid choice. Defaulting to DeepL.")
            self.translation_service = 'deepl'

    def translate_with_openai(self, original_text, subtitle_index):
        # Fetch context from the database for a better translation result
        # Context is the previous translation which can help in maintaining consistency
        context = self.database_manager.get_translation_from_index(subtitle_index - 1)

        # Call the OpenAI translation function from the 'openai_translator.py' file
        # It uses the original text, the target language, the movie name, and the context
        translated_text = translate_openai(
            original_text=original_text,
            target_lang=self.target_lang,
            movie_name=self.movie_name,
            context=context
        )

        # Return the translated text
        return translated_text

    def translate_deepl(self, original_text):
        # Use the translate_deepl function from the deepl_translator module
        # The function takes the original text and the target language to perform the translation
        # The target language is a class attribute defined in the Translator class
        translated_text = translate_deepl(original_text, self.target_lang)

        # Return the text translated into the target language
        return translated_text

    def calculate_default_index_range(self):
        # Retrieve the index of the last subtitle that was translated
        start_index = self.database_manager.get_last_translated_index()
        # Get the highest subtitle index in the database to define the range
        max_index = self.database_manager.get_max_subtitle_index()

        # If there is no maximum index, assume the default range extends 50 subtitles from the start_index
        if max_index is None:
            end_index = start_index + 49
        else:
            # If a maximum index exists, set the end of the range to the smaller of start_index + 49 or the max_index
            end_index = min(start_index + 49, max_index)

        # Return the starting and ending indices of the default translation range
        return start_index, end_index

    def create_translated_srt(self):
        # Construct the filename for the translated subtitles using the movie name and target language
        # This filename format includes the movie's original name followed by the target language code and the .srt extension
        new_file_name = f"{self.movie_name}.{self.target_lang}.srt"
        # Create the full path for the new SRT file by combining the translations directory path and the new file name
        translated_file_path = os.path.join(self.translations_path, new_file_name)

        # Attempt to save the translations into the newly named SRT file
        try:
            # This calls a method on the database manager object to extract translated text from the database
            # and write it to the SRT file format at the specified path
            self.database_manager.save_translations_to_srt(translated_file_path)
            # If successful, print a confirmation message with the path to the new SRT file
            print(f"Translated subtitles saved to file: {translated_file_path}")
        except Exception as e:
            # If an error occurs during the save process, print an error message
            print(f"Error saving translations to file: {e}")

    def get_user_input(self, default_index_range):

        while True:
            # Prompt the user to enter a range of indices for subtitles to translate
            index_range_input = input(
                f"Enter index range in format 'start-end' (default {default_index_range}): ").strip()
            # Use the user-provided index range or the default if no input is provided
            index_range = index_range_input if index_range_input else default_index_range
            print(f"Setting index_range to {index_range}\n")

            # Ask for the batch size, which determines how many translations are processed at once
            batch_size_input = input("Enter the batch size (default 5): ").strip()
            # Ensure the batch size is a digit and fallback to default if not
            batch_size = int(batch_size_input) if batch_size_input.isdigit() else 5
            print(f"Setting batch_size to {batch_size}\n")

            # Query whether previously translated texts should be overwritten
            overwrite_translations_input = input(
                "Do you want to update already translated texts? (y/n): ").lower().strip()
            # Interpret the user input, defaulting to not overwrite if the response is not affirmative
            overwrite_translations = True if overwrite_translations_input in ['y', ''] else False
            print(f"Setting overwrite_translations to {overwrite_translations}\n")

            # Check if the provided index range is valid
            if '-' in index_range:
                valid, start_index, end_index = self.check_index_range(index_range)
                if valid:
                    # If valid, update the index range and exit the loop
                    index_range = f"{start_index}-{end_index}"
                    break
            else:
                # For a single index, check its validity before proceeding
                if self.check_single_index(index_range):
                    break

        # Return the collected user inputs: index range, batch size, and overwrite preference
        return index_range, batch_size, overwrite_translations

    def check_index_range(self, index_range):
        # Attempt to retrieve the highest subtitle index from the database
        # This index represents the total number of subtitles available
        max_index = self.database_manager.get_max_subtitle_index()

        # If the maximum index cannot be determined, it indicates an issue, such as an empty database
        if max_index is None:
            print("Error: Unable to retrieve the maximum index from the database.")
            # Return False to indicate the failure of the range check
            return False

        try:
            # Attempt to parse the start and end indices provided by the user
            start_index, end_index = map(int, index_range.split('-'))

            # Ensure the start index is not less than 1, adjusting it if necessary
            if start_index < 1:
                start_index = 1
                print(f"Start index is too small, setting to minimum value of 1.")

            # Ensure the end index does not exceed the maximum index in the database, adjusting it if necessary
            if end_index > max_index:
                end_index = max_index
                print(f"End index is too big, setting to maximum available index of {max_index}.")

            # Check if the start index is greater than the end index, which is invalid
            elif start_index > end_index:
                raise ValueError("Start index cannot be greater than end index.")

            # If all checks pass, return True along with the validated start and end indices
            return True, start_index, end_index

        except ValueError:
            # Catch and handle any ValueError, such as if the provided range isn't in a valid format
            print("Invalid index range. Please enter a valid range like 'x-y', where x <= y.")
            # Return False to indicate the failure to validate the range
            return False

    def check_single_index(self, index_range):
        # Retrieve the highest subtitle index to validate against
        max_index = self.database_manager.get_max_subtitle_index()

        try:
            # Attempt to convert the index_range to an integer to ensure it's a valid single index
            single_index = int(index_range)
            # Check if the index is within the valid range (greater than 0 and less or equal to max_index)
            if single_index < 0 or single_index > max_index:
                # If out of bounds, raise an error to signal invalid input
                raise ValueError
            # If no error is raised, the index is valid
            return True
        except ValueError:
            # Catch the error if conversion to int fails or index is out of bounds
            print("Invalid index. Please enter a valid single index.")
            # Return False to indicate failure in validation
            return False

    def set_parameters(self, index_range, batch_size, overwrite_translations):
        # Initialize index_range as an empty list to hold the ranges or single indices
        self.index_range = []
        # Split the index_range string by commas to support multiple ranges or indices
        for part in index_range.split(','):
            part = part.strip()  # Remove leading/trailing whitespace
            if '-' in part:
                # If part contains '-', it's treated as a range and added directly
                self.index_range.append(part)
            else:
                # Attempt to convert each part to an integer to handle single indices
                try:
                    single_index = int(part)
                    # For single indices, create a range where start and end are the same
                    self.index_range.append(f"{single_index}-{single_index}")
                except ValueError:
                    # If conversion fails, indicate the specific part that's invalid
                    print(f"Invalid index: {part}")

        # Set the batch size and overwrite translations flag based on the user input
        self.batch_size = batch_size
        self.overwrite_translations = overwrite_translations

    def process_and_translate_range(self, start_index, end_index, batch_size, overwrite_translations):
        # Initialize the current index to the start of the range
        current_index = start_index
        # Set a commit interval to update the database in batches
        commit_interval = 50
        # Keep track of the number of translations processed
        translations_count = 0
        # Initialize a list to store translation updates
        translations_to_update = []
        # Access the global list of failed translations
        global failed_translations

        # Process subtitles in the specified range in batches
        while current_index <= end_index:
            # Determine the last index of the current batch
            next_batch_index = min(current_index + batch_size - 1, end_index)
            print(f"Translating lines {current_index}-{next_batch_index}...")

            # Fetch rows to translate from the database
            rows_to_translate = self.database_manager.fetch_rows_to_translate(current_index, next_batch_index,
                                                                              overwrite_translations)
            # Concatenate the text of the rows to form the batch text
            batch_text = '\n\n'.join([row[1] for row in rows_to_translate])

            # Initialize variables for translation attempts
            translated_text = None
            attempts = 0
            max_attempts = 5
            # Try translating the batch text until successful or max attempts are reached
            while attempts < max_attempts:
                # Use the specified translation service to translate the text
                if self.translation_service == 'openai':
                    translated_text = self.translate_with_openai(batch_text, current_index)
                elif self.translation_service == 'deepl':
                    translated_text = self.translate_deepl(batch_text)
                else:
                    print("Error: Unknown translation service.")
                    break
                attempts += 1

                # Check if the translation is valid
                if translated_text and is_translation_valid(batch_text, translated_text):
                    print(
                        f"Translation attempt {attempts} " + Fore.GREEN + "succeeded" + Style.RESET_ALL + f" for lines {current_index}-{next_batch_index}.")
                    # Split the translated text into blocks
                    translated_blocks = translated_text.split('\n\n')

                    # Update the database with the translations
                    for i, block in enumerate(translated_blocks):
                        subtitle_index = rows_to_translate[i][0]
                        translations_to_update.append((subtitle_index, block))

                    translations_count += len(rows_to_translate)
                    # Update the database if the commit interval is reached or at the end of the range
                    if translations_count >= commit_interval or next_batch_index == end_index:
                        self.database_manager.update_database(translations_to_update, overwrite_translations)
                        translations_to_update = []
                        translations_count = 0
                    break
                else:
                    print(
                        f"Translation attempt {attempts} " + Fore.RED + "failed" + Style.RESET_ALL + f" for lines {current_index}-{next_batch_index}.")

                # If all attempts fail, add the batch to the list of failed translations
                if attempts == max_attempts:
                    print(
                        f"All translation attempts " + Fore.RED + "failed" + Style.RESET_ALL + f" for lines {current_index}-{next_batch_index}. Adding to the list of failures.")
                    failed_translations.extend([row[0] for row in rows_to_translate])

            # Move to the next batch
            current_index = next_batch_index + 1

        # Final update to the database with any remaining translations
        if translations_to_update:
            self.database_manager.update_database(translations_to_update, overwrite_translations)

    def process_srt(self, overwrite_translations):
        # Announce the start of the translation process
        print("\nStarting translation...\n")

        try:
            # Loop through each index range specified by the user
            for index_range in self.index_range:
                # Convert the start and end of the range from string to integers
                start_index, end_index = map(int, index_range.split('-'))
                print(f"Processing index range {start_index}-{end_index}...\n")
                # Call the function to process and translate the range of subtitles
                self.process_and_translate_range(start_index, end_index, self.batch_size, overwrite_translations)

            # Once all ranges have been processed, create the translated SRT file
            self.create_translated_srt()

            # If there were any failed translations, attempt to retranslate them
            if failed_translations:
                print(f"Indexes of failed translations before retranslation: {failed_translations}")
                # Copy the list of failed translations for reprocessing
                temp_failed_translations = failed_translations[:]
                # Clear the original list before attempting retranslation
                failed_translations.clear()

                # Ask the user if they want to retry translating the failed ones
                retry = input("Do you want to try retranslating the failed translations? (y/n): ")
                if retry.lower() == 'y':
                    # Retry translation for each failed index
                    for index in temp_failed_translations:
                        self.process_and_translate_range(index, index, 1, overwrite_translations)
                else:
                    # If the user decides not to retry, you can add a message or take other actions
                    print("Not retrying failed translations. Continuing with the next steps.")

                # After retrying, check if there are still any failed translations
                if failed_translations:
                    print(f"Indexes of failed translations after retranslation: {failed_translations}")
                else:
                    # If all retranslations succeeded, notify the user
                    print("All retranslations succeeded, the list of failures is now empty.")

        except ValueError:
            # Catch and handle any ValueError, typically from incorrect input formats
            print("Invalid input.")
