import os
from dotenv import load_dotenv
from translator_class import Translator


def main():
    # Load environment variables from a .env file
    load_dotenv()

    # Retrieve the file path and target language from the environment variables
    file_path = os.getenv('FILE_PATH')
    target_lang = "fi"
    print(file_path)  # Print the file path to verify it's been loaded correctly

    # Create an instance of the Translator class with the specified file path and target language
    translator = Translator(file_path, target_lang)

    # Allow the user to select the translation service (e.g., OpenAI or DeepL)
    translator.select_translation_service()

    # Get the default index range for translation from the Translator instance
    default_index_range = translator.index_range

    # Prompt the user for input regarding the index range, batch size, and whether to overwrite translations
    index_range, batch_size, overwrite_translations = translator.get_user_input(default_index_range)

    # Apply the user's specifications to the Translator instance
    translator.set_parameters(index_range, batch_size, overwrite_translations)

    # Begin the process of translating the subtitles as per the user's inputs
    translator.process_srt(overwrite_translations)


if __name__ == "__main__":
    while True:
        # Run the main function in a loop to continuously process translations
        main()

        # Provide the user with an option to exit the program
        if input("Type 'quit' to exit: ").lower() == 'quit':
            break
