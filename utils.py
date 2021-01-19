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

    def __init__(self, name = None, desc = None, date = None):
        self.id = ID()
        self.name = name
        self.desc = desc
        self.date = date

class RequestQueue:

    def __init__(self):
        self.bot_queue = []

    def push(self, request):
        self.bot_queue.append(request)

        self.bot_queue = sorted(self.bot_queue, key = lambda req : req.date)

    def pop(self):

        if len(self.bot_queue) == 0:
            return

        head, *self.bot_queue = self.bot_queue

        return head