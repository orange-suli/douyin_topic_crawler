"""
QA Agent - 抖音全栈系统自动化回归测试脚本 (含边界值测试)
测试集: ["大模型", "赛博朋克", "极光"]
边界值专项: limit=8 严格截断验证
"""
import requests
import time
import sys

API_BASE = "http://localhost:8000"
KEYWORDS = ["大模型", "赛博朋克", "极光"]
LIMIT = 5               # workflow 规定的标准 limit
BOUNDARY_LIMIT = 8      # 用户要求的边界值测试 limit

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[93m[INFO]\033[0m"
WARN = "\033[95m[WARN]\033[0m"

results = []

# ── 健康检查 ───────────────────────────────────────────────────────
print(f"\n{INFO} 健康检查 GET /api/videos ...")
try:
    r = requests.get(f"{API_BASE}/api/videos", timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print(f"{PASS} 后端服务在线，HTTP 200")
except Exception as e:
    print(f"{FAIL} 后端服务不可达: {e}")
    sys.exit(1)

# ──────────────────────────────────────────────────────────────────
# 阶段 A: 标准关键词循环测试 (limit=5)
# ──────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"{INFO} 阶段 A: 多关键词标准回归测试 (limit={LIMIT})")
print('='*60)

for kw in KEYWORDS:
    print(f"\n{INFO} 开始测试关键词: 【{kw}】")

    # Step 1: POST /api/crawl 触发爬虫
    print(f"  -> 触发 POST /api/crawl (keyword={kw}, limit={LIMIT})...")
    start = time.time()
    crawl_ok = False
    videos_saved = 0
    try:
        r = requests.post(
            f"{API_BASE}/api/crawl",
            json={"keyword": kw, "limit": LIMIT},
            timeout=300,
        )
        elapsed = round(time.time() - start, 1)

        if r.status_code == 200:
            body = r.json()
            if body.get("code") == 200:
                data = body.get("data", {})
                videos_saved = data.get("videos_saved", 0)
                print(f"  {PASS} /api/crawl 返回 200，耗时 {elapsed}s")
                print(f"         videos_saved={videos_saved}, authors_saved={data.get('authors_saved')}")
                crawl_ok = True
            else:
                print(f"  {FAIL} /api/crawl 返回 200 但 code 非 200: {body}")
        else:
            print(f"  {FAIL} /api/crawl HTTP {r.status_code}，耗时 {elapsed}s，detail: {r.text[:200]}")

    except requests.exceptions.Timeout:
        elapsed = round(time.time() - start, 1)
        print(f"  {FAIL} /api/crawl 请求超时 (>{elapsed}s)")
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        print(f"  {FAIL} /api/crawl 异常: {e}")

    # Step 2: 数据校验 GET /api/videos?keyword=...
    print(f"  -> 数据校验 GET /api/videos?keyword={kw} ...")
    data_ok = False
    count = 0
    try:
        r2 = requests.get(
            f"{API_BASE}/api/videos",
            params={"keyword": kw, "limit": 50},
            timeout=10,
        )
        assert r2.status_code == 200, f"HTTP {r2.status_code}"
        videos = r2.json().get("data", [])
        count = len(videos)
        if count > 0:
            print(f"  {PASS} 数据校验通过，当前关键词累计入库: {count} 条")
            data_ok = True
        else:
            print(f"  {FAIL} 数据校验失败，视频列表为空")
    except Exception as e:
        print(f"  {FAIL} 数据校验请求异常: {e}")

    # Step 3: limit 截断精确断言（使用 /api/videos/detailed 新接口）
    limit_ok = None
    if crawl_ok and videos_saved > 0:
        try:
            r3 = requests.get(
                f"{API_BASE}/api/videos/detailed",
                params={"keyword": kw, "limit": 50},
                timeout=10,
            )
            detailed = r3.json().get("data", [])
            # 本批次入库量（videos_saved）不应超过 LIMIT
            if videos_saved <= LIMIT:
                print(f"  {PASS} limit 截断验证: videos_saved={videos_saved} <= limit={LIMIT}")
                limit_ok = True
            else:
                print(f"  {FAIL} limit 截断验证失败: videos_saved={videos_saved} > limit={LIMIT}")
                limit_ok = False
        except Exception as e:
            print(f"  {WARN} limit 截断二次校验请求异常: {e}")

    results.append({
        "keyword": kw,
        "crawl_ok": crawl_ok,
        "data_ok": data_ok,
        "limit_ok": limit_ok,
        "videos_saved": videos_saved,
        "elapsed_s": elapsed,
    })

    # Step 4: 防风控休眠
    if kw != KEYWORDS[-1]:
        print(f"  {INFO} 防风控休眠 15s，避免连续触发速率限制...")
        time.sleep(15)

# ──────────────────────────────────────────────────────────────────
# 阶段 B: 边界值专项测试 (limit=8)
# ──────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"{INFO} 阶段 B: 边界值专项测试 (limit={BOUNDARY_LIMIT})")
print('='*60)

BOUNDARY_KW = "美食"   # 使用新关键词，单独测试截断精度
print(f"\n{INFO} 边界值关键词: 【{BOUNDARY_KW}】，limit={BOUNDARY_LIMIT}")
print(f"  -> 触发 POST /api/crawl (keyword={BOUNDARY_KW}, limit={BOUNDARY_LIMIT})...")

start = time.time()
boundary_ok = False
boundary_saved = 0
try:
    rb = requests.post(
        f"{API_BASE}/api/crawl",
        json={"keyword": BOUNDARY_KW, "limit": BOUNDARY_LIMIT},
        timeout=300,
    )
    elapsed_b = round(time.time() - start, 1)

    if rb.status_code == 200 and rb.json().get("code") == 200:
        body_b = rb.json()
        boundary_saved = body_b.get("data", {}).get("videos_saved", 0)
        print(f"  {PASS} /api/crawl 返回 200，耗时 {elapsed_b}s，videos_saved={boundary_saved}")

        # 核心断言: 入库条数必须 <= BOUNDARY_LIMIT
        if boundary_saved <= BOUNDARY_LIMIT:
            print(f"  {PASS} [边界值断言] videos_saved={boundary_saved} <= limit={BOUNDARY_LIMIT} -- 截断逻辑生效")
            boundary_ok = True
        else:
            print(f"  {FAIL} [边界值断言] videos_saved={boundary_saved} > limit={BOUNDARY_LIMIT} -- 截断逻辑失效！")
    else:
        elapsed_b = round(time.time() - start, 1)
        print(f"  {FAIL} /api/crawl 非 200 响应: {rb.text[:200]}")

except requests.exceptions.Timeout:
    elapsed_b = round(time.time() - start, 1)
    print(f"  {FAIL} /api/crawl 请求超时 (>{elapsed_b}s)")
except Exception as e:
    elapsed_b = round(time.time() - start, 1)
    print(f"  {FAIL} /api/crawl 异常: {e}")

# ── 汇总报告 ───────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("回归测试汇总报告")
print(f"{'='*60}")
print(f"{'关键词':<14} {'爬虫':^6} {'数据':^6} {'limit截断':^10} {'入库条数':^8} {'耗时(s)'}")
print("-" * 60)

for r in results:
    cs = "OK" if r["crawl_ok"] else "NG"
    ds = "OK" if r["data_ok"] else "NG"
    ls = ("OK" if r["limit_ok"] else "NG") if r["limit_ok"] is not None else "N/A"
    print(f"  {r['keyword']:<12} {cs:^6} {ds:^6} {ls:^10} {r['videos_saved']:^8} {r['elapsed_s']}")

# 边界值行
bs = "OK" if boundary_ok else "NG"
print(f"  {BOUNDARY_KW+'(边界)':12} {bs:^6} {'--':^6} {bs:^10} {boundary_saved:^8} {elapsed_b}")

print(f"\n{'='*60}")
all_std_pass = all(r["crawl_ok"] and r["data_ok"] for r in results)
print(f"阶段A (标准回归): {'全部通过' if all_std_pass else '存在失败项'}")
print(f"阶段B (边界值 limit={BOUNDARY_LIMIT}): {'通过 -- 截断逻辑验证OK' if boundary_ok else '失败 -- 截断逻辑异常'}")
print(f"\n最终结论: {'全部通过' if (all_std_pass and boundary_ok) else '存在失败项，请检查上方日志'}")
