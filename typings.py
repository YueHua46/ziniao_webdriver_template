from typing import TypedDict, Optional
from selenium import webdriver


class StoreInfo(TypedDict):
    driver: webdriver.Chrome
    store_name: str
    store_id: str

