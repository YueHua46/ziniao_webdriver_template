import hashlib
import os
import shutil
import time
import traceback
from typing import Dict
import uuid
import json
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import subprocess
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from logger import logger
# from typing import Tuple
from typings import StoreInfo
from config import ZINIAO_CONFIG

is_windows = platform.system() == 'Windows'
is_mac = platform.system() == 'Darwin'

if is_windows:
    driver_folder_path = ZINIAO_CONFIG['driver_folder_path']   # 存放chromedriver的文件夹路径，程序自动下载driver文件到该路径下
    client_path = ZINIAO_CONFIG['client_path']  # 紫鸟客户端在本设备的路径
else:
    driver_folder_path = os.path.expanduser(r'~/webdriver')
    client_path = os.path.join(os.path.expanduser('~'), 'ziniao')
socket_port = ZINIAO_CONFIG['socket_port']  # 系统未被占用的端口

user_info = ZINIAO_CONFIG['user_info']

def _kill_process(version):
    """
    终止紫鸟客户端已启动的进程（若未在运行则静默跳过）
    :param version: 客户端版本
    """
    if version == "v5":
        process_name = 'SuperBrowser.exe'
    else:
        process_name = 'ziniao.exe'
    if is_windows:
        ret = subprocess.run(
            ['taskkill', '/f', '/t', '/im', process_name],
            capture_output=True,
            text=True,
        )
        if ret.returncode != 0:
            # 128/1 等表示“没有找到进程”，属于正常情况，不报错
            logger.info("紫鸟客户端未在运行，跳过终止进程")
        else:
            logger.info(f"已终止进程: {process_name}")
    elif is_mac:
        ret = subprocess.run(['killall', 'ziniao'], capture_output=True)
        if ret.returncode == 0:
            time.sleep(3)
        # 未运行时 killall 返回非 0，静默跳过


def _start_browser():
    """
    启动客户端
    :return:
    """
    try:
        if is_windows:
            cmd = [client_path, '--run_type=web_driver', '--ipc_type=http', '--port=' + str(socket_port)]
        elif is_mac:
            cmd = ['open', '-a', client_path, '--args', '--run_type=web_driver', '--ipc_type=http',
                   '--port=' + str(socket_port)]
        else:
            exit()
        subprocess.Popen(cmd)
        time.sleep(5)
    except Exception:
        logger.error('start browser process failed: ' + traceback.format_exc())
        exit()


def _update_core():
    """
    下载所有内核，打开店铺前调用，需客户端版本5.285.7以上
    因为http有超时时间，所以这个action适合循环调用，直到返回成功
    """
    data = {
        "action": "updateCore",
        "requestId": str(uuid.uuid4()),
    }
    data.update(user_info)
    while True:
        result = _send_http(data)
        logger.info(result)
        if result is None:
            logger.info("等待客户端启动...")
            time.sleep(2)
            continue
        if result.get("statusCode") is None or result.get("statusCode") == -10003:
            logger.info("当前版本不支持此接口，请升级客户端")
            return
        elif result.get("statusCode") == 0:
            logger.info("更新内核完成")
            return
        else:
            logger.warning(f"等待更新内核: {json.dumps(result)}")
            time.sleep(2)


def _send_http(data):
    """
    通讯方式
    :param data:
    :return:
    """
    try:
        url = 'http://127.0.0.1:{}'.format(socket_port)
        response = requests.post(url, json.dumps(data).encode('utf-8'), timeout=120)
        return json.loads(response.text)
    except Exception as err:
        logger.error(err)
        return None


def _delete_all_cache():
    """
    删除所有店铺缓存
    非必要的，如果店铺特别多、硬盘空间不够了才要删除
    """
    if not is_windows:
        return
    local_appdata = os.getenv('LOCALAPPDATA')
    cache_path = os.path.join(local_appdata, 'SuperBrowser')
    if os.path.exists(cache_path):
        shutil.rmtree(cache_path)


def _delete_all_cache_with_path(path):
    """
    :param path: 启动客户端参数使用--enforce-cache-path时设置的缓存路径
    删除所有店铺缓存
    非必要的，如果店铺特别多、硬盘空间不够了才要删除
    """
    if not is_windows:
        return
    cache_path = os.path.join(path, 'SuperBrowser')
    if os.path.exists(cache_path):
        shutil.rmtree(cache_path)


def _open_store(store_info, isWebDriverReadOnlyMode=0, isprivacy=0, isHeadless=0, cookieTypeSave=0, jsInfo=""):
    request_id = str(uuid.uuid4())
    data = {
        "action": "startBrowser"
        , "isWaitPluginUpdate": 0
        , "isHeadless": isHeadless
        , "requestId": request_id
        , "isWebDriverReadOnlyMode": isWebDriverReadOnlyMode
        , "cookieTypeLoad": 0
        , "cookieTypeSave": cookieTypeSave
        , "runMode": "1"
        , "isLoadUserPlugin": False
        , "pluginIdType": 1
        , "privacyMode": isprivacy
    }
    data.update(user_info)

    if store_info.isdigit():
        data["browserId"] = store_info
    else:
        data["browserOauth"] = store_info

    if len(str(jsInfo)) > 2:
        data["injectJsInfo"] = json.dumps(jsInfo)

    r = _send_http(data)
    if r is None:
        logger.error("startBrowser 调用失败，返回为空")
        return {"statusCode": -1, "msg": "startBrowser http failed"}
    code = str(r.get("statusCode"))
    if code == "0":
        return r
    elif code == "-10003":
        logger.error(f"login Err {json.dumps(r, ensure_ascii=False)}")
        return r
    else:
        logger.error(f"Fail {json.dumps(r, ensure_ascii=False)} ")
        return r


def _close_store(browser_oauth):
    request_id = str(uuid.uuid4())
    data = {
        "action": "stopBrowser"
        , "requestId": request_id
        , "duplicate": 0
        , "browserOauth": browser_oauth
    }
    data.update(user_info)

    r = _send_http(data)
    if r is None:
        logger.error("stopBrowser 调用失败，返回为空")
        return {"statusCode": -1, "msg": "stopBrowser http failed"}
    code = str(r.get("statusCode"))
    if code == "0":
        return r
    elif code == "-10003":
        logger.error(f"login Err {json.dumps(r, ensure_ascii=False)}")
        return r
    else:
        logger.error(f"Fail {json.dumps(r, ensure_ascii=False)} ")
        return r


def _get_browser_list() -> list:
    request_id = str(uuid.uuid4())
    data = {
        "action": "getBrowserList",
        "requestId": request_id
    }
    data.update(user_info)

    r = _send_http(data)
    if r is None:
        logger.error("getBrowserList 调用失败，返回为空")
        return []
    code = str(r.get("statusCode"))
    if code == "0":
        return r.get("browserList")
    elif code == "-10003":
        logger.error(f"login Err {json.dumps(r, ensure_ascii=False)}")
        return []
    else:
        logger.error(f"Fail {json.dumps(r, ensure_ascii=False)} ")
        return []


def _get_driver(open_ret_json, is_headless=False):
    core_type = open_ret_json.get('core_type')
    if core_type == 'Chromium' or core_type == 0:
        major = open_ret_json.get('core_version').split('.')[0]
        if is_windows:
            chrome_driver_path = os.path.join(driver_folder_path, 'chromedriver%s.exe') % major
        else:
            chrome_driver_path = os.path.join(driver_folder_path, 'chromedriver%s') % major
        logger.info(f"chrome_driver_path: {chrome_driver_path}")
        port = open_ret_json.get('debuggingPort')
        options = Options()
        options.add_argument('--log-level=3')
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
        options.add_experimental_option("debuggerAddress", '127.0.0.1:' + str(port))
        # 启用performance日志以支持CDP网络事件捕获
        try:
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        except Exception:
            pass
        if is_headless:
            options.add_argument('--headless')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(service=Service(chrome_driver_path), options=options)
        # 反检测脚本注入
        if is_headless:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.navigator.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'en']});
                """
            })
        return driver
    else:
        return None

def _custom_check_ip(driver, expected_ip):
    """
    自定义ip检测
    :param driver: driver实例
    :param expected_ip: 期望的ip
    :return: 检测结果
    """
    if not expected_ip:
        raise ValueError("期望的ip不能为空")
    driver.get("https://ip.sb/")
    # 等待页面加载完成
    wait = WebDriverWait(driver, timeout=10, poll_frequency=0.5)
    wait.until(EC.presence_of_element_located((By.XPATH, "//td[@class='proto_address']/a")))
    ip_element = driver.find_element(By.XPATH, "//td[@class='proto_address']/a")
    ip = ip_element.text
    logger.info(f"当前店铺浏览器检测到的IP：{ip}")
    logger.info(f"期望的IP：{expected_ip}")
    return ip == expected_ip

def _open_ip_check(driver, ip_check_url):
    """
    打开ip检测页检测ip是否正常
    :param driver: driver实例
    :param ip_check_url ip检测页地址
    :return 检测结果
    """
    try:
        driver.get(ip_check_url)
        # 等待ip检测页加载完成
        wait = WebDriverWait(driver, timeout=30, poll_frequency=0.5)
        wait.until(EC.presence_of_element_located((By.XPATH, '//button[contains(@class, "styles_btn--success")]')))
        return True
    except NoSuchElementException:
        logger.warning("未找到ip检测成功元素")
        return False
    except Exception as e:
        logger.error("ip检测异常:" + traceback.format_exc())
        return False


def _open_launcher_page(driver, launcher_page):
    driver.get(launcher_page)
    # 等待页面加载完成
    time.sleep(3)
    try:
        # 使用 WebDriverWait 等待页面加载状态为 complete
        WebDriverWait(driver, timeout=30).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
    except Exception as e:
        logger.warning(f"等待页面加载超时: {e}")


def _get_exit():
    """
    关闭客户端
    :return:
    """
    data = {"action": "exit", "requestId": str(uuid.uuid4())}

    data.update(user_info)

    logger.info('@@ get_exit...' + json.dumps(data, ensure_ascii=False))
    _send_http(data)


def _encrypt_sha1(fpath: str) -> str:
    with open(fpath, 'rb') as f:
        return hashlib.new('sha1', f.read()).hexdigest()


def _download_file(url, save_path):
    # 发送GET请求获取文件内容
    response = requests.get(url, stream=True)
    # 检查请求是否成功
    if response.status_code == 200:
        # 创建一个本地文件并写入下载的内容（如果文件已存在，将被覆盖）
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        logger.info(f"文件已成功下载并保存到：{save_path}")
    else:
        logger.error(f"下载失败，响应状态码为：{response.status_code}")


def download_driver():
    if is_windows:
        config_url = "https://cdn-superbrowser-attachment.ziniao.com/webdriver/exe_32/config.json"
    elif is_mac:
        arch = platform.machine()
        if arch == 'x86_64':
            config_url = "https://cdn-superbrowser-attachment.ziniao.com/webdriver/mac/x64/config.json"
        elif arch == 'arm64':
            config_url = "https://cdn-superbrowser-attachment.ziniao.com/webdriver/mac/arm64/config.json"
        else:
            return
    else:
        return
    response = requests.get(config_url)
    # 检查请求是否成功
    if response.status_code == 200:
        # 获取文本内容
        txt_content = response.text
        config = json.loads(txt_content)
    else:
        logger.error(f"下载驱动失败，状态码：{response.status_code}")
        exit()
    if not os.path.exists(driver_folder_path):
        os.makedirs(driver_folder_path)

    # 获取文件夹中所有chromedriver文件
    driver_list = [filename for filename in os.listdir(driver_folder_path) if filename.startswith('chromedriver')]

    for item in config:
        filename = item['name']
        if is_windows:
            filename = filename + ".exe"
        local_file_path = os.path.join(driver_folder_path, filename)
        if filename in driver_list:
            # 判断sha1是否一致
            file_sha1 = _encrypt_sha1(local_file_path)
            if file_sha1 == item['sha1']:
                logger.info(f"驱动{filename}已存在，sha1校验通过...")
            else:
                logger.warning(f"驱动{filename}的sha1不一致，重新下载...")
                _download_file(item['url'], local_file_path)
                # mac首次下载修改文件权限
                if is_mac:
                    cmd = ['chmod', '+x', local_file_path]
                    subprocess.Popen(cmd)
        else:
            logger.info(f"驱动{filename}不存在，开始下载...")
            _download_file(item['url'], local_file_path)
            # mac首次下载修改文件权限
            if is_mac:
                cmd = ['chmod', '+x', local_file_path]
                subprocess.Popen(cmd)

def close_store_and_quit_driver(store_id, driver):
    _close_store(store_id)
    driver.quit()

def _use_one_browser_run_task(browser, is_headless: bool = False):
    """
    打开一个店铺运行脚本
    :param browser: 店铺信息
    :return: (driver, store_id, store_name) 或 None
    """
    # 如果要指定店铺ID, 获取方法:登录紫鸟客户端->账号管理->选择对应的店铺账号->点击"查看账号"进入账号详情页->账号名称后面的ID即为店铺ID
    store_id = browser.get('browserOauth')
    store_name = browser.get("browserName")
    # 打开店铺
    logger.info(f"=====打开店铺：{store_name}=====")
    ret_json = _open_store(store_id, isHeadless = 1 if is_headless else 0)
    logger.info(ret_json)
    code = str(ret_json.get("statusCode")) if isinstance(ret_json, dict) else "-1"
    if code != "0":
        logger.error(f"打开店铺失败，statusCode={code}")
        return None
    logger.info(
        "调试端口=%s, Chromium内核版本=%s",
        ret_json.get("debuggingPort"),
        ret_json.get("coreVersion"),
    )
    store_id = ret_json.get("browserOauth")
    if store_id is None:
        store_id = ret_json.get("browserId")
    # 使用驱动实例开启会话
    driver = _get_driver(ret_json, is_headless)
    if driver is None:
        logger.info(f"=====关闭店铺：{store_name}=====")
        _close_store(store_id)
        return None

    # 等待店铺打开完成
    try:
        # 使用 WebDriverWait 等待页面加载状态为 complete
        WebDriverWait(driver, timeout=30).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
    except Exception as e:
        logger.warning(f"等待店铺打开超时: {e}")

    ip_usable = False
    if is_headless:
        ip_usable = _custom_check_ip(driver, ret_json.get("ip"))
        if not ip_usable:
            logger.warning("ip检测不通过，请检查")
            close_store_and_quit_driver(store_id, driver)
            return None
    else:
        # 获取ip检测页地址
        ip_check_url = ret_json.get("ipDetectionPage")
        if not ip_check_url:
            logger.warning("ip检测页地址为空，请升级紫鸟浏览器到最新版")
            logger.info(f"=====关闭店铺：{store_name}=====")
            close_store_and_quit_driver(store_id, driver)
            exit()
        ip_usable = _open_ip_check(driver, ip_check_url)
    # 执行脚本
    try:
        if ip_usable:
            logger.info("ip检测通过，打开店铺平台主页")
            _open_launcher_page(driver, ret_json.get("launcherPage"))
            logger.info(f"店铺{store_name}打开成功")
            # 是否成功返回
            # 返回 driver、store_id、store_name
            return {
                "driver": driver,
                "store_id": store_id,
                "store_name": store_name
            }
        else:
            logger.warning("ip检测不通过，请检查")
            close_store_and_quit_driver(store_id, driver)
            return None
    except:
        logger.error("脚本运行异常:" + traceback.format_exc())
        close_store_and_quit_driver(store_id, driver)
        return None

def _check_platform_version():
    is_windows = platform.system() == 'Windows'
    is_mac = platform.system() == 'Darwin'

    if not is_windows and not is_mac:
        raise "webdriver/cdp只支持windows和mac操作系统"

def _init_process():
    """ 需要从系统右下角角标将紫鸟浏览器退出后再运行"""

    _check_platform_version()

    """  
    windows用
    有店铺运行的时候，会删除失败
    删除所有店铺缓存，非必要的，如果店铺特别多、硬盘空间不够了才要删除
    _delete_all_cache()

    启动客户端参数使用--enforce-cache-path时用这个方法删除，传入设置的缓存路径删除缓存
    delete_all_cache_with_path(path)
    """

    '''下载各个版本的webdriver驱动'''
    download_driver()

    # 终止紫鸟客户端已启动的进程
    # todo 3、v5与v6的进程名不同，按版本修改v5或v6
    _kill_process(version="v5")

    logger.info("=====启动客户端=====")
    _start_browser()
    logger.info("=====更新内核=====")
    _update_core()

def open_store_by_name(store_name: str, browser_list=None, is_headless: bool = False) -> tuple[StoreInfo, str]:
    """
    根据店铺名称打开店铺
    :param store_name: 店铺名称
    :param browser_list: 已获取的店铺列表（推荐主流程只初始化一次并传入）
    :param is_headless: 是否无头模式
    :return: (StoreInfo, str) 店铺信息和错误信息
    """
    err_msg = ''
    if browser_list is None:
        # 兼容老用法，自动初始化
        _init_process()
        logger.info("=====获取店铺列表=====")
        browser_list = _get_browser_list()
    if not browser_list:
        logger.warning("browser list is empty")
        err_msg = "browser list is empty"
        return None, err_msg    
    for browser in browser_list:
        if browser.get("browserName").lower() == store_name.lower():
            return _use_one_browser_run_task(browser, is_headless), err_msg
    err_msg = f"店铺不存在：{store_name}"
    logger.warning(err_msg)
    return None, err_msg


def open_stores_by_names(store_names: list, browser_list=None, is_headless: bool = False, max_threads: int = 5):
    """
    并发打开多个店铺，返回每个店铺的 driver、store_id、store_name 等信息组成的列表。
    :param store_names: 店铺名称列表
    :param browser_list: 已获取的店铺列表（推荐主流程只初始化一次并传入）
    :param is_headless: 是否无头模式
    :param max_threads: 最大并发线程数
    :return: [{"driver":..., "store_id":..., "store_name":...}, ...]
    """
    if browser_list is None:
        # 兼容老用法，自动初始化
        _init_process()
        logger.info("=====获取店铺列表=====")
        browser_list = _get_browser_list()
    if not browser_list:
        logger.warning("browser list is empty")
        return []
    name2browser = {browser.get("browserName"): browser for browser in browser_list}
    selected_browsers = [name2browser[name] for name in store_names if name in name2browser]
    results = []
    def open_one(browser):
        return _use_one_browser_run_task(browser, is_headless)
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        future_to_name = {executor.submit(open_one, browser): browser.get("browserName") for browser in selected_browsers}
        for future in as_completed(future_to_name):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(f"打开店铺 {future_to_name[future]} 失败: {e}")
    return results
