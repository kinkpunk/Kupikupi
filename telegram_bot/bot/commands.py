from dataclasses import dataclass


@dataclass(frozen=True)
class BotCommandSpec:
    command: str
    description: str


def bot_command_specs() -> list[BotCommandSpec]:
    return [
        BotCommandSpec(command="start", description="Открыть Kupikupi"),
        BotCommandSpec(command="help", description="Помощь и список команд"),
        BotCommandSpec(command="id", description="Показать Telegram ID"),
        BotCommandSpec(command="privacy", description="Данные, privacy и terms"),
        BotCommandSpec(command="requests", description="Последние shopping requests"),
        BotCommandSpec(command="watchlists", description="Активные списки покупок"),
        BotCommandSpec(command="pause", description="Поставить список на паузу"),
        BotCommandSpec(command="resume", description="Возобновить список"),
        BotCommandSpec(command="archive", description="Архивировать список"),
    ]


async def setup_bot_commands(bot) -> None:
    from aiogram.types import BotCommand

    await bot.set_my_commands(
        [
            BotCommand(command=item.command, description=item.description)
            for item in bot_command_specs()
        ]
    )
