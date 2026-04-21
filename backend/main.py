import sys
import asyncio

# 针对 Windows 系统的 Playwright 异步子进程兼容性修复
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from backend.spider import run_spider
from backend.database import export_to_excel
import sqlite3
import os
import json

app = FastAPI(title="Douyin Scrawl API", version="1.0.0", description="API Agent for serving cleaned datapanel data.")

# 配置 CORS，允许前端调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()
    print(f"  [STARTUP] Current Event Loop: {type(loop)}")
    if sys.platform == "win32":
        # 如果依然不是 Proactor，则在运行时发出警告
        from asyncio.windows_events import ProactorEventLoop
        if not isinstance(loop, ProactorEventLoop):
            print("  [WARNING] Windows ProactorEventLoop not in use! Playwright may fail.")

DB_PATH = os.path.join(os.path.dirname(__file__), "douyin_data.db")

def get_db_connection():
    """获取 SQLite 数据库连接并设置 row_factory 为字典形态"""
    if not os.path.exists(DB_PATH):
        raise Exception("Database file not found. Ensure pipeline Phase 1 & 2 ran successfully.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---- ---- 下方为同步 DB 访问封装函数，供 async 线程池调用以实现高并发不阻塞 ---- ----

def fetch_videos_query(skip: int, limit: int, keyword: str = None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        base_query = """
            SELECT v.*, a.nickname AS author_nickname, a.follower_count 
            FROM videos v
            LEFT JOIN authors a ON v.author_uid = a.uid
        """
        
        if keyword:
            query = base_query + " WHERE v.search_keyword = ? ORDER BY v.create_time DESC LIMIT ? OFFSET ?"
            cursor.execute(query, (keyword, limit, skip))
        else:
            query = base_query + " ORDER BY v.create_time DESC LIMIT ? OFFSET ?"
            cursor.execute(query, (limit, skip))
            
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def fetch_detailed_videos_query(skip: int, limit: int, keyword: str = None) -> list:
    """
    查询视频详情列表，JOIN authors 取粉丝数，并将 tags 字符串解析为列表。
    供 /api/videos/detailed 路由调用。
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        base_query = """
            SELECT
                v.aweme_id,
                v.desc        AS title,
                v.create_time,
                v.tags,
                v.digg_count,
                v.comment_count,
                v.share_count,
                v.collect_count,
                v.search_keyword,
                v.video_url,
                a.nickname    AS author_nickname,
                a.uid         AS author_uid,
                a.follower_count
            FROM videos v
            LEFT JOIN authors a ON v.author_uid = a.uid
        """
        if keyword:
            query = base_query + " WHERE v.search_keyword = ? ORDER BY v.digg_count DESC LIMIT ? OFFSET ?"
            cursor.execute(query, (keyword, limit, skip))
        else:
            query = base_query + " ORDER BY v.digg_count DESC LIMIT ? OFFSET ?"
            cursor.execute(query, (limit, skip))

        rows = cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            # 将 tags 逗号字符串解析为 list
            raw_tags = d.get('tags') or ''
            try:
                parsed = json.loads(raw_tags)
                d['tags'] = parsed if isinstance(parsed, list) else [raw_tags] if raw_tags else []
            except (json.JSONDecodeError, TypeError):
                d['tags'] = [t.strip() for t in raw_tags.split(',') if t.strip()]
            # 保证 video_url 始终有值（兜底拼接）
            if not d.get('video_url'):
                d['video_url'] = f"https://www.douyin.com/video/{d['aweme_id']}"
            result.append(d)
        return result


def fetch_stats_query(keyword: str = None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        where_clause = "WHERE search_keyword = ?" if keyword else ""
        where_args = (keyword,) if keyword else ()
        
        # 1. 互动数据 (柱状对比图)
        cursor.execute(f"""
            SELECT 
                SUM(digg_count) as total_digg,
                SUM(comment_count) as total_comment,
                SUM(share_count) as total_share,
                SUM(collect_count) as total_collect
            FROM videos {where_clause}
        """, where_args)
        interaction_bar = dict(cursor.fetchone() or {})
        
        # 处理可能为 None 的情况
        for k in interaction_bar:
            if interaction_bar[k] is None:
                interaction_bar[k] = 0
        
        # 2. 视频标签 (词云图)
        tag_where = "WHERE tags IS NOT NULL AND tags != ''"
        if keyword:
            tag_where += " AND search_keyword = ?"
            cursor.execute(f"SELECT tags FROM videos {tag_where}", (keyword,))
        else:
            cursor.execute(f"SELECT tags FROM videos {tag_where}")
        tags_rows = cursor.fetchall()
        tag_counts = {}
        tag_cooccurrence = {}
        for row in tags_rows:
            tags_str = row['tags']
            if isinstance(tags_str, str):
                try:
                    # 尝试反序列化 JSON，因为部分脚本可能会把 list 转 json 后存入 sqlite
                    tags_list = json.loads(tags_str)
                    if not isinstance(tags_list, list):
                        tags_list = [tags_str]
                except json.JSONDecodeError:
                    # 降级处理为普通逗号分隔的字符串解析
                    tags_list = [t.strip() for t in tags_str.split(',') if t.strip()]
                
                # 去重清洗，避免同一个视频里出现相同的两个标签导致自我关联
                tags_list = list(set([t for t in tags_list if t]))
                
                for i in range(len(tags_list)):
                    tag = tags_list[i]
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                    # 构建共现矩阵
                    for j in range(i + 1, len(tags_list)):
                        t1, t2 = sorted([tag, tags_list[j]])
                        pair = f"{t1}|||{t2}"
                        tag_cooccurrence[pair] = tag_cooccurrence.get(pair, 0) + 1
                        
        # 组装共现网络数据 (限制前 50 个核心节点以免过于拥挤)
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:50]
        top_tags = {t[0] for t in sorted_tags}
        
        nodes = [{"name": t, "value": count, "symbolSize": min(count * 5 + 10, 50)} for t, count in sorted_tags]
        links = []
        for pair, weight in tag_cooccurrence.items():
            t1, t2 = pair.split("|||")
            if t1 in top_tags and t2 in top_tags and weight > 0:
                links.append({"source": t1, "target": t2, "value": weight})
        
        network_data = {"nodes": nodes, "links": links}
                    
        # 3. 粉丝数与互动率的散点图 (粉丝数 vs 包含点赞评论分享汇总的互动率)
        scatter_sql = """
            SELECT 
                v.aweme_id,
                v.digg_count, v.comment_count, v.share_count, v.collect_count,
                a.follower_count, a.nickname
            FROM videos v
            INNER JOIN authors a ON v.author_uid = a.uid
        """
        if keyword:
            scatter_sql += " WHERE v.search_keyword = ?"
            cursor.execute(scatter_sql, (keyword,))
        else:
            cursor.execute(scatter_sql)
        scatter_rows = cursor.fetchall()
        scatter_data = []
        for r in scatter_rows:
            f_count = r['follower_count'] or 0
            if f_count > 0:
                total_interact = (r['digg_count'] or 0) + (r['comment_count'] or 0) + (r['share_count'] or 0) + (r['collect_count'] or 0)
                # 计算万分对比率或直接百分比率，作为互动率参考指标
                interaction_rate = round(total_interact / f_count, 6)
                scatter_data.append({
                    "aweme_id": r['aweme_id'],
                    "nickname": r['nickname'],
                    "follower_count": f_count,
                    "interaction_rate": interaction_rate,
                    "total_interaction": total_interact
                })

        # 4. 加权爆款指数 TOP 10 (水平柱状图)
        # 权重: digg*1, collect*2, comment*5, share*10
        viral_sql = f"""
            SELECT 
                desc AS title,
                (IFNULL(digg_count, 0) * 1 + IFNULL(collect_count, 0) * 2 + IFNULL(comment_count, 0) * 5 + IFNULL(share_count, 0) * 10) as viral_score
            FROM videos {where_clause}
            ORDER BY viral_score DESC
            LIMIT 10
        """
        cursor.execute(viral_sql, where_args)
        viral_data = [dict(row) for row in cursor.fetchall()]

        return {
            "interaction_bar": interaction_bar,
            "tag_cloud": tag_counts,
            "scatter_data": scatter_data,
            "viral_data": viral_data,
            "network_data": network_data
        }

# ---- ---- 异步 API 路由 ---- ----

@app.get("/api/videos", summary="获取视频列表数据")
async def get_videos(
    skip: int = Query(0, description="跳过行数"), 
    limit: int = Query(50, description="返回数量限制"),
    keyword: str = Query(None, description="搜索关键词")
):
    """
    提供最新抓取的抖音列表数据。包含短视频的基础指标和作者信息。
    """
    try:
        # 使用 asyncio.to_thread 卸载同步阻塞的 Sqlite 库访问，实现真正的异步与高并发处理响应
        data = await asyncio.to_thread(fetch_videos_query, skip, limit, keyword)
        return {"code": 200, "message": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/detailed", summary="获取视频详情列表（含 video_url 与标签数组）")
async def get_detailed_videos(
    keyword: str = Query(None, description="按搜索关键词筛选；为空则返回全量"),
    skip: int = Query(0, ge=0, description="分页偏移量"),
    limit: int = Query(50, ge=1, le=500, description="每页数量，最大 500")
):
    """
    返回结构化的视频详情列表，按点赞数降序排列。

    每条记录包含：
    - `aweme_id`、`title`（视频标题）、`create_time`
    - `tags`（标签数组，已解析）
    - `digg_count`、`comment_count`、`share_count`、`collect_count`
    - `video_url`（可直接跳转的抖音视频链接）
    - `author_nickname`、`author_uid`、`follower_count`（博主粉丝数）
    - `search_keyword`（来源关键词）
    """
    try:
        data = await asyncio.to_thread(fetch_detailed_videos_query, skip, limit, keyword)
        return {"code": 200, "message": "success", "total": len(data), "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats", summary="获取可视化看板聚合数据")
async def get_stats(keyword: str = Query(None, description="搜索关键词")):
    """
    获取给前端看板用于绘制 ECharts 的结构化业务数据集合。
    包含总播放点赞互动柱状图、标签词云和互动散点三项集合。
    """
    try:
        data = await asyncio.to_thread(fetch_stats_query, keyword)
        return {"code": 200, "message": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CrawlRequest(BaseModel):
    keyword: str
    limit: int = 10

@app.post("/api/crawl", summary="触发核心抓取流水线")
async def start_crawl(req: CrawlRequest):
    """
    接收前端页面传递的关键词和抓取条数上限。
    触发 Playwright 爬虫完成抓取 -> 清洗 -> 入库全流水线。
    完成后返回状态，前端可随即刷新图表。
    """
    result = await run_spider(keyword=req.keyword, limit=req.limit)
    if result.get("status") == "success":
        return {"code": 200, "message": result["message"], "data": result.get("data")}
    raise HTTPException(status_code=500, detail=result.get("message", "未知错误"))

@app.get("/api/download/{keyword}", summary="下载关键字相关的 Excel 数据流")
async def download_excel(keyword: str):
    """
    调用数据库层函数生成该关键字的 Excel，并通过 FileResponse 将附件下载到前端。
    若需要下载全量数据，可传入 'all' 代替 keyword。
    """
    actual_kw = "" if keyword.lower() == "all" else keyword
    try:
        file_path = await asyncio.to_thread(export_to_excel, actual_kw)
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="无法导出：没有找到该关键词对应的数据")
            
        filename = os.path.basename(file_path)
        # 返回 Excel 文件流
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件导出失败: {str(e)}")

# ── 静态前端文件挂载 ──────────────────────────────────────────────
# 必须在所有 /api/* 路由注册完毕后再挂载，否则会屏蔽 API 路由
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    # 显式使用 asyncio 循环
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, loop="asyncio")
