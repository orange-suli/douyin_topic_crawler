import pandas as pd
from cleaner import DataCleaner
from database import init_db, batch_insert_videos, batch_insert_authors, get_db_connection

def test_pipeline():
    print(">>> 正在初始化数据库（含热迁移 video_url 列）...")
    init_db()

    # ------------------------------------------------------------------ #
    # 构造 mock 原始数据，覆盖 video_url 的三条获取路径：                 #
    #  条目 1：接口返回了 share_url → 直接使用                            #
    #  条目 2：接口返回了 aweme_url 但无 share_url → 使用 aweme_url       #
    #  条目 3：两者均无 → 用 aweme_id 拼接标准链接兜底                    #
    # ------------------------------------------------------------------ #
    mock_raw_data = [
        {
            "_keyword": "test_keyword",
            "data": [
                {
                    "aweme_info": {
                        "aweme_id": "1234567890",
                        "desc": "测试视频1: 含 share_url 字段",
                        "create_time": 1610000000,
                        "share_url": "https://v.douyin.com/abc123/",   # 路径1
                        "author": {
                            "uid": "u1",
                            "nickname": "博主A",
                            "follower_count": "1.2w"
                        },
                        "statistics": {
                            "digg_count": "20万",
                            "comment_count": 500,
                            "share_count": "3.5k",
                            "collect_count": 0,
                        },
                        "text_extra": [
                            {"hashtag_name": "测试标签1"},
                            {"hashtag_name": "AI"}
                        ]
                    }
                },
                {
                    "aweme_info": {
                        "aweme_id": "0987654321",
                        "desc": "测试视频2: 含 aweme_url，无 share_url",
                        "create_time": 1620000000,
                        "aweme_url": "https://www.douyin.com/video/0987654321",  # 路径2
                        "author": {
                            "uid": "u2",
                            "nickname": "博主B",
                        },
                        "statistics": {
                            "digg_count": None,
                            "comment_count": "100",
                        },
                        "text_extra": [
                            {"name": "不同Tag结构"}
                        ]
                    }
                },
                {
                    "aweme_info": {
                        "aweme_id": "1111111111",
                        "desc": "测试视频3: 无 share_url 也无 aweme_url，用 aweme_id 兜底",
                        "create_time": 1630000000,
                        # 无 share_url / aweme_url → 兜底路径3
                        "author": {
                            "uid": "u3",
                            "nickname": "博主C",
                            "follower_count": "500"
                        },
                        "statistics": {
                            "digg_count": 100,
                            "comment_count": 10,
                            "share_count": 5,
                            "collect_count": 2,
                        },
                        "text_extra": []
                    }
                },
                {
                    # 无 aweme_id —— 脏数据，应被剔除
                    "aweme_info": {
                        "desc": "极其异常的脏数据",
                        "author": {"uid": "u_dirty"}
                    }
                }
            ]
        }
    ]

    print(">>> 开始清洗模拟数据...")
    videos_df, authors_df = DataCleaner.clean_raw_data(mock_raw_data)

    print("\n--- 清洗后的视频数据 DataFrame ---")
    print(videos_df[['aweme_id', 'desc', 'video_url']].to_string(index=False))

    print("\n--- 清洗后的作者数据 DataFrame ---")
    print(authors_df)

    # ---- 断言：video_url 必须存在且有值 ----
    assert 'video_url' in videos_df.columns, "[FAIL] video_url \u5217\u4e0d\u5b58\u5728\uff01"
    assert len(videos_df) == 3, f"[FAIL] \u5e94\u67093\u6761\u6709\u6548\u8bb0\u5f55\uff08\u810f\u6570\u636e\u5df2\u8fc7\u6ee4\uff09\uff0c\u5b9e\u9645 {len(videos_df)} \u6761"
    
    row1 = videos_df[videos_df['aweme_id'] == '1234567890'].iloc[0]
    assert row1['video_url'] == "https://v.douyin.com/abc123/", \
        f"[FAIL] \u6761\u76ee1 share_url \u672a\u6b63\u786e\u8bfb\u53d6: {row1['video_url']}"

    row2 = videos_df[videos_df['aweme_id'] == '0987654321'].iloc[0]
    assert row2['video_url'] == "https://www.douyin.com/video/0987654321", \
        f"[FAIL] \u6761\u76ee2 aweme_url \u672a\u6b63\u786e\u8bfb\u53d6: {row2['video_url']}"

    row3 = videos_df[videos_df['aweme_id'] == '1111111111'].iloc[0]
    assert row3['video_url'] == "https://www.douyin.com/video/1111111111", \
        f"[FAIL] \u6761\u76ee3 aweme_id \u515c\u5e95\u94fe\u63a5\u4e0d\u6b63\u786e: {row3['video_url']}"

    print("\n[OK] video_url \u6240\u6709\u8def\u5f84\u65ad\u8a00\u901a\u8fc7\uff01")

    print("\n>>> 开始写入数据库...")
    batch_insert_videos(videos_df)
    batch_insert_authors(authors_df)

    print("\n>>> 从数据库中查询验证 video_url 是否落盘...")
    with get_db_connection() as conn:
        df_vid = pd.read_sql("SELECT aweme_id, desc, video_url FROM videos WHERE aweme_id IN ('1234567890','0987654321','1111111111')", conn)
        print("\n[DB] Videos (关键字段):")
        print(df_vid.to_string(index=False))

    # 再次断言数据库中的值
    for _, row in df_vid.iterrows():
        assert row['video_url'] and row['video_url'].startswith("http"), \
            f"[FAIL] \u6570\u636e\u5e93\u4e2d aweme_id={row['aweme_id']} \u7684 video_url \u4e3a\u7a7a\u6216\u5f02\u5e38: {row['video_url']}"
    
    print("[OK] \u6570\u636e\u5e93\u843d\u76d8\u9a8c\u8bc1\u901a\u8fc7! video_url \u5b57\u6bb5\u6210\u529f\u5165\u5e93\u3002")
    print("\n>>> \u6d4b\u8bd5\u5168\u90e8\u901a\u8fc7\uff01")

if __name__ == "__main__":
    test_pipeline()
