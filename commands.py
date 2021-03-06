class Command:
    def __init__(self, name, method, description, is_admin=False):
        self.name = name
        self.method = method
        self.description = description
        self.is_admin = is_admin

    def __repr__(self):
        return '/{name} - {descr}'.format(name=self.name, descr=self.description)


commands = dict()


def add_command(name, method, description, is_admin=False):
    global commands
    commands[name] = Command(name, method, description, is_admin)


def make_commands(chat, is_admin):
    return {c.name: chat.__getattribute__(c.method) for c in commands.values() if
            (is_admin == c.is_admin) or not c.is_admin or is_admin}


def make_help(is_admin):
    return '\n'.join([str(c) for c in commands.values() if (is_admin == c.is_admin) or not c.is_admin or is_admin])


add_command('enable', '_cmd_enable', 'Включить нотификации')
add_command('disable', '_cmd_disable', 'Выключить нотификации')
add_command('stats_raw', '_cmd_stats_raw', 'Показать статистику в json', True)
add_command('stats', '_cmd_stats_last', 'Показать статистику')
add_command('make_admin', '_cmd_make_admin', 'Сделать админом', True)
add_command('run_notify', '_cmd_run_notify', 'Запустить нотификации', True)
add_command('run_attend', '_cmd_run_attend', 'Запустить опрос', True)
add_command('users', '_cmd_show_users', 'Список подписавшихся', True)
add_command('users_raw', '_cmd_show_users_raw', 'Данные по подписавшимся', True)
add_command('change', '_cmd_manual_change',
            'Сменить ответ на последний вопрос (или ответить "да", если вопроса не было)')


def main():
    class DummyHandler:
        def _cmd_enable(self):
            print('lel')

    c = DummyHandler()
    print(commands)
    print(make_commands(c, True))
    for c in make_commands(c, True).values():
        c()


if __name__ == '__main__':
    main()
