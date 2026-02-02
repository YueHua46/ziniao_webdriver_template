from logger import logger
from ziniao_func import open_store_by_name

def main():
    logger.info(f"基础紫鸟WebDriver项目模板")
    open_store_by_name("Test-Store")


if __name__ == '__main__':
    main()