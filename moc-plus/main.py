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

class SearchScreen(Screen):
    """用于搜索和显示结果的屏幕。"""
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("n", "next_page", "Next Page"),
        ("p", "previous_page", "Prev Page"),
        ("a", "download_all", "Download All"),
    ]

    def __init__(self):
        super().__init__()
        self.current_page = 1
        self.total_pages = 1
        self.current_query = ""

    def compose(self) -> ComposeResult:
        yield Header(name="Search Online Music")
        yield Input(placeholder="Enter song or artist name...")
        with VerticalScroll(id="search_results_view"):
            yield ListView(id="search_results_list")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def start_search(self, query: str, page: int = 1) -> None:
        """启动后台搜索任务的通用方法。"""
        self.query_one("#search_results_list", ListView).clear()
        self.query_one(Input).disabled = True
        self.app.sub_title = f"Searching for '{query}' on page {page}..."
        # 使用 threading + call_from_thread
        thread = threading.Thread(target=self.search_worker, args=[query, page])
        thread.start()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.current_query = event.value
        self.current_page = 1
        self.total_pages = 1
        self.start_search(self.current_query, self.current_page)

    def search_worker(self, query: str, page: int):
        """这个方法在后台线程中运行。"""
        try:
            result = downloader.search_songs(query, page)
        except Exception as e:
            result = e
        self.app.call_from_thread(self.app.on_search_finished, result)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not hasattr(event.item, "song_data"): return
        song_data = event.item.song_data
        self.app.sub_title = f"Downloading '{song_data['title']}'..."
        thread = threading.Thread(target=self.download_worker, args=[[song_data]])
        thread.start()

    def download_worker(self, songs_to_download: list[dict]):
        """在后台线程中运行下载流程。"""
        downloaded_count = 0
        errors = []
        download_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "downloads"))
        for song_data in songs_to_download:
            try:
                song_info = downloader.get_song_info(song_data["id"])
                downloader.download_song_and_lrc(song_info, download_dir)
                downloaded_count += 1
            except Exception:
                errors.append(song_data["title"])
        result = (downloaded_count, errors)
        self.app.call_from_thread(self.app.on_download_finished, result)

    def action_next_page(self) -> None:
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.start_search(self.current_query, self.current_page)

    def action_previous_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self.start_search(self.current_query, self.current_page)

    def action_download_all(self) -> None:
        list_view = self.query_one("#search_results_list", ListView)
        songs_on_page = [child.song_data for child in list_view.children if hasattr(child, "song_data")]
        if not songs_on_page: return
        self.app.sub_title = f"Queueing {len(songs_on_page)} songs for download..."
        thread = threading.Thread(target=self.download_worker, args=[songs_on_page])
        thread.start()


# --- 主应用 ---

class MocPlusApp(App):
    """A Textual music player application."""
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "push_screen('search')", "Search"),
        # 'p' is handled by on_key, 'enter' is handled by on_list_view_selected
        ("r", "refresh_playlist", "Refresh Playlist"),
    ]
    SCREENS = {"search": SearchScreen}
    CSS_PATH = "tui.css"
    status_text = var("STATUS: Welcome to MOC-Plus!")

    def __init__(self):
        super().__init__()
        self.player: Optional[Player] = None
        self.playlist = Playlist()
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
        self.call_next(self.action_refresh_playlist)

    def on_search_finished(self, result) -> None:
        """由 search_worker 通过 call_from_thread 调用。"""
        logging.info(f"--- on_search_finished TRIGGERED ---")
        if not isinstance(self.screen, SearchScreen):
            logging.warning("Search finished, but SearchScreen is not active.")
            return
        
        search_screen = self.screen
        list_view = search_screen.query_one("#search_results_list", ListView)
        input_widget = search_screen.query_one(Input)
        input_widget.disabled = False
        logging.info(f"Worker result type: {type(result)}")

        if isinstance(result, Exception):
            self.sub_title = f"Search failed: {result}"
            logging.error(f"Search worker returned an exception: {result}")
            list_view.append(ListItem(Static(f"Error: {result}")))
        else:
            search_results, total_pages, total_songs = result
            search_screen.total_pages = total_pages
            self.sub_title = f"Found {total_songs} songs | Page {search_screen.current_page}/{total_pages}"
            logging.info(f"Search successful. Found {len(search_results)} songs.")
            if not search_results:
                list_view.append(ListItem(Static("No results found.")))
            else:
                for song in search_results:
                    list_item = ListItem(Static(song['title']))
                    list_item.song_data = song
                    list_view.append(list_item)
        input_widget.focus()

    def on_download_finished(self, result) -> None:
        """由 download_worker 通过 call_from_thread 调用。"""
        logging.info(f"--- on_download_finished TRIGGERED ---")
        downloaded_count, errors = result
        if errors:
            self.sub_title = f"Completed. Downloaded {downloaded_count} songs. {len(errors)} failed."
        else:
            self.sub_title = f"Successfully downloaded {downloaded_count} song(s)."
        if isinstance(self.screen, SearchScreen):
            self.pop_screen()
        self.call_next(self.action_refresh_playlist)

    async def action_refresh_playlist(self) -> None:
        self.playlist.scan_directory(self.music_dir)
        self.playlist.scan_directory(self.downloads_dir)
        list_view = self.query_one("#playlist_listview", ListView)
        list_view.clear()
        if not self.playlist.songs:
            list_view.append(ListItem(Static("No songs found. Press 's' to search.")))
        else:
            for song in self.playlist.songs:
                list_item = ListItem(Static(song.title))
                list_item.song_data = song 
                list_view.append(list_item)
        self.status_text = "Playlist refreshed. Select a song and press Enter."

    def on_key(self, event: "events.Key") -> None:
        """捕获所有未被处理的按键事件。"""
        if event.key == "p":
            self.action_toggle_pause()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """当用户在任何ListView上按回车时调用。"""
        # 通过检查ListView的ID来区分是在主屏幕还是搜索屏幕
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
