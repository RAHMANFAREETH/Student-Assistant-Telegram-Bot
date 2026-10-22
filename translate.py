import time

from telebot import types
from deep_translator import GoogleTranslator, MyMemoryTranslator


# ==================================================
# USER TRANSLATION STATE
# ==================================================

translation_state = {}

# Prevent users from making requests too quickly
last_translation_time = {}

# Simple translation cache
translation_cache = {}


# ==================================================
# LANGUAGES
# ==================================================

SOURCE_LANGUAGES = {
    "🔎 Auto Detect": "auto",
    "🇬🇧 English": "en",
    "🇱🇰 Tamil": "ta",
    "🇸🇦 Arabic": "ar",
    "🇱🇰 Sinhala": "si"
}

TARGET_LANGUAGES = {
    "🇬🇧 English": "en",
    "🇱🇰 Tamil": "ta",
    "🇸🇦 Arabic": "ar",
    "🇱🇰 Sinhala": "si"
}


# ==================================================
# TRANSLATION FUNCTION
# ==================================================

def translate_text(source, target, text):

    # ----------------------------------------------
    # CHECK CACHE
    # ----------------------------------------------

    cache_key = (
        source,
        target,
        text
    )

    if cache_key in translation_cache:

        return (
            translation_cache[cache_key],
            "Cache"
        )


    # ----------------------------------------------
    # TRY GOOGLE FIRST
    # ----------------------------------------------

    google_error = None

    try:

        result = GoogleTranslator(
            source=source,
            target=target
        ).translate(text)

        if result:

            translation_cache[cache_key] = result

            return (
                result,
                "Google"
            )

    except Exception as e:

        google_error = str(e)

        print(
            "Google Translator error:",
            google_error
        )


    # ----------------------------------------------
    # GOOGLE FAILED → TRY MYMEMORY
    # ----------------------------------------------

    try:

        result = MyMemoryTranslator(
            source=source,
            target=target
        ).translate(text)

        if result:

            translation_cache[cache_key] = result

            return (
                result,
                "MyMemory"
            )

    except Exception as e:

        print(
            "MyMemory Translator error:",
            e
        )

        raise RuntimeError(
            "Both translation services are currently unavailable."
        )


# ==================================================
# REGISTER TRANSLATION HANDLERS
# ==================================================

def register_translation_handlers(
    bot,
    show_main_menu
):


    # ==============================================
    # SOURCE LANGUAGE MENU
    # ==============================================

    def show_source_menu(chat_id):

        translation_state[chat_id] = {
            "step": "source"
        }

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2
        )

        markup.add(

            types.KeyboardButton(
                "🔎 Auto Detect"
            ),

            types.KeyboardButton(
                "🇬🇧 English"
            ),

            types.KeyboardButton(
                "🇱🇰 Tamil"
            ),

            types.KeyboardButton(
                "🇸🇦 Arabic"
            ),

            types.KeyboardButton(
                "🇱🇰 Sinhala"
            ),

            types.KeyboardButton(
                "🏠 Main Menu"
            )
        )

        bot.send_message(
            chat_id,
            """
🌐 Translator

Choose the language of your original text.

If you are not sure, choose:

🔎 Auto Detect
""",
            reply_markup=markup
        )


    # ==============================================
    # TARGET LANGUAGE MENU
    # ==============================================

    def show_target_menu(chat_id):

        state = translation_state.get(
            chat_id
        )

        if not state:

            show_source_menu(chat_id)

            return

        state["step"] = "target"

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2
        )

        markup.add(

            types.KeyboardButton(
                "🇬🇧 English"
            ),

            types.KeyboardButton(
                "🇱🇰 Tamil"
            ),

            types.KeyboardButton(
                "🇸🇦 Arabic"
            ),

            types.KeyboardButton(
                "🇱🇰 Sinhala"
            ),

            types.KeyboardButton(
                "🔙 Change Source"
            ),

            types.KeyboardButton(
                "🏠 Main Menu"
            )
        )

        bot.send_message(
            chat_id,
            f"""
✅ Source language:

{state["source_name"]}

Now choose the target language:
""",
            reply_markup=markup
        )


    # ==============================================
    # READY TO TRANSLATE
    # ==============================================

    def show_text_menu(chat_id):

        state = translation_state[
            chat_id
        ]

        state["step"] = "text"

        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True,
            row_width=2
        )

        markup.add(

            types.KeyboardButton(
                "🔁 Change Languages"
            ),

            types.KeyboardButton(
                "🏠 Main Menu"
            )
        )

        bot.send_message(
            chat_id,
            f"""
🌐 Translator Ready

From:
{state["source_name"]}

To:
{state["target_name"]}

📝 Send the text you want to translate.
""",
            reply_markup=markup
        )


    # ==============================================
    # TRANSLATE BUTTON
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.text == "🌐 Translate"
    )
    def translation_menu(message):

        show_source_menu(
            message.chat.id
        )


    # ==============================================
    # TRANSLATION HANDLER
    # ==============================================

    @bot.message_handler(
        func=lambda m:
        m.chat.id in translation_state
    )
    def handle_translation(message):

        chat_id = message.chat.id

        if not message.text:

            bot.send_message(
                chat_id,
                "❌ Please send text."
            )

            return

        text = message.text.strip()

        state = translation_state.get(
            chat_id
        )

        if not state:

            return


        # ==========================================
        # MAIN MENU
        # ==========================================

        if text == "🏠 Main Menu":

            translation_state.pop(
                chat_id,
                None
            )

            name = (
                message.from_user.first_name
                or "Friend"
            )

            show_main_menu(
                chat_id,
                name
            )

            return


        # ==========================================
        # CHANGE SOURCE
        # ==========================================

        if text == "🔙 Change Source":

            show_source_menu(
                chat_id
            )

            return


        # ==========================================
        # CHANGE LANGUAGES
        # ==========================================

        if text == "🔁 Change Languages":

            show_source_menu(
                chat_id
            )

            return


        # ==========================================
        # SELECT SOURCE
        # ==========================================

        if state["step"] == "source":

            if text not in SOURCE_LANGUAGES:

                bot.send_message(
                    chat_id,
                    """
❌ Choose a source language using the buttons.
"""
                )

                return

            state["source"] = (
                SOURCE_LANGUAGES[text]
            )

            state["source_name"] = text

            show_target_menu(
                chat_id
            )

            return


        # ==========================================
        # SELECT TARGET
        # ==========================================

        if state["step"] == "target":

            if text not in TARGET_LANGUAGES:

                bot.send_message(
                    chat_id,
                    """
❌ Choose a target language using the buttons.
"""
                )

                return

            target = TARGET_LANGUAGES[
                text
            ]

            source = state[
                "source"
            ]

            if (
                source != "auto"
                and source == target
            ):

                bot.send_message(
                    chat_id,
                    """
❌ Source and target languages cannot be the same.

Choose another target language.
"""
                )

                return

            state["target"] = target

            state["target_name"] = text

            show_text_menu(
                chat_id
            )

            return


        # ==========================================
        # TRANSLATE TEXT
        # ==========================================

        if state["step"] == "text":

            # --------------------------------------
            # RATE LIMIT OUR OWN BOT
            # --------------------------------------

            current_time = time.time()

            last_time = last_translation_time.get(
                chat_id,
                0
            )

            if current_time - last_time < 1.5:

                bot.send_message(
                    chat_id,
                    """
⏳ Please wait a moment before sending another translation.
"""
                )

                return

            last_translation_time[
                chat_id
            ] = current_time


            # --------------------------------------
            # VALIDATION
            # --------------------------------------

            if len(text) > 5000:

                bot.send_message(
                    chat_id,
                    """
❌ Text is too long.

Please send less than 5000 characters at a time.
"""
                )

                return


            status = bot.send_message(
                chat_id,
                "⏳ Translating..."
            )


            # --------------------------------------
            # TRANSLATE
            # --------------------------------------

            try:

                translated_text, provider = (
                    translate_text(
                        state["source"],
                        state["target"],
                        text
                    )
                )


                try:

                    bot.delete_message(
                        chat_id,
                        status.message_id
                    )

                except Exception:

                    pass


                # ----------------------------------
                # RESULT HEADER
                # ----------------------------------

                result_header = (
                    "✅ Translation Complete\n\n"
                    f"From: {state['source_name']}\n"
                    f"To: {state['target_name']}\n\n"
                    "──────────────\n\n"
                )


                # ----------------------------------
                # TELEGRAM MESSAGE LIMIT
                # ----------------------------------

                max_length = 3800

                complete_result = (
                    result_header
                    + translated_text
                )


                if (
                    len(complete_result)
                    <= max_length
                ):

                    bot.send_message(
                        chat_id,
                        complete_result
                    )

                else:

                    bot.send_message(
                        chat_id,
                        result_header
                    )

                    for i in range(
                        0,
                        len(translated_text),
                        max_length
                    ):

                        bot.send_message(
                            chat_id,
                            translated_text[
                                i:
                                i + max_length
                            ]
                        )


                # ----------------------------------
                # NEXT ACTION
                # ----------------------------------

                bot.send_message(
                    chat_id,
                    """
🌐 Send another text to translate using the same languages.

Or choose:

🔁 Change Languages
🏠 Main Menu
"""
                )


                # Terminal debugging
                print(
                    f"Translation provider: {provider}"
                )


            # ======================================
            # ALL SERVICES FAILED
            # ======================================

            except Exception as e:

                try:

                    bot.delete_message(
                        chat_id,
                        status.message_id
                    )

                except Exception:

                    pass


                bot.send_message(
                    chat_id,
                    """
❌ Translation services are temporarily unavailable.

Please try again after a short while.
"""
                )

                print(
                    "Translation error:",
                    e
                )