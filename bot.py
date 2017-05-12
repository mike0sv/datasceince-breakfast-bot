from threading import Thread
from time import sleep, time

import telepot
from telepot.delegate import include_callback_query_chat_id, pave_event_space, per_chat_id, create_open
from telepot.helper import Editor
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

from utils import PersistedDict
from scheduler import Event

with open('token') as token_file:
    token = token_file.read().strip()
with open('superusers.txt') as su_file:
    superusers = set(map(lambda x: int(x.strip()), su_file.readlines()))

users_dump = 'users.json'
users = PersistedDict(users_dump)
statistics = PersistedDict('statistics.json')
# bot = telepot.Bot(token)
handlers = dict()

# notification_cron = '30 21 * * 1'
notification_cron = '30 21 * * *'


class BreakfastHandler(telepot.helper.ChatHandler):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='Yes', callback_data='yes'),
        InlineKeyboardButton(text='No', callback_data='no'),
    ]])

    def __init__(self, *args, **kwargs):
        super(BreakfastHandler, self).__init__(*args, **kwargs)
        print('Init', self.id)
        self.last_date = None
        global handlers
        handlers[self.id] = self
        if self.id not in users:
            self.register_user()

            self.editor = None
            self.msg_id = None
        else:
            self.msg_id = users[self.id]['msg_id']
            self.editor = Editor(self.bot, self.msg_id)

    def register_user(self):
        data = self.bot.getChat(self.id)
        data['disabled'] = False
        data['admin'] = self.id in superusers
        users[self.id] = data
        users.save()

    def notify(self, date):
        self._cancel_last()
        self.last_date = date
        sent = self.sender.sendMessage('Придешь на завтрак?', reply_markup=self.keyboard)
        self.editor = Editor(self.bot, sent)
        self.msg_id = telepot.message_identifier(sent)
        users[self.id]['msg_id'] = sent
        users.save()

    def _cancel_last(self):
        if self.msg_id:
            self.editor.editMessageReplyMarkup(reply_markup=None)
            self.editor = None
            self.msg_id = None
            users[self.id]['msg_id'] = None
            users.save()

    def on_callback_query(self, msg):
        query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
        self.bot.answerCallbackQuery(query_id, text='Okay')
        self._cancel_last()
        users[self.id]['last_answer'] = query_data
        statistics[self.last_date][query_data].append(self.id)
        users.save()
        statistics.save()

    def on_message(self, msg):
        if 'new_chat_member' in msg:
            return
            # pprint(msg)
        if telepot.flavor(msg) == 'callback_query':
            self.on_callback_query(msg)
        else:
            if 'text' in msg and msg['text'] == '/stats':
                self.sender.sendMessage(str(statistics))


def notify_all():
    now = int(time())
    statistics[now] = {'yes': [], 'no': []}
    statistics.save()
    for chat, handler in handlers.items():
        if not users[chat]['disabled']:
            handler.notify(now)


def main():
    bot = telepot.DelegatorBot(token, [
        include_callback_query_chat_id(
            pave_event_space())(
            per_chat_id(types=['private']), create_open, BreakfastHandler, timeout=10000),
    ])
    notifications_thread = Thread(target=notify_all)
    notifications_thread.daemon = True
    notifications_thread.start()
    for user in users:
        bot.handle({'chat': {'type': 'private', 'id': int(user)}, 'message_id': None, 'new_chat_member': None})
    notification = Event(lambda: notification_cron, notify_all)
    notification.run(True)
    bot.message_loop(run_forever=True)


if __name__ == '__main__':
    main()
