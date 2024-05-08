import asyncio
import logging
import os
import time
from typing import Union

import requests
from aiogram import Bot, Dispatcher, types
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import BaseFilter

from config.config import TG_TOKEN, TRANSCRIBE_URL, TG_BOT_USERNAME
from database.controller import controller_factory, TG

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TG_TOKEN)
dp = Dispatcher()


class ChatTypeFilter(BaseFilter):
    def __init__(self, chat_type: Union[str, list]):
        self.chat_type = chat_type

    async def __call__(self, message: types.Message) -> bool:
        if isinstance(self.chat_type, str):
            return message.chat.type == self.chat_type
        else:
            return message.chat.type in self.chat_type


async def main():
    await dp.start_polling(bot)


@dp.message(ChatTypeFilter(chat_type=["group", "supergroup"]))
async def save_message(message: types.Message):
    if message.text is not None and message.text.startswith(TG_BOT_USERNAME):
        try:
            parameter = int(message.text.split(" ")[1])
            if parameter > 0:
                summarization = controller_factory(TG).create_summarization(message.chat.id,
                                                                            message.reply_to_message.message_id,
                                                                            parameter)
                await bot.send_message(message.from_user.id, summarization)
            else:
                await message.answer("Параметр - положительное число")
        except AttributeError:
            await message.answer(
                "Ваше сообщение должно быть ответом на сообщение, с которого нужно начать суммаризацию")
        except IndexError:
            await message.answer("Не вижу параметра в сообщении")
        except ValueError:
            await message.answer("Параметр - не число, так нельзя")
        except TelegramForbiddenError:
            await message.answer("Вы ничего не писали боту, поэтому не могу отправить суммаризацию")
    elif message.via_bot is None or message.via_bot.id != 7052943514:
        text = f"{message.from_user.first_name}: "
        if message.voice is not None:
            filename = f"{time.time()}.mp3"
            transcription_response = requests.post(TRANSCRIBE_URL, files={'file': open(filename, 'rb')})
            if transcription_response.status_code == 200:
                text += transcription_response.json()['transcription']
            os.remove(filename)
        if message.text is not None:
            if message.text.startswith("/"):
                return
            text += message.text
        controller_factory(TG).save_message(message.message_id, message.chat.id, text)


if __name__ == "__main__":
    asyncio.run(main())
