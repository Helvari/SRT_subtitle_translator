import openai
from dotenv import load_dotenv

load_dotenv()
client = openai.OpenAI()


def translate_openai(original_text, target_lang, movie_name, context):
    # print(original_text, target_lang, movie_name, subtitle_index, context)
    print(context)

    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            prompt = (
                f"Translate the following subtitles from their original language to {target_lang} for the movie '{movie_name}', "
                f"while preserving the context between sentences. Aim for an accurate translation that not only maintains the original text's meaning and emotion, "
                f"but also uses genre-specific terminology and expressions appropriate for the film. Be natural and fluent for speakers of {target_lang}. "
                f"Keep the structure, tone, and letter casing as in the original. "
                f"Pay special attention to context and the flow between sentences, ensuring that the translated subtitles reflect the continuity of dialogue and narrative. "
                f"Do not repeat the same text between text blocks. "
                "Be precise and subtle in your translations, using liberties only as necessary to ensure the text's naturalness and fluency in the target language. "
                "Incorporate genre-specific terms and expressions when appropriate to enhance the authenticity and richness of the translation.\n\n"
                f"Previous translation (for context): {context}\n\n"
            )
            response = client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": original_text}
                ]
            )
            translated_text = response.choices[0].message.content

            return translated_text

        except openai.APIError as e:
            print(f"OpenAI API returned an error: {e}")
            return None
