import sqlite3
import pandas as pd
from contextlib import contextmanager
import os
from threading import Lock

DB_PATH = os.path.join(os.path.dirname(__file__), "douyin_data.db")
db_lock = Lock()

@contextmanager
def get_db_connection():
    """线程安全的数据库连接上下文管理器"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        try:
            yield conn
        finally:
            conn.commit()
            conn.close()

def init_db():
    """初始化数据库表结构"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 视频表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                aweme_id TEXT PRIMARY KEY,
                desc TEXT,
                create_time TEXT,
                author_uid TEXT,
                digg_count INTEGER,
                comment_count INTEGER,
                share_count INTEGER,
                collect_count INTEGER,
                tags TEXT,
                search_keyword TEXT,
                video_url TEXT
            )
        ''')
        
        # 热迁移：如果旧库已存在但缺少 video_url 列，则动态添加，避免重建库
        try:
            cursor.execute("ALTER TABLE videos ADD COLUMN video_url TEXT")
        except Exception:
            pass  # 字段已存在则静默跳过
        
        # 作者表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS authors (
                uid TEXT PRIMARY KEY,
                nickname TEXT,
                follower_count INTEGER
            )
        ''')

def batch_insert_videos(df: pd.DataFrame):
    """批量插入视频数据"""
    if df.empty:
        return
        
    required_cols = ['aweme_id', 'desc', 'create_time', 'author_uid', 'digg_count', 
                     'comment_count', 'share_count', 'collect_count', 'tags', 
                     'search_keyword', 'video_url']
    
    # 保障列存在且过滤
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
    insert_df = df[required_cols]

    with get_db_connection() as conn:
        # 使用 replace 避免重复抓取导致的 primary key 冲突
        insert_df.to_sql('videos', conn, if_exists='append', index=False, 
                         method=lambda table, conn, keys, data_iter:
                             conn.executemany(
                                 f"INSERT OR REPLACE INTO {table.name} ({', '.join(keys)}) "
                                 f"VALUES ({', '.join(['?'] * len(keys))})",
                                 data_iter
                             )
                        )

def batch_insert_authors(df: pd.DataFrame):
    """批量插入作者数据"""
    if df.empty:
        return
        
    required_cols = ['uid', 'nickname', 'follower_count']
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
    insert_df = df[required_cols]
    
    # 去重处理（同一个 batch 抓取到同一个博主的多个视频时可能会有重复博主）
    insert_df = insert_df.drop_duplicates(subset=['uid'])

    with get_db_connection() as conn:
        insert_df.to_sql('authors', conn, if_exists='append', index=False,
                         method=lambda table, conn, keys, data_iter:
                             conn.executemany(
                                 f"INSERT OR REPLACE INTO {table.name} ({', '.join(keys)}) "
                                 f"VALUES ({', '.join(['?'] * len(keys))})",
                                 data_iter
                             )
                        )

def export_to_excel(keyword: str) -> str:
    """从数据库读取关键词数据并导出为 Excel 文件，返回文件绝对路径"""
    query = """
        SELECT v.*, a.nickname, a.follower_count 
        FROM videos v
        LEFT JOIN authors a ON v.author_uid = a.uid
    """
    params = []
    if keyword:
        query += " WHERE v.search_keyword = ?"
        params.append(keyword)
    
    # 使用 pd.read_sql_query 读取数据
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(query, conn, params=params)
    
    if df.empty:
        return ""

    # 列名映射为中文，增强 Excel 可读性
    rename_map = {
        'aweme_id': '视频ID',
        'desc': '标题/描述',
        'create_time': '发布时间',
        'author_uid': '作者UID',
        'digg_count': '点赞数',
        'comment_count': '评论数',
        'share_count': '分享数',
        'collect_count': '收藏数',
        'tags': '标签',
        'search_keyword': '抓取关键词',
        'video_url': '详情链接',
        'nickname': '作者昵称',
        'follower_count': '作者粉丝数'
    }
    df = df.rename(columns=rename_map)
    
    # 按互动量（点赞数）降序排列
    if '点赞数' in df.columns:
        df = df.sort_values(by='点赞数', ascending=False)

    # 构造绝对路径
    filename = f"douyin_data_{keyword if keyword else 'all'}.xlsx"
    export_dir = os.path.dirname(DB_PATH)
    file_path = os.path.abspath(os.path.join(export_dir, filename))
    
    # 写入 Excel
    df.to_excel(file_path, index=False, engine='openpyxl')
    
    print(f"[*] Excel 导出完成: {file_path} (共 {len(df)} 条数据)")
    return file_path

# 执行初始化
init_db()
