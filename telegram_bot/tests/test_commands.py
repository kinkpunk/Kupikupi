from bot.commands import bot_command_specs


def test_bot_commands_include_field_test_entry_points() -> None:
    commands = bot_command_specs()
    command_names = [item.command for item in commands]

    assert command_names == [
        "start",
        "help",
        "id",
        "privacy",
        "requests",
        "watchlists",
        "pause",
        "resume",
        "archive",
    ]
    assert all(item.description for item in commands)
