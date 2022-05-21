"""
    Parse site drom.ru for city Tomsk and save new data per day
"""
import re
from datetime import datetime
import time

import requests
from bs4 import BeautifulSoup

from tools.webScrapper import MultiThreads
from tools.SQLite import connect_to_sqllite, SQLite_db

from pages.drom_ru.database import migration, DATABASE

URL = "https://tomsk.drom.ru/auto/all"
WEEK_SECONDS = 86400
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'
}


class Card:
    id = None
    url = None
    img = None
    date = None
    name = None
    year = None
    model = None
    price = None

    def __init__(self, session: requests.Session, url: str, s_page: BeautifulSoup):
        self.session = session
        self.s_page = s_page
        self.url = url

    def __request_id(self):
        if self.id:
            return
        self.id = int(self.url.split('/')[-1].split('.')[0])

    def __request_date(self):
        if self.date:
            return
        str_ = self.s_page.find("div", class_="css-pxeubi evnwjo70")
        str_dt = re.search(r'\d{2}.\d{2}.\d{4}', str(str_.string))
        self.date = int(time.mktime(datetime.strptime(
            str_dt.group(), '%d.%m.%Y').timetuple()))

    def __request_name(self):
        if self.name:
            return
        self.name = self.s_page.find(
            "span", class_="css-1kb7l9z e162wx9x0").string

    def __request_model(self):
        if self.model:
            return
        if not self.name:
            self.__request_name()
        self.model = ' '.join(self.name.split(',')[0].split(' ')[1:])

    def __request_year(self):
        if self.year:
            return
        if not self.name:
            self.__request_name()

        self.year = int(re.search(r'\d{4}', self.name.split(','[-1])).group())

    def __request_price(self):
        if self.price:
            return
        self.price = int("".join(
            re.findall(r'\d+', self.s_page.find(
                "div", class_="css-eazmxc e162wx9x0"
            ).text)
        ))

    def __request_img(self):
        if self.img:
            return
        self.img = self.session.get(self.s_page.find(
            "img",
            class_="css-1mnj4qi evrha4s0"
        )["src"], headers=HEADERS).content

    def request_all_data(self):
        self.__request_id()
        self.__request_img()
        self.__request_date()
        self.__request_name()
        self.__request_year()
        self.__request_model()
        self.__request_price()

    def get_all_data(self):
        self.request_all_data()
        return {
            "id": self.id,
            "date": self.date,
            "name": self.name,
            "year": self.year,
            "model": self.model,
            "price": self.price,
            "url": self.url,
            "img": self.img
        }

    def get_date(self):
        if not self.date:
            self.__request_date()

        return self.date

    def get_name(self):
        if not self.name:
            self.__request_name()

        return self.name

    def get_id(self):
        if not self.id:
            self.__request_id()

        return self.id

    def check_page(self):
        return len(self.s_page.find_all("div", class_="css-pg8aei e1lm3vns0")) > 0


def isActualDate(timestamp: int):
    return time.time() - timestamp < WEEK_SECONDS


@connect_to_sqllite(DATABASE)
def added_card_to_base(sqlite: SQLite_db, card: Card):
    data_tuple = (
        card.id,
        card.date,
        card.name,
        card.year,
        card.model,
        card.price,
        card.url,
        card.img
    )
    isDublicate = len(sqlite.insert_data_with_response(execute=f"""
            INSERT OR IGNORE INTO cards(
                card_id,
                time_create,
                name,
                year,
                model,
                price,
                url,
                image
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
    """, data_tuple=data_tuple)) == 0

    sqlite.select_data("SELECT 1;")
    return isDublicate


@connect_to_sqllite(DATABASE)
def check_card_id(sqlite: SQLite_db, card: Card):
    return sqlite.select_data(f"""
        SELECT
            count(*)
        FROM cards
        WHERE card_id={card.get_id()}
    """)[0][0] > 0


def parse_car_page(session: requests.Session, url: str, isActual_list: [int], index: int):
    s = BeautifulSoup(session.get(
        url,
        headers=HEADERS
    ).content, "html.parser")
    c = Card(
        session=session,
        url=url,
        s_page=s
    )
    if check_card_id(card=c):
        print(f"Dublicate - {c.id}")
        isActual_list[index] = True
        return True

    if c.check_page():
        isActual = isActualDate(c.get_date())
        if isActual:
            c.request_all_data()
            isDublicate = added_card_to_base(card=c)
            if isDublicate:
                print(f"Dublicate - {c.name}")
            else:
                print(f"Save - {c.name}")
            isActual_list[index] = True
            return True
        else:
            isActual_list[index] = False
            print(f"NOT ACTUAL - {c.id} - {c.url}")
    else:
        print(f"EMPTY - {c.url}")
        isActual_list[index] = False

    return False


def parse_cards_MultiThreads(session, card_link_list):
    count_card = len(card_link_list)
    isActual_list = [None] * count_card
    thread_pool = 20 if count_card > 20 else count_card

    th = MultiThreads(
        func=parse_car_page,
        list_iterable=[
            [
                session,
                card_link_list[index]["href"],
                isActual_list,
                index
            ] for index in range(count_card)
        ],
        thread_pool=thread_pool
    )
    th.start()

    return True in isActual_list


def check_pins_on_page(s_page):
    "If there are 20 pins on the page, then go to a new page "
    count = len(s_page.find_all("div", title="Прикреплено"))
    return count == 20


def loop_lead_pages(session):
    """
        Data from the pages is collected until
        there are no actual ads for 3 pages
    """
    number_page = 1
    isActual = True
    count_passed_pages = 0
    while isActual or count_passed_pages < 3:
        response = session.get(
            f"{URL}/page{number_page}?order_d=desc&unsold=1",
            headers=HEADERS
        )
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            if check_pins_on_page(soup):
                print(f"page {number_page} passed")
                number_page += 1
                continue

            card_link_list = soup.find(
                class_="css-1173kvb eaczv700"
            ).find_all(
                "a", class_="css-5l099z ewrty961"
            )
            isActual = parse_cards_MultiThreads(session, card_link_list)
            if not isActual:
                count_passed_pages += 1

        number_page += 1


def main():
    migration()

    session = requests.session()
    loop_lead_pages(session)
    print("Done")
