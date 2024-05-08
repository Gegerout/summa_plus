from peewee import Model, SqliteDatabase, PrimaryKeyField, IntegerField, CharField

db = SqliteDatabase("database.db")


class BaseModel(Model):
    id = PrimaryKeyField(unique=True)

    class Meta:
        database = db


class Message(BaseModel):
    source_id = IntegerField()
    chat_id = IntegerField()
    text = CharField()


class VkMessage(Message):
    pass


class TgMessage(Message):
    pass


class Summarization(BaseModel):
    message_id = IntegerField()
    parameter = IntegerField()
    text = CharField()


class VkSummarization(Summarization):
    pass


class TgSummarization(Summarization):
    pass
