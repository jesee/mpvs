import logging
import requests
import os
import re
import subprocess
import shutil
from urllib.parse import quote, urlparse
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple, Optional, Any

# --- 日志配置 ---
# 创建一个唯一的日志文件，避免被缓存
log_file = os.path.join(os.path.dirname(__file__), 'downloader.log')
# 每次启动时都清空日志
if os.path.exists(log_file):
    os.remove(log_file)
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- 配置 ---
BASE_URL = "https://www.dda5.com"
SEARCH_URL = f"{BASE_URL}/so.php"
PLAY_API_URL = f"{BASE_URL}/style/js/play.php"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': f"{BASE_URL}/",
    'X-Requested-With': 'XMLHttpRequest',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
}

# --- 核心功能 (已重构为库) ---

class DownloaderError(Exception):
    """下载器模块的自定义异常基类"""
    pass

class NetworkError(DownloaderError):
    """网络请求相关的错误"""
    pass

class ParseError(DownloaderError):
    """HTML或JSON解析相关的错误"""
    pass

def search_songs(keyword: str, page: int = 1) -> Tuple[List[Dict[str, str]], int, int]:
    """
    根据关键词和页码搜索歌曲。
    :return: (歌曲列表, 总页数, 总歌曲数)
    :raises: NetworkError, ParseError
    """
    logging.info(f"开始搜索，关键词: '{keyword}', 页码: {page}")
    songs = []
    total_pages = 0
    total_songs = 0
    try:
        encoded_keyword = quote(keyword)
        url = f"{SEARCH_URL}?wd={encoded_keyword}&page={page}"
        logging.info(f"请求URL: {url}")
        
        response = requests.get(url, headers=HEADERS, timeout=15)
        logging.info(f"收到响应，状态码: {response.status_code}")
        response.raise_for_status()
        
        logging.info("开始使用lxml解析HTML...")
        soup = BeautifulSoup(response.text, 'lxml')
        logging.info("HTML解析完成。")
        
        song_list_items = soup.select('div.play_list ul li')
        logging.info(f"找到 {len(song_list_items)} 个歌曲项目。")
        for item in song_list_items:
            title_element = item.select_one('div.name a.url')
            if title_element:
                title = title_element.get_text(strip=True)
                href = title_element.get('href')
                match = re.search(r'/mp3/([^.]+)\.html', href)
                if match:
                    song_id = match.group(1)
                    songs.append({'title': title, 'id': song_id})

        page_info_div = soup.select_one("div.page")
        if page_info_div:
            page_links = page_info_div.find_all('a', class_='btn')
            for link in page_links:
                text = link.get_text(strip=True)
                if '共' in text and '页' in text:
                    pages_match = re.search(r'共(\d+)页', text)
                    if pages_match: total_pages = int(pages_match.group(1))
                if '共' in text and '首' in text:
                    songs_match = re.search(r'共(\d+)首', text)
                    if songs_match: total_songs = int(songs_match.group(1))
        
        if total_songs == 0:
            pagedata_div = soup.select_one("div.pagedata span")
            if pagedata_div: total_songs = int(pagedata_div.get_text(strip=True))
        
        logging.info(f"搜索完成。找到歌曲: {len(songs)}, 总页数: {total_pages}, 总歌曲: {total_songs}")

    except requests.exceptions.RequestException as e:
        logging.error(f"网络请求期间发生错误: {e}")
        raise NetworkError(f"网络请求错误: {e}") from e
    except Exception as e:
        logging.error(f"处理期间发生未知错误: {e}", exc_info=True)
        raise ParseError(f"解析时发生错误: {e}") from e
        
    return songs, total_pages, total_songs

def get_song_info(song_id: str) -> Optional[Dict[str, Any]]:
    """
    获取歌曲的完整信息 (URL, 歌词等)。
    :raises: NetworkError, ParseError
    """
    try:
        data = {'id': song_id, 'type': 'dance'}
        response = requests.post(PLAY_API_URL, headers=HEADERS, data=data, timeout=10)
        response.raise_for_status()
        json_data = response.json()
        
        if json_data.get('msg') == 1:
            return json_data
        else:
            raise ParseError(f"API未返回成功状态。ID: {song_id}, 响应: {json_data}")
            
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"获取歌曲信息时网络错误: {e}") from e
    except ValueError as e:
        raise ParseError(f"无法解析来自API的响应: {response.text}") from e

def download_song_and_lrc(song_info: Dict[str, Any], download_dir: str) -> str:
    """
    下载并智能处理歌曲和歌词。
    :return: 最终保存的音频文件路径。
    :raises: DownloaderError, NetworkError, IOError
    """
    if not song_info or not song_info.get('url'):
        raise DownloaderError("歌曲信息无效或缺少下载链接。")

    title = song_info.get('title', '未知歌曲')
    safe_title = re.sub(r'[\\/*?:\"<>|]', "_", title)
    url = song_info['url']
    
    path = urlparse(url).path
    original_ext = os.path.splitext(path)[1].lower() or ".tmp"
    final_ext = '.mp3' if original_ext == '.mp3' else '.aac'
    final_audio_path = os.path.join(download_dir, f"{safe_title}{final_ext}")
    
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # --- 音频处理 ---
    if os.path.exists(final_audio_path):
        # 文件已存在，直接返回路径
        return final_audio_path

    temp_download_path = os.path.join(download_dir, f"{safe_title}.downloading")
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(temp_download_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        if final_ext == '.mp3':
            os.rename(temp_download_path, final_audio_path)
        else:
            ffmpeg_path = shutil.which('ffmpeg')
            if ffmpeg_path:
                command = [ffmpeg_path, '-i', temp_download_path, '-c:a', 'copy', final_audio_path, '-y', '-hide_banner', '-loglevel', 'error']
                result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='ignore')
                if result.returncode == 0:
                    os.remove(temp_download_path)
                else:
                    os.rename(temp_download_path, os.path.join(download_dir, f"{safe_title}{original_ext}"))
                    raise DownloaderError(f"ffmpeg提取失败: {result.stderr}")
            else:
                final_original_path = os.path.join(download_dir, f"{safe_title}{original_ext}")
                os.rename(temp_download_path, final_original_path)
                raise DownloaderError(f"未找到ffmpeg，文件已保存为原始格式: {os.path.basename(final_original_path)}")

    except requests.exceptions.RequestException as e:
        if os.path.exists(temp_download_path): os.remove(temp_download_path)
        raise NetworkError(f"下载 '{safe_title}' 时出错: {e}") from e
    except Exception as e:
        if os.path.exists(temp_download_path): os.remove(temp_download_path)
        raise DownloaderError(f"处理 '{safe_title}' 时发生未知错误: {e}") from e

    # --- 保存歌词 ---
    lrc_content = song_info.get('lrc')
    if lrc_content:
        lrc_path = os.path.join(download_dir, f"{safe_title}.lrc")
        if not os.path.exists(lrc_path):
            try:
                with open(lrc_path, 'w', encoding='utf-8') as f:
                    f.write(lrc_content)
            except IOError as e:
                # 不把这个当成致命错误，只返回警告
                # warnings.warn(f"保存歌词时出错: {e}")
                pass # 在TUI应用中，暂时忽略歌词保存失败

    return final_audio_path
