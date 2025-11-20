import json
import random
from asyncio import sleep as asleep
from time import sleep

with open('chunk.json', encoding='utf-8') as fin:
    TEST_AVIA_SEARCH = json.load(fin)


class AviaApi:
    __TASK_ID = "2907fb1b501f1dd2535b5ce8a4a23849"

    def __init__(self):
        self._chunk_index = 0

    async def get_chunk(self, task_id):  # noqa: ARG002
        """
        Получаем ответы
        :return:
        """
        if task_id != self.__TASK_ID:
            raise Exception('Task not found')

        while self._chunk_index < len(TEST_AVIA_SEARCH):
            sleep(15)
            if random.randint(0, 1):
                yield {}
            else:
                chunk = TEST_AVIA_SEARCH[self._chunk_index]
                self._chunk_index += 1
                yield chunk

    async def start_search(self) -> dict:
        """
        Создаем поиск
        :return:
        """
        await asleep(8)
        if random.randint(0, 1):
            return {
                "success": True,
                "task_id": self.__TASK_ID
            }
        return {
            "success": False,
            "error_message": "some_error"
        }
