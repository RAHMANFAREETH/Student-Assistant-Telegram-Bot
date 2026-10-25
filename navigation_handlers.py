from navigation import (
    MAIN_MENU,
    LEGACY_MAIN_MENU,
    CANCEL,
)


def register_navigation_handlers(
    bot,
    show_main_menu,
):
    """
    Universal safe navigation.

    Module-specific state handlers should first yield
    global/navigation buttons using:

        from navigation import should_yield_to_navigation

    Then these handlers can receive Main Menu / Cancel.
    """

    @bot.message_handler(
        func=lambda m:
        m.text in {
            MAIN_MENU,
            LEGACY_MAIN_MENU,
            CANCEL,
        }
    )
    def universal_navigation(
        message
    ):
        show_main_menu(
            message.chat.id,
            message.from_user.first_name
            or "Friend",
        )
