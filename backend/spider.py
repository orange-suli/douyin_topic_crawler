import asyncio
import json
import math
import random
import os
from playwright.async_api import async_playwright, Page, Response

# ANSI 颜色定义，用于终端高亮
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# 临时存放 raw_data.json 的路径 (位于 backend 目录下)
RAW_DATA_PATH = os.path.join(os.path.dirname(__file__), "raw_data.json")

class DouyinSpider:
    def __init__(self, keyword: str, limit: int = 10):
        self.keyword = keyword
        self.limit = limit
        self.scraped_data = []

    async def handle_response(self, response: Response):
        """
        核心数据截获逻辑，监听匹配后端 API 的响应体。
        绝不通过解析脆弱的 HTML DOM 获取基础数据。
        """
        # 拦截包含目标 XHR 的请求
        if "/aweme/v1/web/search/item/" in response.url and response.status == 200:
            # 应对 preflight（OPTIONS）请求，通常无 JSON 响应体会引发报错，因此包含在 try-catch 中
            if response.request.method == "OPTIONS":
                return
                
            try:
                # 获取 JSON 响应体
                data = await response.json()
                print(f"{GREEN}[+] 成功截获搜素接口数据! URL: {response.url[:60]}...{RESET}")
                
                # 注入搜索关键词
                if isinstance(data, dict):
                    data['_keyword'] = self.keyword
                
                # 将每次截获的 data 追加储存
                self.scraped_data.append(data)
                
                # 写入本地 raw_data.json 暂存 (交接给 Data Agent 使用)
                with open(RAW_DATA_PATH, "w", encoding="utf-8") as f:
                    json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)
                print(f"{GREEN}[*] 数据已成功暂存至: {RAW_DATA_PATH}{RESET}")
                
            except Exception as e:
                print(f"{RED}[-] 解析 JSON 失败或该响应非 JSON 格式: {str(e)[:100]}{RESET}")

    async def human_machine_verification(self, page: Page):
        """
        反风控与人机协作机制：
        若检测到滑块验证、风控弹窗等阻断型警告，立即挂起并呼唤人工。
        """
        try:
            # 1. 简单等待一下页面渲染
            await asyncio.sleep(2)
            
            # 2. 检测滑块验证码相关特征
            captcha = page.locator(".captcha_verify_container, #captcha_container").first
            if await captcha.count() > 0 and await captcha.is_visible():
                print(f"{RED}\n[!!!] 拦截警告: 检测到滑块/验证码风控！{RESET}")
                print(f"{YELLOW}[*] 等待手动滑块验证中，请在 Chromium 窗口中操作...程序会自动检测放行。{RESET}")
                # 循环检测弹窗何时消失
                while await captcha.count() > 0 and await captcha.is_visible():
                    await asyncio.sleep(1)
                print(f"{GREEN}[+] 风控已解除，继续抓取流...{RESET}")
                
            # 3. 检测强制登录弹窗或登录遮罩层
            # 抖音常见的登录弹窗 class 或者 id
            login_modal = page.locator(".login-guide-container, .dy-account-close, #login-pannel, .login-mask").first
            if await login_modal.count() > 0 and await login_modal.is_visible():
                print(f"{YELLOW}[!] 检测到未登录拦截框，程序无法继续获取数据...{RESET}")
                print(f"{RED}[!!!] 请在当前浏览器窗口用抖音 APP 扫码登录！{RESET}")
                print(f"{YELLOW}[*] 程序会在登录成功（死循环轮询检测到弹窗消失）后自动恢复抓取...{RESET}")
                while await login_modal.count() > 0 and await login_modal.is_visible():
                    await asyncio.sleep(2)
                print(f"{GREEN}[+] 已检测到登录状态，继续当前流程...{RESET}")
        except Exception as e:
            # 防止因为 DOM 剧烈变动导致检测崩溃，静默通过，但不阻断整条流
            pass

    async def random_delay(self):
        """
        执行规范：每次页面操作注入 2s - 8s 随机延迟
        """
        delay = random.uniform(2, 8)
        print(f"[*] 防风控延时 {delay:.2f} 秒...")
        await asyncio.sleep(delay)

    async def run(self):
        print(f"{GREEN}=== 抖音 Scraper Agent 初始化 ==={RESET}")
        
        # 存放用户浏览器配置（Cookies、LocalStorage）的目录，用来保持免登录状态
        USER_DATA_DIR = os.path.join(os.path.dirname(__file__), "user_data")
        os.makedirs(USER_DATA_DIR, exist_ok=True)
        
        async with async_playwright() as p:
            # 依照规范：headless=False 并且绑定持久化用户目录
            context = await p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                args=['--disable-blink-features=AutomationControlled']  # 基础反嗅探
            )
            
            # 反爬绕过：注入一段抹消 webdriver 特征的 JS
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # 持久化上下文会默认自带一个 page
            pages = context.pages
            page = pages[0] if len(pages) > 0 else await context.new_page()
            
            # 注册网络响应拦截回调 - 优先保证异步被执行
            page.on("response", self.handle_response)

            try:
                # 步骤 1：主页种下 Cookie
                print("[*] 准备进入抖音首页进行会话初始化...")
                await page.goto("https://www.douyin.com/", wait_until="commit")
                await self.human_machine_verification(page)
                await self.random_delay()

                # 步骤 2：进行关键词搜索跳转
                # 注：直接以 query 参数跳转会有很大机率触发页面内的二次跳转或渲染缺失，但对纯 API 监听来说影响较小
                search_url = f"https://www.douyin.com/search/{self.keyword}?type=video"
                print(f"[*] 正在跳转关键词搜索页 (Keyword: {self.keyword})...")
                await page.goto(search_url, wait_until="domcontentloaded")
                
                # 给足够时间让页面发起搜索请求
                await self.random_delay()
                await self.human_machine_verification(page)

                # 步骤 3：模拟下划操作，触发接下来的分页请求
                # ceil 向上取整确保小 limit（如 5）也能触发至少一次完整的 XHR
                scroll_times = max(1, math.ceil(self.limit / 10))
                for i in range(scroll_times):
                    print(f"[*] 模拟向下滑动，尝试提取更多分页数据 (第 {i+1}/{scroll_times} 次)...")
                    await page.mouse.wheel(0, 1500)
                    await self.random_delay()
                    await self.human_machine_verification(page)
                    
            except Exception as e:
                print(f"{RED}[-] 运行过程中出现异常终止: {e}{RESET}")
            finally:
                print(f"{GREEN}[*] Playwright 任务完结，准备断开浏览器持久化连接以保存 Cookie 等内容。{RESET}")
                await context.close()


async def run_spider(keyword: str, limit: int) -> dict:
    """
    通过前端动态传参启动的爬取核心逻辑 API。
    包含：爬取 -> 清洗 -> 入库 流转，并返回一个状态字典。

    可被 FastAPI 主程序以 `from backend.spider import run_spider` 的形式导入调用，
    也支持直接通过 `python backend/spider.py` 在命令行运行（见 __main__ 入口）。
    """
    spider = DouyinSpider(keyword=keyword, limit=limit)
    await spider.run()

    if not spider.scraped_data:
        return {
            "status": "error",
            "keyword": keyword,
            "message": "未截获到有效的数据，可能遇到了爬虫风控或网络超时。",
        }

    try:
        # 防御性导入：兼容「python backend/spider.py」直接运行
        # 与「from backend.spider import run_spider」被 FastAPI 导入两种场景
        try:
            from cleaner import DataCleaner
            from database import batch_insert_videos, batch_insert_authors
        except ModuleNotFoundError:
            from backend.cleaner import DataCleaner
            from backend.database import batch_insert_videos, batch_insert_authors

        videos_df, authors_df = DataCleaner.clean_raw_data(spider.scraped_data)

        if videos_df.empty:
            return {
                "status": "error",
                "keyword": keyword,
                "message": "数据截获成功但清洗后无有效视频记录，请检查接口响应结构。",
            }

        # [Fix 1] 强制按 limit 截断，保证入库条数严格不超过用户期望值
        # 截获的 XHR 条数由抖音服务端决定（非确定性），此处是唯一强约束点
        original_count = len(videos_df)
        videos_df = videos_df.head(limit)
        if len(videos_df) < original_count:
            print(f"[*] limit 截断: 截获 {original_count} 条 -> 保留 {len(videos_df)} 条（limit={limit}）")

        # 同步过滤 authors_df，只保留截断后视频实际涉及的博主，避免孤立记录入库
        included_uids = set(videos_df['author_uid'].tolist())
        authors_df = authors_df[authors_df['uid'].isin(included_uids)]

        batch_insert_videos(videos_df)
        batch_insert_authors(authors_df)

        return {
            "status": "success",
            "keyword": keyword,
            "message": "数据抓取及入库流水线完成",
            "data": {
                "videos_saved": len(videos_df),
                "authors_saved": len(authors_df),
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "keyword": keyword,
            "message": f"流水线清洗或入库环节遇到错误: {str(e)}",
        }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="抖音爬虫")
    parser.add_argument("--keyword", type=str, default="数据分析", help="搜索关键词")
    parser.add_argument("--limit", type=int, default=10, help="限制条数")
    args = parser.parse_args()
    
    result = asyncio.run(run_spider(keyword=args.keyword, limit=args.limit))
    print("返回状态结果:", result)
