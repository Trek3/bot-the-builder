from dateutil.relativedelta import relativedelta

import datetime

def calls(f):
    def wrapper(*args):
        print('### calling function {}'.format(f.__name__))
        return f(*args)
    return wrapper

def ID():
    index = 0
    while True:
        yield str(index).zfill(9)
        index += 1

class BotRequest:

    def __init__(self, name = None, desc = None, date = None, chat_id = None):
        self.name = name
        self.desc = desc
        self.date = date
        self.chat_id = chat_id
        
    def create(self):
        if self.date is None:
            self.date = datetime.datetime.now().date() + relativedelta(months = 1)

    def __str__(self):
        if self.date is None:
            return 'Nome: {}\nDescrizione: {}\n\n'.format(self.name, self.desc)
        else:
            return 'Nome: {}\nDescrizione: {}\nLa deadline per la consegna è per il {}.\n\n'.format(self.name, self.desc, str(self.date))