import os

import requests
from vk_api import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

from config.config import VK_TOKEN, VK_GROUP_ID, TRANSCRIBE_URL, VK_GROUP_USERNAME
from database.controller import controller_factory, VK

vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
long_poll = VkBotLongPoll(vk_session, group_id=VK_GROUP_ID)


def get_name_of_user(chat_id: int, user_id: int):
    profiles = vk_session.method("messages.getConversationMembers", {"peer_id": chat_id})['profiles']
    for profile in profiles:
        if profile['id'] == user_id:
            return profile['first_name'] + " " + profile['last_name'] if 'last_name' in profile.keys() else ""


def send_message(user_id: int, text: str):
    body = {
        "user_id": user_id,
        "message": text,
        "random_id": 0
    }

    vk_session.method("messages.send", body)


for event in long_poll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW and event.from_chat:
        print(event.obj)
        user_id = event.obj['message']['from_id']
        chat_id = event.obj['message']['peer_id']
        if event.obj['message']['text'].startswith("[" + VK_GROUP_USERNAME):
            try:
                parameter = int(event.obj['message']['text'].split(" ")[1])
                if parameter > 0:
                    summarization = controller_factory(VK).create_summarization(chat_id, get_name_of_user(chat_id, event.obj['message']['reply_message']['from_id']) + ": " + event.obj['message']['reply_message']['text'], parameter)
                    send_message(user_id, summarization)
                else:
                    send_message(user_id, "Параметр - положительное число")
            except KeyError:
                send_message(user_id, "Ваше сообщение должно быть ответом на сообщение, с которого нужно начать суммаризацию")
            except IndexError:
                send_message(user_id, "Не вижу параметра в сообщении")
            except ValueError:
                send_message(user_id, "Параметр - не число, так нельзя")
        else:
            text = get_name_of_user(chat_id, user_id) + ": "
            if len(event.obj['message']['attachments']) == 1 and event.obj['message']['attachments'][0]['type'] == 'audio_message':
                link = event.obj['message']['attachments'][0]['audio_message']['link_mp3']
                response = requests.get(link)
                filename = link.split("/")[-1]
                open(filename, 'wb').write(response.content)
                transcription_response = requests.post(TRANSCRIBE_URL, files={'file': open(filename, 'rb')})
                if transcription_response.status_code == 200:
                    text += transcription_response.json()['transcription']
                os.remove(filename)
            elif event.obj['message']['text'] != '':
                text += event.obj['message']['text']
            else:
                continue
            controller_factory(VK).save_message(0, chat_id, text)
