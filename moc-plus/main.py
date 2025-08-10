import os
import logging
import threading
from functools import partial
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import var
from textual.screen import Screen
from textual.widgets import (Footer, Header, Input, ListItem, ListView,
                             Static)

import downloader
from player import Player
from playlist import Playlist, Song

# --- 日志配置 ---
log_file = os.path.join(os.path.dirname(__file__), 'app.log')
if os.path.exists(log_file):
    os.remove(log_file)
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- 搜索屏幕 ---

import downloader
from player import Player
from playlist import Playlist, Song


# --- 命令屏幕 ---

class CommandScreen(Screen):
    """一个通用的屏幕，用于接收用户输入的命令参数（如文件路径）。"""
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def __init__(self, prompt: str, initial_value: str, callback):
        super().__init__()
        self.prompt = prompt
        self.initial_value = initial_value
        self.callback = callback

    def compose(self) -> ComposeResult:
        yield Static(self.prompt, id="command_prompt")
        yield Input(self.initial_value, id="command_input")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.app.pop_screen()
        # 调用从主应用传递过来的回调函数，并传入最终的输入值
        if self.callback:
            self.callback(event.value)


# --- 搜索屏幕 ---

class SearchScreen(Screen):
    """用于搜索和显示结果的屏幕。"""
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("n", "next_page", "Next Page"),
        ("p", "previous_page", "Prev Page"),
        ("a", "download_all", "Download All"),
    ]


# --- 主应用 ---

class MocPlusApp(App):
    """A Textual music player application."""
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "push_screen('search')", "Search"),
        ("p", "toggle_pause", "Play/Pause"),
        ("r", "import_from_folders", "Import from Folders"),
        ("ctrl+s", "show_save_screen", "Save Playlist"),
        ("ctrl+o", "show_load_screen", "Load Playlist"),
    ]
    SCREENS = {
        "search": SearchScreen,
        "command": CommandScreen,
    }
    CSS_PATH = "tui.css"
    status_text = var("STATUS: Welcome to MOC-Plus!")

    def __init__(self):
        super().__init__()
        self.player: Optional[Player] = None
        self.playlist = Playlist()
        self.config_dir = os.path.expanduser("~/.mpvs")
        self.playlist_path = os.path.join(self.config_dir, "default.m3u")
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        self.music_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '斗破苍穹'))
        self.downloads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'downloads'))
        
    def compose(self) -> ComposeResult:
        yield Header(name="MOC-Plus Terminal Player")
        yield Static(id="status_bar")
        with VerticalScroll(id="playlist_view"):
            yield ListView(id="playlist_listview")
        yield Footer()

    def on_mount(self) -> None:
        self.player = Player()
        self.action_load_playlist(self.playlist_path)

    def on_search_finished(self, result) -> None:
        if not isinstance(self.screen, SearchScreen): return
        search_screen = self.screen
        list_view = search_screen.query_one("#search_results_list", ListView)
        input_widget = search_screen.query_one(Input)
        input_widget.disabled = False
        if isinstance(result, Exception):
            self.sub_title = f"Search failed: {result}"
            list_view.append(ListItem(Static(f"Error: {result}")))
        else:
            search_results, total_pages, total_songs = result
            search_screen.total_pages = total_pages
            self.sub_title = f"Found {total_songs} songs | Page {search_screen.current_page}/{total_pages}"
            if not search_results:
                list_view.append(ListItem(Static("No results found.")))
            else:
                for song in search_results:
                    list_item = ListItem(Static(song['title']))
                    list_item.song_data = song
                    list_view.append(list_item)
        input_widget.focus()

    def on_download_finished(self, result) -> None:
        downloaded_count, errors = result
        new_songs_playlist = Playlist()
        new_songs_playlist.scan_directory(self.downloads_dir)
        added_count = 0
        for song in new_songs_playlist.songs:
            if not any(p_song.path == song.path for p_song in self.playlist.songs):
                self.playlist.songs.append(song)
                added_count += 1
        if errors:
            self.sub_title = f"Completed. Downloaded {downloaded_count}. {len(errors)} failed."
        else:
            self.sub_title = f"Successfully downloaded {downloaded_count} song(s)."
        if isinstance(self.screen, SearchScreen):
            self.pop_screen()
        self._update_playlist_view()
        if added_count > 0:
            self.status_text = f"Added {added_count} new song(s). Press Ctrl+S to save."
        else:
            self.status_text = "Download complete. No new songs added to playlist."

    def _update_playlist_view(self):
        """用当前 self.playlist 的内容刷新UI的通用方法。"""
        list_view = self.query_one("#playlist_listview", ListView)
        list_view.clear()
        if not self.playlist.songs:
            list_view.append(ListItem(Static("Playlist is empty. Press 'r' to import from folders.")))
        else:
            for song in self.playlist.songs:
                list_item = ListItem(Static(song.title))
                list_item.song_data = song 
                list_view.append(list_item)

    def action_show_load_screen(self):
        """显示加载播放列表的命令屏幕。"""
        self.push_screen(
            CommandScreen(
                prompt="Load playlist from:",
                initial_value=self.playlist_path,
                callback=self.action_load_playlist
            )
        )

    def action_show_save_screen(self):
        """显示保存播放列表的命令屏幕。"""
        self.push_screen(
            CommandScreen(
                prompt="Save playlist as:",
                initial_value=self.playlist_path,
                callback=self.action_save_playlist
            )
        )

    def action_load_playlist(self, path: str):
        """加载指定路径的播放列表并刷新UI。"""
        self.playlist_path = path
        self.playlist.load_m3u(self.playlist_path)
        self._update_playlist_view()
        self.status_text = f"Loaded playlist from {self.playlist_path}"

    def action_save_playlist(self, path: str):
        """保存当前播放列表到指定路径。"""
        self.playlist_path = path
        self.playlist.save_m3u(self.playlist_path)
        self.status_text = f"Playlist saved to {self.playlist_path}"

    def action_import_from_folders(self) -> None:
        """从本地文件夹扫描并导入歌曲（会覆盖当前列表）。"""
        self.playlist.scan_directory(self.music_dir)
        self.playlist.scan_directory(self.downloads_dir)
        self._update_playlist_view()
        self.status_text = "Imported songs from local folders. Press Ctrl+S to save."

    def on_key(self, event: "events.Key") -> None:
        """捕获所有未被处理的按键事件。"""
        if event.key == "p":
            self.action_toggle_pause()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """当用户在任何ListView上按回车时调用。"""
        if event.list_view.id == "playlist_listview":
            if hasattr(event.item, 'song_data'):
                song_to_play: Song = event.item.song_data
                if self.player: 
                    self.player.play(song_to_play.path)
                    self.status_text = f"Playing: {song_to_play.title}"

    def watch_status_text(self, new_text: str) -> None:
        self.query_one("#status_bar", Static).update(new_text)

def main():
    app = MocPlusApp()
    app.run()

if __name__ == "__main__":
    main()
