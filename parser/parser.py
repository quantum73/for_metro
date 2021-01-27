import logging
import os
import time
from datetime import date, datetime

import sqlalchemy
from selenium import webdriver
from sqlalchemy import String, Integer, Column, Date, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger('PARSER')
handler = logging.StreamHandler()
formatter = logging.Formatter(fmt='%(asctime)s | <%(name)s> | %(message)s', datefmt='%H:%M:%S %d.%m.%Y')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

Base = declarative_base()


class News(Base):
    __tablename__ = 'news'

    id = Column(Integer, unique=True, primary_key=True, autoincrement=True)
    news_id = Column(Integer, unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    url_image = Column(String(120), nullable=False)
    news_date = Column(Date, nullable=False)
    parsed_date = Column(DateTime, nullable=False)

    def __repr__(self):
        return f'<News "{self.title}">'


class NewsParser:
    def __init__(self, url='https://mosmetro.ru/press/news/'):
        self.url = url
        self.chromedriver = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'chromedriver')
        opts = webdriver.ChromeOptions()
        opts.add_argument('--headless')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        self.browser = webdriver.Chrome(executable_path=self.chromedriver, options=opts)
        self.browser.implicitly_wait(3)
        self.moths_templates = {
            'января': 1,
            'февраля': 2,
            'марта': 3,
            'апреля': 4,
            'мая': 5,
            'июня': 6,
            'июля': 7,
            'августа': 8,
            'сентября': 9,
            'октября': 10,
            'ноября': 11,
            'декабря': 12,
        }

    def to_date(self, str_date: str):
        day, month, year = str_date.lower().split()
        month = self.moths_templates.get(month)
        day, year = int(day), int(year)
        return date(year=year, month=month, day=day)

    def parse_news(self):
        self.browser.get(self.url)

        news_list = self.browser.find_elements_by_xpath("//div[contains(@class, 'list-item')]")
        for item in news_list:
            url_image = item.find_element_by_xpath("a/img").get_attribute('src')
            title = item.find_element_by_xpath("a/span/span[contains(@class, 'text-title')]").text
            old_window = self.browser.window_handles[0]

            link = item.find_element_by_xpath("a").get_attribute("href")
            news_id = int(link.rstrip('/').split('/')[-1])
            self.browser.execute_script(f"window.open('{link}')")
            new_window = self.browser.window_handles[1]

            self.browser.switch_to.window(new_window)
            publish_date = self.browser.find_element_by_xpath("//div[contains(@class, 'content-date')]").text
            publish_date = self.to_date(publish_date)
            parsed_date = datetime.now()

            self.browser.close()
            self.browser.switch_to.window(old_window)
            result = {"news_id": news_id,
                      "title": title,
                      "url_image": url_image,
                      "publish_date": publish_date,
                      "parsed_date": parsed_date}
            yield result

    def __del__(self):
        logger.debug("<-- CLOSE BROWSER -->")
        self.browser.close()


if __name__ == '__main__':
    db_path = 'postgresql+psycopg2://postgres:postgres@postgres/for_metro'
    db = sqlalchemy.create_engine(db_path)
    Base.metadata.tables["news"].create(bind=db, checkfirst=True)
    Session = sessionmaker(bind=db)
    session = Session()
    parser = NewsParser()

    while True:
        for item in parser.parse_news():
            news_id = item.get("news_id")
            if not session.query(News).filter_by(news_id=news_id).first():
                session.add(News(
                    news_id=news_id,
                    title=item.get("title"),
                    url_image=item.get("url_image"),
                    news_date=item.get("publish_date"),
                    parsed_date=item.get("parsed_date"),
                ))
                logger.debug(f"Added new news item #{news_id}")
        session.commit()
        logger.debug("Commit all new data")

        time.sleep(10 * 60)
