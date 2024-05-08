import os.path
from typing import Type, Union

import peewee
import requests as requests

from config.config import SUMMARIZE_URL
from database import Message, Summarization, VkMessage, VkSummarization, TgMessage, TgSummarization, db

VK = "VK"
TG = "TG"


class Controller:
    def __init__(self, message_type: Type[Message], summarization_type: Type[Summarization]):
        self.MT = message_type
        self.ST = summarization_type

    def save_message(self, source_id: int, chat_id: int, text: str):
        self.MT(source_id=source_id, chat_id=chat_id, text=text).save()

    def create_summarization(self, chat_id: int, key: Union[int, str], parameter: int):
        try:
            if type(key) is int:
                source_id = key
            else:
                source_id = list(self.MT.select().where((self.MT.chat_id == chat_id) & (self.MT.text == key)))[-1].id
            summarization = self.ST.get((self.ST.message_id == source_id) & (self.ST.parameter == parameter))
            return summarization.text
        except peewee.DoesNotExist:
            if type(key) is int:
                source_id = key
                start_id = self.MT.get(self.MT.source_id == source_id).id
            else:
                start_id = list(self.MT.select().where((self.MT.chat_id == chat_id) & (self.MT.text == key)))[-1].id
                source_id = start_id
            messages = self.MT.select().where((self.MT.id >= start_id) & (self.MT.chat_id == chat_id)).limit(parameter)
            text = requests.post(SUMMARIZE_URL, json={
                'messages': "dialogue:" + "\n".join(map(lambda x: x.text, list(messages)))
            }).json()['text']
            self.ST(message_id=source_id, parameter=parameter, text=text).save()
            return text


def controller_factory(source: str):
    if not os.path.exists("database.db"):
        db.create_tables([
            VkMessage, VkSummarization,
            TgMessage, TgSummarization
        ])
    if source == VK:
        return Controller(VkMessage, VkSummarization)
    elif source == TG:
        return Controller(TgMessage, TgSummarization)
