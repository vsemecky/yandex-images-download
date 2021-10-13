import hashlib
import itertools
import json
import os
import io
import glob
import pathlib
import re
import requests
import sys
import time
from bs4 import BeautifulSoup
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from PIL import Image
from hashlib import md5
from math import floor
from seleniumwire import webdriver
from typing import List, Union, Optional
from urllib.parse import urlparse, urlencode

from termcolor import colored
from urllib3.exceptions import SSLError, NewConnectionError
from slugify import slugify

Driver = Union[webdriver.Chrome, webdriver.Edge, 
               webdriver.Firefox, webdriver.Safari]

DRIVER_NAME_TO_CLASS = {
    'Chrome': webdriver.Chrome,
    'Edge': webdriver.Edge,
    'Firefox': webdriver.Firefox,
    'Safari': webdriver.Safari,
}  # type: Dict[str, Driver]


def get_driver(name: str = "Chrome") -> Driver:
    # driver_class = DRIVER_NAME_TO_CLASS[name]
    # args = {'executable_path': path} if path else {}
    # driver = driver_class(**args)
    # driver = driver_class()

    driver = DRIVER_NAME_TO_CLASS[name]()

    # Time to authorize
    driver.get(YandexImagesDownloader.MAIN_URL)
    time.sleep(10)

    return driver


#####
@dataclass_json
@dataclass
class ImgUrlResult:
    status: str
    message: str
    img_url: str
    img_path: str

    STATUS_COLORS = {
        'fail': 'red',
        'success': 'green',
        'ok': 'green',
        'skip': 'yellow',  # old synonymum for exist
        'exist': 'yellow',
        'negative': 'cyan',
    }

    def print(self):
        status_colored = colored(self.status, self.STATUS_COLORS[self.status])
        print(f"\t{status_colored}: {self.img_url} - {self.message}")


@dataclass_json
@dataclass
class PageResult:
    status: str
    message: str
    page: int
    errors_count: int
    img_url_results: List[ImgUrlResult]


@dataclass_json
@dataclass
class KeywordResult:
    status: str
    message: str
    keyword: str
    errors_count: int
    page_results: List[PageResult]


@dataclass_json
@dataclass
class DownloaderResult:
    status: str
    message: str
    keyword_results: List[KeywordResult]


def save_json(json_path, downloader_result: DownloaderResult):
    downloader_result_json = downloader_result.to_dict()  # pylint: disable=no-member
    pretty_json = json.dumps(downloader_result_json, indent=4, ensure_ascii=False)
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(pretty_json)
    print(f"Result information saved: {json_path}.")


#####

# Log of successfully downloaded image urls
downloaded_log = {}
# negative_ids = []  # used as global variable


def filepath_fix_existing(directory_path: pathlib.Path, name: str,
                          filepath: pathlib.Path) -> pathlib.Path:
    """Expands name portion of filepath with numeric "(x)" suffix.
    """
    new_filepath = filepath
    if filepath.exists():
        for i in itertools.count(start=1):
            new_name = f'{name} ({i}){filepath.suffix}'
            new_filepath = directory_path / new_name
            if not new_filepath.exists():
                break

    return new_filepath


def download_single_image(img_url: str,
                          output_directory: pathlib.Path,
                          min_width: int,
                          min_height: int,
                          sub_directory: str = "",
                          negative_ids=[]
                          ) -> ImgUrlResult:

    img_url_result = ImgUrlResult(status=None, message=None, img_url=img_url, img_path=None)

    # Generate unique hash (SHA224 of img_url)
    img_hash = hashlib.sha224(img_url.encode()).hexdigest()

    directory_path = output_directory / sub_directory
    directory_path.mkdir(parents=True, exist_ok=True)
    img_path = directory_path / img_hash

    # Skip downloading if image `id` is in negative
    if img_hash in negative_ids:
        img_url_result.status = "negative"
        img_url_result.message = ""
        img_url_result.print()
        return img_url_result

    # Skip downloading if image already exist
    glob_path = f"{directory_path}/{img_hash}.*"
    if glob.glob(glob_path):
        img_url_result.status = "exist"
        img_url_result.message = "Image already exists"
        img_url_result.img_path = glob_path
        img_url_result.print()
        return img_url_result

    img_extensions = (".jpg", ".jpeg", ".jfif", "jpe", ".gif", ".png", ".bmp", ".svg", ".webp", ".ico")
    content_type_to_ext = {
        "image/gif": ".gif",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/svg+xml": ".svg",
        "image/x-icon": ".ico"
    }

    try:
        response = requests.get(img_url, timeout=10)

        if response.ok:

            data = response.content
            content_type = response.headers["Content-Type"]

            if not any(img_path.name.endswith(ext) for ext in img_extensions):
                img_path = img_path.with_suffix(
                    content_type_to_ext[content_type]
                )

            # Skip saving if image has lower than minimun resolution
            tmp_pil = Image.open(io.BytesIO(data))
            if tmp_pil.width < min_width or tmp_pil.height < min_height:
                img_url_result.status = "small"
                img_url_result.message = f"Image {tmp_pil.width}x{tmp_pil.height} is less than {min_width}x{min_height}"
                # print("tmp pil:", tmp_pil.width, "x", tmp_pil.height, "min:", min_width, "x", min_height )
                return img_url_result

            with open(img_path, "wb") as f:
                f.write(data)

            img_url_result.status = "success"
            img_url_result.message = "Downloaded the image."
            img_url_result.img_path = str(img_path)

            # Log img_url
            downloaded_log[img_url] = 1

        else:
            img_url_result.status = "fail"
            img_url_result.message = (f"img_url response is not ok."
                                      f" response: {response}.")

    except (KeyboardInterrupt, SystemExit):
        raise

    except (requests.exceptions.SSLError,
            requests.exceptions.ConnectionError) as e:
        img_url_result.status = "fail"
        img_url_result.message = f"{type(e)}"

    except Exception as exception:
        img_url_result.status = "fail"
        img_url_result.message = (f"Something is wrong here.",
                                  f" Error: {type(exception), exception}")

    # Print result
    img_url_result.print()
    # if img_url_result.status == "fail":
    #     print(colored("    fail", 'red'), f"{img_url} - {img_url_result.message}")
    # else:
    #     print(colored("    fail", 'red'), f"{img_url} - {img_url_result.message}")
    #     print(f"    {img_url_result.message} ==> {img_path}")

    return img_url_result


#####


class YandexImagesDownloader:
    """Class to download images from Yandex """

    MAIN_URL = "https://yandex.ru/images/search"
    MAXIMUM_PAGES_PER_SEARCH = 50
    MAXIMUM_IMAGES_PER_PAGE = 30
    MAXIMUM_FILENAME_LENGTH = 50

    def __init__(self,
                 driver: Driver,
                 output_directory="download/",
                 limit=100,
                 isize=None,
                 min_width=None,
                 min_height=None,
                 exact_isize=None,
                 iorient=None,
                 extension=None,
                 color=None,
                 itype=None,
                 commercial=None,
                 recent=None,
                 pool=None,
                 similar_images=False,
                 negative=[]):

        # global negative_ids
        # negative_ids = negative  # Set global variable

        self.driver = driver
        self.output_directory = pathlib.Path(output_directory)
        self.limit = limit
        self.isize = isize
        self.min_width = min_width
        self.min_height = min_height
        self.exact_isize = exact_isize
        self.iorient = iorient
        self.extension = extension
        self.color = color
        self.itype = itype
        self.commercial = commercial
        self.recent = recent

        self.url_params = self.init_url_params()
        self.requests_headers = {
            'User-Agent':
                ("Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML,"
                 " like Gecko) Chrome/41.0.2228.0 Safari/537.36")
        }
        self.cookies = {}
        self.pool = pool
        self.similar_images = similar_images
        self.negative = negative  # List of negative image ids (hashes)

        print(f'Output directory is set to "{self.output_directory}/"')
        print(f"Limit of images is set to {self.limit}")

    def get_response(self):
        current_url = self.driver.current_url
        if self.similar_images:
            current_url = self.MAIN_URL + "?"

        for request in self.driver.requests:
            if str(request).startswith(current_url):
                return request.response

    def init_url_params(self):
        params = {
            "nomisspell": 1,
            "isize": self.isize,
            "iw": None,
            "ih": None,
            "iorient": self.iorient,
            "type": self.extension,
            "color": self.color,
            "itype": self.itype,
            "commercial": self.commercial,
            "recent": self.recent
        }

        if self.exact_isize:
            width, height = self.exact_isize
            params["isize"] = "eq"
            params["iw"] = width
            params["ih"] = height

        return params

    def get_url_params(self, page, text):
        if self.similar_images:
            params = {"p": page, "url": text, "rpt": "imagelike"}
        else:
            params = {"p": page, "text": text}
        params.update(self.url_params)

        return params

    def download_images_by_page(self, keyword, page, imgs_count,
                                sub_directory) -> PageResult:

        page_result = PageResult(status=None,
                                 message=None,
                                 page=page,
                                 errors_count=None,
                                 img_url_results=[])

        self.check_captcha_and_get(YandexImagesDownloader.MAIN_URL,
                                   params=self.get_url_params(page, keyword))

        response = self.get_response()

        if not response or not (response.reason == "OK"):
            page_result.status = "fail"
            page_result.message = (f"Page response is not ok."
                                   f" page: {page},",
                                   f" status_code: {response.status_code if response else '???'}.")
            page_result.errors_count = YandexImagesDownloader.MAXIMUM_IMAGES_PER_PAGE
            return page_result

        soup_page = BeautifulSoup(self.driver.page_source, "lxml")
        # Getting all image urls from page
        try:
            tag_sepr_item = soup_page.find_all("div", class_="serp-item")
            serp_items = [
                json.loads(item.attrs["data-bem"])["serp-item"]
                for item in tag_sepr_item
            ]
            img_hrefs = [key["img_href"] for key in serp_items]
        except Exception as e:
            page_result.status = "fail"
            page_result.message = str(e)
            page_result.errors_count = YandexImagesDownloader.MAXIMUM_IMAGES_PER_PAGE
            return page_result

        errors_count = 0
        for img_url in img_hrefs:
            if imgs_count >= self.limit:
                break

            if self.pool:
                img_url_result = self.pool.apply_async(
                    download_single_image,
                    # args=(),
                    kwds={
                        'img_url': img_url,
                        'output_directory': self.output_directory,
                        'sub_directory': sub_directory,
                        'min_width': self.min_width,
                        'min_height': self.min_height,
                        'negative_ids': self.negative,
                    })
            else:
                img_url_result = download_single_image(
                   img_url,
                   self.output_directory,
                   min_width=self.min_width,
                   min_height=self.min_height,
                   sub_directory=sub_directory
                )

            page_result.img_url_results.append(img_url_result)

            imgs_count += 1

        if self.pool:
            for i, img_url_result in enumerate(page_result.img_url_results):
                page_result.img_url_results[i] = img_url_result.get()
        errors_count += sum(1 if page_result.status == "fail" else 0
                            for page_result in page_result.img_url_results)

        page_result.status = "success"
        page_result.message = f"All successful images from page {page} downloaded."
        page_result.errors_count = errors_count

        return page_result

    def download_images_by_keyword(self, keyword, sub_directory="", label_prefix="") -> KeywordResult:
        keyword_result = KeywordResult(status=None,
                                       message=None,
                                       keyword=keyword,
                                       errors_count=None,
                                       page_results=[])

        if self.similar_images:
            params = {
               "url": keyword,
               "rpt": "imagelike"
            }
        else:
            params = {
                "text": keyword,
                "nomisspell": 1
           }

        self.check_captcha_and_get(YandexImagesDownloader.MAIN_URL,
                                   params=params)
        response = self.get_response()

        if not response or not (response.reason == "OK"):
            keyword_result = "fail"
            keyword_result.message = (
                "Failed to fetch a search page."
                f" url: {YandexImagesDownloader.MAIN_URL},"
                f" params: {params},"
                f" status_code: {response.status_code if response else '???'}")
            return keyword_result

        soup = BeautifulSoup(self.driver.page_source, "lxml")

        # Getting last_page.
        tag_serp_list = soup.find("div", class_="serp-list")
        if not tag_serp_list:
            keyword_result.status = "success"
            keyword_result.message = f"No images with keyword {keyword} found."
            keyword_result.errors_count = 0
            print(f"    {keyword_result.message}")
            return keyword_result
        serp_list = json.loads(tag_serp_list.attrs["data-bem"])["serp-list"]
        last_page = serp_list["lastPage"]
        actual_last_page = 1 + floor(
            self.limit / YandexImagesDownloader.MAXIMUM_IMAGES_PER_PAGE)

        print(f"  Found {last_page+1} pages of {keyword}.")

        # Getting all images.
        imgs_count = 0
        errors_count = 0

        for page in range(last_page + 1):
            if imgs_count >= self.limit:
                break

            if page > actual_last_page:
                actual_last_page += 1

            print(f"\n  [{label_prefix}]: Scrapping page {page+1}/{actual_last_page} {keyword}")

            page_result = self.download_images_by_page(keyword, page, imgs_count, sub_directory)
            keyword_result.page_results.append(page_result)
            page_result_urls_count = len(page_result.img_url_results)
            if page_result_urls_count <= 0:
                print("    Last page found (0 results)")
                break

            imgs_count += len(page_result.img_url_results)
            errors_count += page_result.errors_count

            time.sleep(0.5)  # bot id protection

        keyword_result.status = "success"
        keyword_result.message = f"All images for {keyword} downloaded!"
        keyword_result.errors_count = errors_count

        return keyword_result

    def download_images(self, keywords: List[str], single_output_dir=False) -> DownloaderResult:
        dowloader_result = DownloaderResult(status=None, message=None, keyword_results=[])
        dowloader_result.status = "fail"

        keywords_counter = 0
        keywords_count = len(keywords)
        for keyword in keywords:
            keywords_counter += 1

            if single_output_dir:
                sub_directory = ""
            elif self.similar_images:
                sub_directory = slugify(keyword)
            else:
                sub_directory = keyword

            # Skip if subdirectory (url) is too long
            if len(sub_directory) > 255:
                print(f"Sub-directory too long: {colored(sub_directory, 'cyan')}")
                continue

            print(f"{keywords_counter}/{keywords_count} Downloading images for {keyword}...")

            if single_output_dir:
                sub_directory = ""
            elif self.similar_images:
                sub_directory = slugify(keyword)
            else:
                sub_directory = keyword

            keyword_result = self.download_images_by_keyword(
                keyword,
                sub_directory=sub_directory,
                label_prefix=f"{keywords_counter}/{keywords_count}"  # Pass counter info for printing progress
            )
            dowloader_result.keyword_results.append(keyword_result)

            print(keyword_result.message)

        dowloader_result.status = "success"
        dowloader_result.message = "Everything is downloaded!"

        return dowloader_result

    class StopCaptchaInput(Exception):
        pass

    def check_captcha_and_get(self, url, params=None):
        """Checking for captcha on url and get url after that.
        If there is captcha, you have to type it in input() or quit."""

        url_with_params = f"{url}?{urlencode(params)}"

        del self.driver.requests
        self.driver.get(url_with_params)

        while True:
            soup = BeautifulSoup(self.driver.page_source, "lxml")

            if not soup.select(".form__captcha"):
                break

            print("Please, type the captcha in the browser, then press Enter or type [q] to exit")
            reply = input()
            if reply == "q":
                raise YandexImagesDownloader.StopCaptchaInput()

            del self.driver.requests
            self.driver.get(url_with_params)
