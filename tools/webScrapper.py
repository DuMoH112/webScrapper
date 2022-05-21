from time import sleep
from threading import current_thread, Thread


class MultiThreads:
    def __init__(self, func, list_iterable, thread_pool):
        self.func = func
        self.list_iterable = list_iterable
        self.thread_pool = thread_pool
        self.threads = set()

    def __start_thread(self, target, args):
        while True:
            if self.thread_pool > 0:
                self.thread_pool -= 1

                thread = Thread(
                    target=target,
                    args=[args],
                    daemon=False
                )

                self.threads.add(thread.name)
                thread.start()
                break
            else:
                sleep(1)

    def start(self):
        for arg in self.list_iterable:
            self.__start_thread(
                target=self.start_function,
                args=arg
            )

        while self.threads:
            sleep(5)

        print('MultiThreads Done \n')

    def start_function(self, arg):
        self.func(*arg)

        self.threads.remove(current_thread().name)
        self.thread_pool += 1
