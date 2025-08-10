import requests
import os
import re
import subprocess
import shutil
from urllib.parse import quote, urlparse

from bs4 import BeautifulSoup

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

# --- 核心功能 ---

def search_songs(keyword, page=1):
    """根据关键词和页码搜索歌曲"""
    songs = []
    total_pages = 0
    total_songs = 0
    try:
        encoded_keyword = quote(keyword)
        url = f"{SEARCH_URL}?wd={encoded_keyword}&page={page}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        song_list_items = soup.select('div.play_list ul li')
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
                    if pages_match:
                        total_pages = int(pages_match.group(1))
                if '共' in text and '首' in text:
                    songs_match = re.search(r'共(\d+)首', text)
                    if songs_match:
                        total_songs = int(songs_match.group(1))
        
        if total_songs == 0:
            pagedata_div = soup.select_one("div.pagedata span")
            if pagedata_div:
                total_songs = int(pagedata_div.get_text(strip=True))

    except requests.exceptions.RequestException as e:
        print(f"网络请求错误: {e}")
    except Exception as e:
        print(f"解析时发生错误: {e}")
        
    return songs, total_pages, total_songs

def get_song_info(song_id):
    """获取歌曲的完整信息 (URL, 歌词等)"""
    try:
        data = {'id': song_id, 'type': 'dance'}
        response = requests.post(PLAY_API_URL, headers=HEADERS, data=data, timeout=10)
        response.raise_for_status()
        json_data = response.json()
        
        if json_data.get('msg') == 1:
            return json_data
        else:
            print(f"错误: API未返回成功状态。ID: {song_id}, 完整响应: {json_data}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"获取歌曲信息时网络错误: {e}")
    except ValueError:
        print(f"错误: 无法解析来自API的响应: {response.text}")
    return None

def download_song_and_lrc(song_info, download_dir):
    """下载并智能处理歌曲（MP3直接保存，其他格式无损提取AAC流），同时保存歌词"""
    if not song_info or not song_info.get('url'):
        print("歌曲信息无效或缺少下载链接，跳过。")
        return

    title = song_info.get('title', '未知歌曲')
    safe_title = re.sub(r'[\\/*?:\"<>|]', "_", title)
    url = song_info['url']
    
    # 从URL解析原始文件名和扩展名
    path = urlparse(url).path
    original_ext = os.path.splitext(path)[1].lower()
    if not original_ext: original_ext = ".tmp"

    # 决定最终的文件扩展名
    final_ext = '.mp3' if original_ext == '.mp3' else '.aac'
    final_audio_path = os.path.join(download_dir, f"{safe_title}{final_ext}")
    
    # --- 音频处理 ---
    if os.path.exists(final_audio_path):
        print(f"音频文件 '{os.path.basename(final_audio_path)}' 已存在，跳过。")
    else:
        temp_download_path = os.path.join(download_dir, f"{safe_title}.downloading")
        try:
            print(f"开始下载: {safe_title} (原始格式: {original_ext or '未知'})")
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(temp_download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"下载完成。")

            # --- 智能处理 ---
            if final_ext == '.mp3':
                print("文件是MP3格式，直接保存。")
                os.rename(temp_download_path, final_audio_path)
            else: # 处理AAC和其他格式
                ffmpeg_path = shutil.which('ffmpeg')
                if ffmpeg_path:
                    print(f"提取AAC音频流至 '{os.path.basename(final_audio_path)}'...")
                    # 使用 -c:a copy 进行无损、快速的重新封装
                    command = [ffmpeg_path, '-i', temp_download_path, '-c:a', 'copy', final_audio_path, '-y']
                    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='ignore')
                    
                    if result.returncode == 0:
                        print(f"成功提取音频流。")
                        os.remove(temp_download_path)
                    else:
                        print(f"ffmpeg提取失败: {result.stderr}")
                        print("保留原始文件。")
                        os.rename(temp_download_path, os.path.join(download_dir, f"{safe_title}{original_ext}"))
                else:
                    final_original_path = os.path.join(download_dir, f"{safe_title}{original_ext}")
                    print(f"\n警告: 未找到ffmpeg。文件已保存为原始格式: {os.path.basename(final_original_path)}")
                    os.rename(temp_download_path, final_original_path)

        except requests.exceptions.RequestException as e:
            print(f"\n下载 '{safe_title}' 时出错: {e}")
            if os.path.exists(temp_download_path):
                os.remove(temp_download_path)

    # --- 保存歌词 ---
    lrc_content = song_info.get('lrc')
    if lrc_content:
        lrc_path = os.path.join(download_dir, f"{safe_title}.lrc")
        if os.path.exists(lrc_path):
            print(f"歌词 '{os.path.basename(lrc_path)}' 已存在，跳过。")
        else:
            try:
                with open(lrc_path, 'w', encoding='utf-8') as f:
                    f.write(lrc_content)
                print(f"歌词保存完成。")
            except IOError as e:
                print(f"保存歌词时出错: {e}")

# --- 交互式主程序 ---
def main():
    """主交互函数"""
    print("--- DDA5 音乐下载器 (最终智能版) ---")
    if not shutil.which('ffmpeg'):
        print("警告: 未在系统中找到 'ffmpeg'。")
        print("非MP3格式的音频将以原始格式保存，可能无法直接播放。")
        print("为了获得最佳体验，建议安装ffmpeg (例如: sudo apt-get install ffmpeg)")
    
    download_dir = input("请输入歌曲要保存的文件夹路径 (默认为 'downloads'): ").strip()
    if not download_dir:
        download_dir = 'downloads'
    
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        print(f"已创建文件夹: {download_dir}")

    while True:
        keyword = input("\n输入歌曲或歌手名进行搜索 (输入 'q' 退出): ").strip()
        if not keyword:
            continue
        if keyword.lower() == 'q':
            break

        page = 1
        total_pages = 1
        while True:
            print(f"\n正在搜索 '{keyword}' - 第 {page} 页...")
            songs, current_total_pages, total_songs = search_songs(keyword, page)
            
            if current_total_pages > 0:
                total_pages = current_total_pages

            if not songs:
                print("未找到相关歌曲，请尝试其他关键词。")
                break

            print(f"\n--- 共 {total_songs} 首歌曲，{total_pages} 页 ---")
            for i, song in enumerate(songs):
                print(f"{i + 1:2d}: {song['title']}")
            print("------------------")

            prompt = (
                "请选择操作:\n"
                " - 输入歌曲序号 (如 1) 以下载单曲\n"
                " - 输入 'a' 下载本页全部歌曲\n"
                " - 输入 'n' 进入下一页\n"
                " - 输入 'p' 返回上一页\n"
                " - 输入 's' 重新搜索\n"
                " - 输入 'q' 退出程序\n"
                "> "
            )
            choice = input(prompt).strip().lower()

            if choice == 'q':
                print("感谢使用，再见！")
                return
            elif choice == 's':
                break
            elif choice == 'n':
                if page < total_pages:
                    page += 1
                else:
                    print("已经是最后一页了。")
            elif choice == 'p':
                if page > 1:
                    page -= 1
                else:
                    print("已经是第一页了。")
            elif choice == 'a':
                print(f"\n准备下载本页全部 {len(songs)} 首歌曲...")
                for song in songs:
                    song_info = get_song_info(song['id'])
                    if song_info:
                        download_song_and_lrc(song_info, download_dir)
                print("\n本页全部任务已处理完毕。")
            elif choice.isdigit() and 1 <= int(choice) <= len(songs):
                selected_song = songs[int(choice) - 1]
                print(f"\n准备下载: {selected_song['title']}")
                song_info = get_song_info(selected_song['id'])
                if song_info:
                    download_song_and_lrc(song_info, download_dir)
            else:
                print("无效输入，请重试。")


if __name__ == '__main__':
    main()