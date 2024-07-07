import asyncio
import logging
import os
import time
from typing import Union

import requests
from aiogram import Bot, Dispatcher, types
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config.config import TG_TOKEN, TRANSCRIBE_URL, TG_BOT_USERNAME, scraper_latest_post, scraper_key, \
    scraper_post_contents, SUMMARIZE_URL, posts_instruction
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


class ChannelSummarization(StatesGroup):
    waiting_for_channel_name = State()


@dp.message(Command("sum_channel"), ChatTypeFilter(chat_type="private"))
async def cmd_sum_channel(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, введите название канала.")
    await state.set_state(ChannelSummarization.waiting_for_channel_name)


@dp.message(ChannelSummarization.waiting_for_channel_name, ChatTypeFilter(chat_type="private"))
async def process_channel_name(message: types.Message, state: FSMContext):
    channel_url = message.text
    channel_name = channel_url.split('/')[-1]

    response = requests.get(f'{scraper_latest_post}?key={scraper_key}&username={channel_name}')
    response_data = response.json()

    if response_data.get('error') or 'result' not in response_data or 'post_number' not in response_data['result']:
        await message.answer("Ошибка при получении постов из этого канала. Перепроверьте данные")

    latest_post_number = int(response_data['result']['post_number'])

    await message.answer("Формирую сводку:)")

    captions = []
    post_number = latest_post_number
    while len(captions) < 7:
        response = requests.get(f'{scraper_post_contents}?key={scraper_key}&username={channel_name}&post={post_number}')
        response_data = response.json()

        if not response_data.get('error') and 'results' in response_data and 'caption' in response_data['results']:
            caption = response_data['results']['caption']
            captions.append(caption)

        post_number -= 1
        if post_number <= 0:
            break

    # Combine all captions into one string
    combined_captions = " ".join(captions)
    posts_sum = requests.post(SUMMARIZE_URL, json={
        'messages': posts_instruction + combined_captions
    }).json()['text']
    await message.answer(posts_sum)
    await state.clear()


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
