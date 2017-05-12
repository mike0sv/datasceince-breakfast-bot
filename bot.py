import sys
import traceback
from time import time

import telepot
from telepot.delegate import include_callback_query_chat_id, pave_event_space, per_chat_id, create_open
from telepot.helper import Editor
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton

from commands import make_help, make_commands
from scheduler import Event
from utils import PersistedDict

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
notification_cron = '0 22 * * *'
result_cron = '0 13 * * *'


def describe_user(uid, show_id=False):
    if uid in users:
        u = users[uid]
        descr = '{username} {first} {last}'.format(username=u.get('username', '???'),
                                                   first=u.get('first_name', '???'),
                                                   last=u.get('last_name', '???'))
        if show_id:
            return '{id} '.format(id=uid) + descr
        else:
            return descr
    else:
        return '????????'


def no_args(method):
    def tmp(self, *args, **kwargs):
        return method(self)

    return tmp


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
        self.editor = None
        self.msg_id = None
        self.question = None
        if self.id not in users:
            self.register_user()
        elif 'msg_id' in users[self.id]:
            self.msg_id = users[self.id]['msg_id']
            self.question = users[self.id]['q']
            self.editor = Editor(self.bot, self.msg_id)

        self.commands = make_commands(self, self._is_admin())

    @no_args
    def _cmd_disable(self):
        users[self.id]['disabled'] = True
        users.save()
        self.sender.sendMessage('Нотификации выключены')

    @no_args
    def _cmd_enable(self):
        users[self.id]['disabled'] = False
        users.save()
        self.sender.sendMessage('Нотификации включены')

    @no_args
    def _cmd_stats(self):
        self.sender.sendMessage(str(statistics))

    @no_args
    def _cmd_help(self):
        self.sender.sendMessage(make_help(self._is_admin()))

    @no_args
    def _cmd_stats_last(self):
        last = last_stat()
        yes = [describe_user(u) for u in statistics[last]['yes']]
        no = [describe_user(u) for u in statistics[last]['no']]

        text = 'Придут ({}):\n{}\nНе придут({}):\n{}'.format(len(yes), '\n'.join(yes), len(no), '\n'.join(no))
        if last + '_result' in statistics:
            last += '_result'
            yes = [describe_user(u) for u in statistics[last]['yes']]
            no = [describe_user(u) for u in statistics[last]['no']]
            text += '\n\nПришли ({}):\n{}\nНе пришли ({}):\n{}'.format(len(yes), '\n'.join(yes), len(no), '\n'.join(no))

        self.sender.sendMessage(text)

    @no_args
    def _cmd_show_users(self):
        self.sender.sendMessage('\n'.join([describe_user(u, True) for u in users]))

    @no_args
    def _cmd_run_notify(self):
        notify_all()

    @no_args
    def _cmd_run_attend(self):
        attend_all()

    def _cmd_make_admin(self, text):
        try:
            other_id = int(text.split(' ')[1])
            users[other_id]['admin'] = True
            users.save()
            other_chat = handlers[other_id]
            other_chat.commands = make_commands(other_chat, True)
        except:
            self.sender.sendMessage('Not valid id')

    def _is_admin(self):
        return users[self.id]['admin']

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
        users[self.id]['q'] = 'n'
        self.question = 'n'
        users.save()

    def attend(self, date):
        self._cancel_last()
        self.last_date = date
        sent = self.sender.sendMessage('Пришел на завтрак?', reply_markup=self.keyboard)
        self.editor = Editor(self.bot, sent)
        self.msg_id = telepot.message_identifier(sent)
        users[self.id]['msg_id'] = sent
        users[self.id]['q'] = 'a'
        self.question = 'a'
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
        date = str(self.last_date)
        if self.question == 'a':
            date += '_result'
        statistics[date][query_data].append(self.id)
        users.save()
        statistics.save()

    def on_message(self, msg):
        try:
            if 'new_chat_member' in msg:
                return
                # pprint(msg)
            if telepot.flavor(msg) == 'callback_query':
                self.on_callback_query(msg)
            else:
                if 'text' in msg:
                    text = msg['text']
                    if text.startswith('/'):
                        cmd = text.split(' ')[0][1:]
                        if cmd in self.commands:
                            self.commands[cmd](text)
                        else:
                            self._cmd_help()
                    else:
                        self._cmd_help()
        except Exception as e:
            if self._is_admin():
                tp, exc, tb = sys.exc_info()
                text = ''.join(traceback.format_exception(tp, exc, tb))
                self.sender.sendMessage(text)


def notify_all():
    now = int(time())
    statistics[now] = {'yes': [], 'no': []}
    statistics.save()
    for chat, handler in handlers.items():
        if not users[chat]['disabled']:
            handler.notify(now)


def last_stat():
    return str(max(map(int, filter(lambda x: not x.endswith('result'), statistics.keys()))))


def attend_all():
    last = last_stat()
    statistics[str(last) + '_result'] = {'yes': [], 'no': []}
    statistics.save()
    for chat, handler in handlers.items():
        if chat in statistics[last]['yes']:
            handler.attend(last)


def main():
    bot = telepot.DelegatorBot(token, [
        include_callback_query_chat_id(
            pave_event_space())(
            per_chat_id(types=['private']), create_open, BreakfastHandler, timeout=10000),
    ])
    for user in users:
        bot.handle({'chat': {'type': 'private', 'id': int(user)}, 'message_id': None, 'new_chat_member': None})
    notification = Event(lambda: notification_cron, notify_all)
    notification.run(True)
    attended = Event(lambda: result_cron, attend_all)
    attended.run(True)
    bot.message_loop(run_forever=True)


if __name__ == '__main__':
    main()