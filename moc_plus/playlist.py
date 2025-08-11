import os
from dataclasses import dataclass, field

SUPPORTED_EXTENSIONS = ['.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a']

@dataclass
class Song:
    """一个简单的数据类，用于存储歌曲信息。"""
    title: str
    path: str

@dataclass
class Playlist:
    """管理歌曲列表和当前选择。"""
    songs: list[Song] = field(default_factory=list)
    current_selection_index: int = 0

    def __post_init__(self):
        """初始化后加载默认播放列表。"""
        default_playlist_path = os.path.expanduser("~/.mpvs/default.m3u")
        config_dir = os.path.dirname(default_playlist_path)
        
        os.makedirs(config_dir, exist_ok=True)

        if not os.path.exists(default_playlist_path):
            # 创建一个有效的、空的 m3u 文件
            with open(default_playlist_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
        
        self.load_m3u(default_playlist_path)


    def get_current_song(self) -> Song | None:
        """获取当前选中的歌曲。"""
        if not self.songs:
            return None
        return self.songs[self.current_selection_index]

    def select_next(self):
        """移动选择到下一首歌曲。"""
        if not self.songs:
            return
        self.current_selection_index = (self.current_selection_index + 1) % len(self.songs)

    def select_previous(self):
        """移动选择到上一首歌曲。"""
        if not self.songs:
            return
        self.current_selection_index = (self.current_selection_index - 1 + len(self.songs)) % len(self.songs)

    def save_m3u(self, filepath: str):
        """将当前播放列表保存到 .m3u 文件。"""
        dir_path = os.path.dirname(filepath)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n')
            for song in self.songs:
                f.write(f'#EXTINF:-1,{song.title}\n')
                f.write(f'{song.path}\n')

    def load_m3u(self, filepath: str, append: bool = False):
        """
        从 .m3u 文件加载播放列表。
        
        :param filepath: .m3u 文件的路径。
        :param append: 如果为 True，则追加到现有列表，否则覆盖。
        """
        if not append:
            self.songs.clear()
            self.current_selection_index = 0
        
        # 如果文件不存在，load_m3u 应该静默返回，而不是创建它。
        # 创建文件的责任应该在应用逻辑中，而不是在通用的加载方法中。
        if not os.path.exists(filepath):
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            title = ""
            for line in f:
                line = line.strip()
                if not line or line.startswith('#EXTM3U'):
                    continue
                if line.startswith('#EXTINF:'):
                    title = line.split(',', 1)[-1]
                elif not line.startswith('#'):
                    path = line
                    if os.path.exists(path):
                        if not title:
                            title = os.path.splitext(os.path.basename(path))[0]
                        if not any(song.path == path for song in self.songs):
                            self.songs.append(Song(title=title, path=path))
                    title = ""

    def delete_song(self, index: int):
        """按索引删除一首歌曲。"""
        if 0 <= index < len(self.songs):
            del self.songs[index]

    def clear(self):
        """清空整个播放列表。"""
        self.songs.clear()
        self.current_selection_index = 0

if __name__ == '__main__':
    # --- 测试 Playlist 模块 ---
    playlist = Playlist()
    
    print("Playlist object created.")
    print(f"Initial songs: {playlist.songs}")

    # 测试加载/保存 m3u 文件
    test_m3u_path = os.path.expanduser("~/.mpvs/test_playlist.m3u")
    print(f"Testing M3U save/load with: {test_m3u_path}")
    
    # 添加一些示例歌曲
    playlist.songs.append(Song(title="Test Song 1", path="/tmp/song1.mp3"))
    playlist.songs.append(Song(title="Test Song 2", path="/tmp/song2.flac"))
    
    # 保存
    playlist.save_m3u(test_m3u_path)
    print(f"Saved {len(playlist.songs)} songs.")

    # 清空并重新加载
    playlist.clear()
    print("Playlist cleared.")
    playlist.load_m3u(test_m3u_path)
    print(f"Loaded {len(playlist.songs)} songs from M3U.")

    if playlist.songs:
        print(f"First song: {playlist.songs[0].title}")
    
    # 清理测试文件
    # os.remove(test_m3u_path)
    # print("Cleaned up test file.")