# -*- coding: utf-8 -*-
import logging
import re
import shutil
import subprocess
import undetected_chromedriver as uc

log = logging.getLogger(__name__)


def _parse_chrome_major(version_output: str):
    """从 Chrome/Chromium 版本输出中提取主版本号"""
    match = re.search(r"\b(\d+)\.\d+\.\d+\.\d+\b", version_output)
    if not match:
        return None

    return int(match.group(1))


def _detect_chrome_executable():
    """查找当前环境可用的 Chrome/Chromium 可执行文件"""
    candidates = [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "chrome",
    ]

    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return path

    return None


def _detect_chrome_major(browser_path: str | None):
    """读取本机 Chrome 主版本，用于匹配 ChromeDriver 主版本"""
    if not browser_path:
        return None

    try:
        result = subprocess.run(
            [browser_path, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as e:
        log.warning(f"⚠️ Chrome 版本检测失败: {e}")
        return None

    version_output = (result.stdout or result.stderr or "").strip()
    version_main = _parse_chrome_major(version_output)
    if version_main:
        log.info(f"✅ 检测到 Chrome: {version_output}，使用 ChromeDriver 主版本 {version_main}")
    else:
        log.warning(f"⚠️ 无法解析 Chrome 版本输出: {version_output}")

    return version_main


def create_browser(headless: bool = True):
    """创建并返回 Chrome WebDriver"""
    options = uc.ChromeOptions()

    base_args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--window-size=1920,1080",
        "--disable-blink-features=AutomationControlled",
        "--disable-extensions",
    ]

    for arg in base_args:
        options.add_argument(arg)

    if headless:
        options.add_argument("--headless=new")

    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0 Safari/537.36"
    )

    try:
        browser_path = _detect_chrome_executable()
        version_main = _detect_chrome_major(browser_path)
        driver_kwargs = {"options": options}

        if browser_path:
            driver_kwargs["browser_executable_path"] = browser_path

        if version_main:
            driver_kwargs["version_main"] = version_main

        driver = uc.Chrome(**driver_kwargs)
        driver.set_window_size(1920, 1080)

        # 反自动化基础伪装
        driver.execute_script("Object.defineProperty(navigator,'webdriver',{get:()=>false})")
        driver.execute_script("window.chrome={runtime:{}}")
        driver.execute_script("Object.defineProperty(navigator,'languages',{get:()=>['zh-CN','zh']})")
        driver.execute_script("Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3]})")

        return driver
    except Exception as e:
        log.error(f"❌ 浏览器启动失败: {e}")
        return None


def inject_cookies(driver, base_url: str, cookie_str: str, domain: str):
    """向浏览器注入 Cookie"""
    driver.get(base_url)

    for item in cookie_str.split(";"):
        item = item.strip()
        if not item or "=" not in item:
            continue

        name, value = item.split("=", 1)
        try:
            driver.add_cookie({
                "name": name.strip(),
                "value": value.strip(),
                "domain": domain,
                "path": "/",
                "secure": True,
                "httpOnly": False
            })
        except Exception as e:
            log.warning(f"⚠️ Cookie 注入失败: {name} -> {e}")
