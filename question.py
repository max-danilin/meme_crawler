import requests, time
from bs4 import BeautifulSoup
from threading import Thread
from random import choice
import multiprocessing
import pycurl
import certifi
from io import BytesIO
import urllib
import concurrent.futures
from requests_futures.sessions import FuturesSession
from requests_threads import AsyncSession
import aiohttp
import asyncio

#Enable to get some logging info
# import logging
# import http.client
# http.client.HTTPConnection.debuglevel = 1

# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

sites = [
    "https://pikabu.ru/community/blackhumour",
    "https://www.pikabu.ru/tag/%D0%9C%D0%B5%D0%BC%D1%8B/hot"
]

pages = 10

class Pikabu_Downloader(Thread):
    def __init__(self, url, session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url
        self.begin = time.time()
        self.session = session

    def run(self, data):
        #print("Beginning with thread number",self.name, ",", round(time.time()-self.begin, 4), " seconds has passed")
        #html_data = self._get_html()
        html_data = data
        #print("After requests.get with thread number", self.name, ",", round(time.time()-self.begin, 4), " seconds has passed")
        if html_data is None:
            return
        self.soup = BeautifulSoup(html_data, "html.parser")
        #print("After making soup with thread number", self.name, ",", round(time.time() - self.begin, 4), " seconds has passed")

    #pycurl
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

    #requests
    # def _get_html(self):
    #     try:
    #         user_agents = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'AppleWebKit/537.36 (KHTML, like Gecko)', 'Chrome/74.0.3729.169', 'Safari/537.36')
    #         print(f"Go {self.url}...")
    #         res = requests.get(self.url, headers={'User-Agent': choice(user_agents)}, stream = True)#, allow_redirects=False)
    #     except Exception as exc:
    #         print(exc)
    #     else:
    #         return res.text

    @staticmethod
    async def _get_html(url, session):
        try:
            user_agents = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'AppleWebKit/537.36 (KHTML, like Gecko)', 'Chrome/74.0.3729.169', 'Safari/537.36')
            print(f"Go {url}...")
            async with session.get(url, headers={'User-Agent': choice(user_agents)}) as res:
                return await res.read()
        except Exception as exc:
            print(exc)
            return

test = "https://readingbooks.site/read/?name=1984&"


pikabu_urls = []
for url in sites:
    pikabu = [url + "?page=" + str(x) for x in range(1, pages)]
    pikabu_urls.extend(pikabu)

def download():
    pikabu_dls = [Pikabu_Downloader(url=page,name=str(i)) for i, page in enumerate(pikabu_urls)]

    # Comment the string above and enable 2 underlying strings to get result from different server
    # tests = [test + "page=" + str(x) for x in range(1, pages)]
    # pikabu_dls = [Pikabu_Downloader(url=page, name=str(i)) for i, page in enumerate(tests)]

    # for pikabu_dl in pikabu_dls:
    #     pikabu_dl.run()
    for pikabu_dl in pikabu_dls:
        pikabu_dl.start()

    for pikabu_dl in pikabu_dls:
        pikabu_dl.join()

def load_url(url):
    user_agents = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'AppleWebKit/537.36 (KHTML, like Gecko)', 'Chrome/74.0.3729.169',
    'Safari/537.36')
    res = requests.get(url, headers={'User-Agent': choice(user_agents)}, stream = True)#, allow_redirects=False)
    return res.text

def concur():
    start = time.time()
    pikabu_dls = [Pikabu_Downloader(url=page, name=str(i)) for i, page in enumerate(pikabu_urls)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        #future_to_url = {executor.submit(pikabu_dl.run): pikabu_dl for pikabu_dl in pikabu_dls}
        future_to_url = {executor.submit(load_url, url): url for url in pikabu_urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
            except Exception as exc:
                print('%r generated an exception: %s' % (url, exc))
    print(f'Finish with {len(pikabu_urls)} requests {time.time() - start}')
    # for pikabu_dl in pikabu_dls:
    #     pikabu_dl.start()
    #
    # for pikabu_dl in pikabu_dls:
    #     pikabu_dl.join()

def req_fut():
    start = time.time()
    user_agents = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'AppleWebKit/537.36 (KHTML, like Gecko)', 'Chrome/74.0.3729.169',
        'Safari/537.36')
    session = FuturesSession()
    futures = [session.get(url, headers={'User-Agent': choice(user_agents)}) for url in pikabu_urls]
    for future in concurrent.futures.as_completed(futures):
        resp = future.result()
        print({
            'url': resp.request.url,
            'content': resp.text,
        })
    print(f'Finish with {len(pikabu_urls)} requests {time.time() - start}')


# session = AsyncSession(n=28)
# async def _main():
#     start = time.time()
#     user_agents = (
#         'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'AppleWebKit/537.36 (KHTML, like Gecko)', 'Chrome/74.0.3729.169',
#         'Safari/537.36')
#     rs = []
#     for url in pikabu_urls:
#         rs.append(await session.get(url, headers={'User-Agent': choice(user_agents)}))
#     print(rs)
#     print(f'Finish with {len(pikabu_urls)} requests {time.time() - start}')


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

async def run():
    start = time.time()
    tasks = []
    # Fetch all responses within one Client session,
    # keep connection alive for all requests.
    async with aiohttp.ClientSession() as session:
        for url in pikabu_urls:
            task = asyncio.ensure_future(Pikabu_Downloader(url, session)._get_html(url, session))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
    for response in responses:
        pikabu_dl = Pikabu_Downloader(url, session)
        pikabu_dl.run(response)
    print(f'Finish with {len(pikabu_urls)} requests {time.time() - start}')

loop = asyncio.get_event_loop()
future = asyncio.ensure_future(run())
loop.run_until_complete(future)

#if __name__ == '__main__':
    #download()
    #concur()
    #req_fut()
    #session.run(_main)

