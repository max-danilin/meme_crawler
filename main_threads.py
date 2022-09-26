import requests
#from urllib.request import urlopen, Request, urlretrieve
#from html.entities import name2codepoint
from bs4 import BeautifulSoup
import re, shutil, os, time
from datetime import datetime, timedelta
from pathlib import Path
from selenium import webdriver
from myhtmlparser import MyHTMLParser
from utils import time_duration, get_past_date
from threading import Thread, Lock
from dateutil import tz
import pycurl, certifi
import aiohttp
import asyncio
from io import BytesIO

sites = [
    "https://www.fl.ru",
    "https://www.weblancer.net/",
    "https://www.freelancejob.ru/",
    "https://www.kwork.ru",
    "https://www.work-zilla.com/",
    "https://www.reddit.com/r/memes/hot/",
    "https://pikabu.ru/community/blackhumour",
    "https://www.pikabu.ru/tag/%D0%9C%D0%B5%D0%BC%D1%8B/hot"
]

epoch_time = "2021-06-01T00:00:00+03:00"
pages = 15
number_of_scrolls = 60

pikabu_urls = []
for url in sites:
    if url.find("pikabu") != -1:
        pikabu = [url + "?page=" + str(x) for x in range(1, pages)]
        pikabu_urls.extend(pikabu)
reddit_urls = [url for url in sites if url.find('reddit') != -1]

class Downloader(Thread):
    def __init__(self, url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url
        self.path = f"{datetime.today().year}/{datetime.today().month}/{datetime.today().day}"
        self.log_list = []

    def run(self):
        Path(self.path).mkdir(parents=True, exist_ok=True)
        html_data = self._get_html()
        if html_data is None:
            return
        self.soup = BeautifulSoup(html_data, "html.parser")

    def _get_html(self):
        try:
            print(f"Go {self.url}...")
            res = requests.get(self.url, headers={'User-Agent': 'Mozilla/5.0'}, stream = True)
        except Exception as exc:
            print(exc)
            print("ahahah")
        else:
            return res.text

    # pycurl for faster performance
    # def _get_html(self):
    #     try:
    #         print(f"Go {self.url}...")
    #         buffer = BytesIO()
    #         c = pycurl.Curl()
    #         c.setopt(c.URL, self.url)
    #         c.setopt(c.WRITEDATA, buffer)
    #         c.setopt(c.CAINFO, certifi.where().encode('utf-8'))
    #         c.setopt(c.FOLLOWLOCATION, True)
    #         c.perform()
    #         c.close()
    #         body = buffer.getvalue()
    #     except Exception as exc:
    #         print(exc)
    #     else:
    #         return body.decode('windows-1251')

    def _image_downloader(self, src, filename_jpg):
        r = requests.get(src, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code == 200:
            # Set decode_content value to True, otherwise the downloaded image file's size will be zero.
            r.raw.decode_content = True
            dest = os.path.join(self.path, filename_jpg)
            with open(dest, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            print('Image successfully Downloaded: ', filename_jpg)
        else:
            print('Image Couldn\'t be retreived')

    def _internal_video_downloader(self, src, filename_mp4):
        dest = os.path.join(self.path, filename_mp4)
        r = requests.get(src, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code == 200:
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(chunk_size=255):
                    if chunk:
                        f.write(chunk)
            print("Video successfully dowloaded: ", filename_mp4)
        else:
            print("Video couldn't be retrieved")

    @staticmethod
    def _log_reader(file):
        if not os.path.isfile(file):
            with open(file, 'w') as log:
                log.write(str(epoch_time) + '\n')
            prev_date = epoch_time
        else:
            with open(file, 'r') as logfile:
                prev_date = logfile.readline().rstrip('\n')
        prev_date = datetime.fromisoformat(prev_date)
        return prev_date

    @staticmethod
    def _log_writer(file, log):
        search_until = log - timedelta(days=1)
        with open(file, 'a') as logfile:
            logfile.write(str(search_until) + '\n')

class Pikabu_Downloader(Downloader):
    def __init__(self, url, lock, *args, **kwargs):
        super().__init__(url, *args, **kwargs)
        self.prev_date = self._log_reader(file ="log_pikabu.txt")
        self.prev_date = self.prev_date.replace(tzinfo=tz.tzoffset('MSK', 10800))
        self.lock = lock

    def run(self):
        super().run()
        data = self.soup.select('article', class_="story")
        self._pikabu_scraper(data)
        with self.lock:
            self._log_writer(file ="log_pikabu.txt", log = self.log_list[0])

    def _pikabu_scraper(self, data):
        for article in data:
            rating = article.get('data-rating')
            date = article.find('time')
            name = article.find(attrs={"class": "story__title-link"})
            if date is not None:
                dt = datetime.fromisoformat(date['datetime'])
                self.log_list.append(dt)
                if dt <= self.prev_date:
                    break
                if rating is not None and int(rating) > 1500:
                    name = name.get_text()
                    new_name = re.sub('[^\w\-_\. ]', '', name)
                    filename_jpg = new_name + ".jpg"
                    filename_mp4 = new_name + ".mp4"
                    filename_gif = new_name + ".gif"
                    meme = article.find('img', "story-image__image")
                    if meme is not None:
                        src = meme['data-large-image']
                        self._image_downloader(src, filename_jpg)
                    video = article.find(class_="player")
                    if video is not None:
                        if video.get('data-webm'):
                            src = video['data-webm']
                            if src is not None and src != '':
                                self._internal_video_downloader(src, filename_mp4)
                        elif video.get('data-source'):
                            src = video['data-source']
                            if src is not None and src != '':
                                self._internal_video_downloader(src, filename_gif)

class Reddit_Downloader(Downloader):
    def __init__(self, url, lock, *args, **kwargs):
        super().__init__(url, *args, **kwargs)
        self.prev_date = self._log_reader(file ="log_reddit.txt")
        self.prev_date = self.prev_date.replace(tzinfo=None)
        self.lock = lock

    def run(self):
        super().run()
        data = self.soup.find_all(attrs={"data-testid": "post-container"})
        self._reddit_scraper(data)
        self.log_list.sort(reverse=True)
        with self.lock:
            self._log_writer(file ="log_reddit.txt", log = self.log_list[0])

    def _reddit_scraper(self, data):
        for article in data:
            date = article.find(attrs={"data-click-id": "timestamp"})
            if date is not None:
                try:
                    dt = datetime.fromisoformat(get_past_date(date.get_text()))
                except ValueError as exc:
                    print("Exception", exc)
                pinned_status = article.find("i", class_=re.compile("icon icon-pin_fill"))
                archived_status = article.find("i", class_=re.compile("icon icon-archived_fill"))
                if pinned_status is None and archived_status is None:
                    self.log_list.append(dt)
                if dt <= self.prev_date and pinned_status is None and archived_status is None:
                    break
                rating_in_thousands = self._get_rating(article)
                if rating_in_thousands > 15:
                    title = article.find(attrs={"data-click-id": "body"})
                    new_title = re.sub('[^\w\-_\. ]', '', title.get_text())
                    filename_jpg = new_title + ".jpg"
                    filename_mp4 = new_title + ".mp4"
                    meme = article.find(attrs={"alt": "Post image"})
                    if meme is not None:
                        src = meme['src']
                        self._image_downloader(src, filename_jpg)
                    video = article.find('video')
                    if video is not None:
                        src = video.find('source')
                        src = src['src']
                        if article.find(class_=re.compile("media-element")) is not None:
                            self._internal_video_downloader(src, filename_mp4)
                        else:
                            self._external_video_downloader(src, filename_mp4)

    @staticmethod
    def _get_rating(article):
        rating_data = article.find(id=re.compile("vote-arrows"))
        if not rating_data.get_text().isalpha():
            if rating_data.get_text().find("k") != -1:
                rating_in_thousands = re.findall('\d+', rating_data.get_text())[0]
            else:
                rating_in_thousands = 0
        else:
            rating_in_thousands = 0
        return int(rating_in_thousands)

    def _external_video_downloader(self, src, filename_mp4):
        dest = os.path.join(self.path, filename_mp4)
        pos_id = src[18:].find('/')
        quality_list = [720, 480, 360, 240]
        for quality in quality_list:
            new_src = src[0:19 + pos_id] + "DASH_" + str(quality) + ".mp4"
            r = requests.get(new_src, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 403:
                print("Quality " + str(quality) + "p" + " not available")
            else:
                break
        if r.status_code == 200:
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(chunk_size=255):
                    if chunk:
                        f.write(chunk)
            print("Video successfully dowloaded: ", filename_mp4)
        else:
            print("Video couldn't be retrieved")

    def _get_html(self):
        try:
            print(f"Go {self.url}...")
            options = webdriver.ChromeOptions()
            options.add_argument('--start-maximized')
            driver = webdriver.Chrome(executable_path= r"C:\Users\мммаксим\Downloads\chromedriver\chromedriver.exe",options=options)
            driver.get(self.url)
            driver.implicitly_wait(5)
            scroll_pause_time = 0.3
            screen_height = driver.execute_script("return window.screen.height;")
            no_of_pg = number_of_scrolls
            i = 1
            while no_of_pg:
                driver.execute_script("window.scrollTo(0, {screen_height}*{i});".format(screen_height=screen_height, i=i))
                time.sleep(scroll_pause_time)
                no_of_pg-=1
                i+=1
            time.sleep(5)
        except Exception as exc:
            print(exc)
            print("ahahah")
        else:
            return driver.page_source

class PageSizer(Thread):
    def __init__(self, url, go_ahead=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url
        self.go_ahead = go_ahead
        self.total_bytes = 0

    def run(self):
        html_data = self._get_html(url=self.url)
        if html_data is None:
            return
        self.total_bytes += len(html_data)
        if self.go_ahead:
            parser = MyHTMLParser(base_url=self.url)
            parser.feed(html_data)
            sizers = [PageSizer(url, go_ahead=False) for url in parser.links]
            for sizer in sizers:
                sizer.start()
            for sizer in sizers:
                sizer.join()
            for sizer in sizers:
                self.total_bytes += sizer.total_bytes

    @staticmethod
    def _get_html(url):
        try:
            print(f"Go {url}...")
            res = requests.get(url,  headers={'User-Agent': 'Mozilla/5.0'})
        except Exception as exc:
            print(exc)
            print("ahahah")
        else:
            return res.text

def logger(file):
    with open(file, 'r+') as log:
        data = log.readlines()
        for i, line in enumerate(data):
            data[i] = datetime.fromisoformat(line.rstrip('\n'))
            data[i] = data[i].replace(tzinfo=None)
        data.sort(reverse=True)
        log.seek(0)
        log.write(str(data[0]) + '\n')
        log.truncate()

@time_duration
def main():
    sizers = [PageSizer(url) for url in sites]

    for sizer in sizers:
        sizer.start()

    for sizer in sizers:
        sizer.join()

    for sizer in sizers:
        print(f"For url {sizer.url} need download {sizer.total_bytes // 1024} Kb")


@time_duration
def download():
    lock_pi = Lock()
    pikabu_dls = [Pikabu_Downloader(url=page, name=page, lock=lock_pi) for page in pikabu_urls]
    for pikabu_dl in pikabu_dls:
        pikabu_dl.start()
    for pikabu_dl in pikabu_dls:
        pikabu_dl.join()

    lock_re = Lock()
    reddit_dls = [Reddit_Downloader(url, lock_re) for url in reddit_urls]
    for reddit_dl in reddit_dls:
        reddit_dl.start()
    for reddit_dl in reddit_dls:
        reddit_dl.join()

# aiohttp performance
# async def fetch(url, session):
#     user_agents = (
#         'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'AppleWebKit/537.36 (KHTML, like Gecko)', 'Chrome/74.0.3729.169',
#         'Safari/537.36')
#     async with session.get(url, headers={'User-Agent': choice(user_agents)}) as response:
#         return await response.read()
#
# async def run():
#     tasks = []
#     start = time.time()
#
#     # Fetch all responses within one Client session,
#     # keep connection alive for all requests.
#     async with aiohttp.ClientSession() as session:
#         for url in pikabu_urls:
#             task = asyncio.ensure_future(fetch(url, session))
#             tasks.append(task)
#
#         responses = await asyncio.gather(*tasks)
#         # you now have all response bodies in this variable
#         print(responses[0])
#     print(f'Finish with {len(pikabu_urls)} requests {time.time() - start}')
#
# def print_responses(result):
#     print(result)
#
# loop = asyncio.get_event_loop()
# future = asyncio.ensure_future(run())
# loop.run_until_complete(future)

main()
#download()
pikabu_pattern = re.compile("pikabu")
reddit_pattern = re.compile("reddit")
if list(filter(reddit_pattern.search, sites)) != []:
    logger("log_reddit.txt")
if list(filter(pikabu_pattern.search, sites)) != []:
    logger("log_pikabu.txt")
