import pandas as pd
import re
from datetime import datetime

class DataCleaner:
    @staticmethod
    def _parse_number(val) -> int:
        """将类似 1.2w, 250万, 3k 的字符串转化为整型"""
        if pd.isna(val) or val is None or str(val).strip() == '':
            return 0
        
        if isinstance(val, (int, float)):
            return int(val)
            
        val_str = str(val).lower().replace(' ', '')
        
        # 如果是纯数字
        if val_str.isdigit():
            return int(val_str)
            
        # 带单位的字符串处理
        multiplier = 1
        if 'w' in val_str:
            multiplier = 10000
            val_str = val_str.replace('w', '')
        elif '万' in val_str:
            multiplier = 10000
            val_str = val_str.replace('万', '')
        elif 'k' in val_str:
            multiplier = 1000
            val_str = val_str.replace('k', '')
            
        # 尝试将剩余部分提取数字并乘上乘数
        match = re.search(r'[\d\.]+', val_str)
        if match:
            return int(float(match.group()) * multiplier)
            
        return 0

    @staticmethod
    def _parse_timestamp(val) -> str:
        """解析时间截为标准时间字符串"""
        if pd.isna(val):
            return ""
        try:
            # 兼容毫秒级
            if int(val) > 10**10:
                val = int(val) / 1000
            return datetime.fromtimestamp(int(val)).strftime('%Y-%m-%d %H:%M:%S')
        except:
            return ""

    @staticmethod
    def clean_raw_data(raw_data_list: list) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        清洗爬取的原始 JSON 列表
        返回: (videos_df, authors_df)
        """
        if not raw_data_list:
            return pd.DataFrame(), pd.DataFrame()

        processed_videos = []
        processed_authors = []

        for payload in raw_data_list:
            if not isinstance(payload, dict):
                continue
            
            search_keyword = payload.get('_keyword', '')
            data_list = payload.get('data', [])
            if not isinstance(data_list, list):
                continue
                
            for entry in data_list:
                item = entry.get('aweme_info')
                if not item:
                    item = entry  # Fallback
                    
                # 数据准则1: 必需存在 aweme_id，否则作为脏数据剔除
                aweme_id = item.get('aweme_id')
                if not aweme_id:
                    continue

                # 1. 平铺抽取 Author 数据
                author_info = item.get('author', {})
                author_uid = author_info.get('uid', 'unknown')
                processed_authors.append({
                    'uid': author_uid,
                    'nickname': author_info.get('nickname', ''),
                    'follower_count': DataCleaner._parse_number(author_info.get('follower_count', 0))
                })

                # 2. 抽取并平铺 Statistics 数据
                stats = item.get('statistics', {})
                
                # 3. 解析 Tags / Text Extra
                tags = []
                text_extra = item.get('text_extra', [])
                if isinstance(text_extra, list):
                    for tag_obj in text_extra:
                        if 'hashtag_name' in tag_obj:
                            tags.append(tag_obj['hashtag_name'])
                        elif isinstance(tag_obj, dict) and 'name' in tag_obj:
                            # 兼容不同接口的结构
                            tags.append(tag_obj['name'])
                tags_str = ",".join(tags)

                # 4. 提取视频 URL（Scraper Agent 新增字段）
                # 优先级：share_url > aweme_url > 用 aweme_id 拼接标准链接
                video_url = (
                    item.get('share_url')
                    or item.get('aweme_url')
                    or f"https://www.douyin.com/video/{aweme_id}"
                )

                # 构建视频单行数据
                processed_videos.append({
                    'aweme_id': str(aweme_id),
                    'desc': item.get('desc', ''),
                    'create_time': DataCleaner._parse_timestamp(item.get('create_time')),
                    'author_uid': str(author_uid),
                    'digg_count': DataCleaner._parse_number(stats.get('digg_count')),
                    'comment_count': DataCleaner._parse_number(stats.get('comment_count')),
                    'share_count': DataCleaner._parse_number(stats.get('share_count')),
                    'collect_count': DataCleaner._parse_number(stats.get('collect_count')),
                    'play_count': DataCleaner._parse_number(stats.get('play_count')),
                    'tags': tags_str,
                    'search_keyword': search_keyword,
                    'video_url': str(video_url)
                })

        videos_df = pd.DataFrame(processed_videos)
        authors_df = pd.DataFrame(processed_authors)
        
        # 兜底空值处理（保证严格的无脏数据）
        if not videos_df.empty:
            num_cols = ['digg_count', 'comment_count', 'share_count', 'collect_count', 'play_count']
            videos_df[num_cols] = videos_df[num_cols].fillna(0).astype(int)
            # video_url 单独处理：用 aweme_id 兜底，不用空字符串
            if 'video_url' in videos_df.columns:
                mask = videos_df['video_url'].isna() | (videos_df['video_url'] == '')
                videos_df.loc[mask, 'video_url'] = videos_df.loc[mask, 'aweme_id'].apply(
                    lambda aid: f"https://www.douyin.com/video/{aid}"
                )
            videos_df.fillna('', inplace=True)
            
        if not authors_df.empty:
            authors_df['follower_count'] = authors_df['follower_count'].fillna(0).astype(int)
            authors_df.fillna('', inplace=True)

        return videos_df, authors_df

if __name__ == '__main__':
    import os
    import json
    from database import batch_insert_videos, batch_insert_authors, init_db
    
    init_db()
    
    raw_data_path = os.path.join(os.path.dirname(__file__), "raw_data.json")
    if os.path.exists(raw_data_path):
        with open(raw_data_path, "r", encoding="utf-8") as f:
            raw_data_list = json.load(f)
            
        videos_df, authors_df = DataCleaner.clean_raw_data(raw_data_list)
        print(f">>> 清洗完成，获得 {len(videos_df)} 条视频，{len(authors_df)} 条作者数据。")
        
        batch_insert_videos(videos_df)
        batch_insert_authors(authors_df)
        print(">>> 写入数据库完成。")
    else:
        print(f">>> {raw_data_path} 不存在。")
