import os
import re
import threading
from functools import partial
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import var
from textual.screen import Screen
from textual.widgets import (
    Footer,
    Header,
    Input,
    ListItem,
    ListView,
    Static,
)

import downloader
from player import Player
from playlist import Playlist, Song

# --- 歌词屏幕 ---
class LyricsScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back"), ("l", "app.pop_screen", "Back")]
    def __init__(self, player: Player, current_song: Optional[Song] = None):
        super().__init__()
        self.player = player
        self.current_song = current_song
        self.lyrics: list[tuple[float, str]] = []
        self.current_line_index = -1
        self.update_timer = self.set_interval(1 / 10, self.update_highlight, pause=True)
    def _parse_lrc(self, lrc_content: str) -> list[tuple[float, str]]:
        parsed_lyrics = []
        for line in lrc_content.splitlines():
            match = re.match(r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)', line)
            if match:
                minutes, seconds, ms, text = match.groups()
                # 确保毫秒总是3位数（例如 "54" -> "540"），以进行正确的计算
                ms_normalized = ms.ljust(3, '0')
                time_in_seconds = int(minutes) * 60 + int(seconds) + int(ms_normalized) / 1000.0
                parsed_lyrics.append((time_in_seconds, text.strip()))
        return sorted(parsed_lyrics)
    def update_highlight(self) -> None:
        if not self.lyrics: return
        current_time = self.player.get_current_time()
        new_line_index = -1
        for i, (time, text) in enumerate(self.lyrics):
            if current_time >= time:
                new_line_index = i
        if new_line_index != self.current_line_index:
            self.current_line_index = new_line_index
            new_content = ""
            for i, (time, text) in enumerate(self.lyrics):
                line_text = text or '♪'
                if i == self.current_line_index:
                    new_content += f"[reverse]{line_text}[/reverse]\n"
                else:
                    new_content += f"{line_text}\n"
            self.query_one("#lyrics_text", Static).update(new_content)
    def compose(self) -> ComposeResult:
        yield Header(name="Lyrics Viewer")
        with VerticalScroll(id="lyrics_container"):
            yield Static("Loading lyrics...", id="lyrics_text")
        yield Footer()
    def on_mount(self) -> None:
        lyrics_widget = self.query_one("#lyrics_text", Static)
        if not self.current_song:
            lyrics_widget.update("No song is currently playing.")
            return
        self.app.sub_title = self.current_song.title
        lrc_path = os.path.splitext(self.current_song.path)[0] + ".lrc"
        if os.path.exists(lrc_path):
            try:
                with open(lrc_path, 'r', encoding='utf-8') as f:
                    lrc_content = f.read()
                self.lyrics = self._parse_lrc(lrc_content)
                if not self.lyrics:
                    lyrics_widget.update(lrc_content or "Lyrics file is empty or has an invalid format.")
                else:
                    self.update_timer.resume()
            except Exception as e:
                lyrics_widget.update(f"Error reading lyrics file:\n{e}")
        else:
            lyrics_widget.update("No lyrics file (.lrc) found for this song.")
    def on_unmount(self) -> None:
        self.update_timer.pause()

# --- 命令屏幕 ---
class CommandScreen(Screen):
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
        if self.callback:
            self.callback(event.value)

# --- 搜索屏幕 ---
class SearchScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back"), ("n", "next_page", "Next Page"), ("p", "previous_page", "Prev Page"), ("a", "download_all", "Download All")]
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
        self.query_one("#search_results_list", ListView).clear()
        self.query_one(Input).disabled = True
        self.app.sub_title = f"Searching for '{query}' on page {page}..."
        thread = threading.Thread(target=self.search_worker, args=[query, page])
        thread.start()
    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.current_query = event.value
        self.current_page = 1
        self.total_pages = 1
        self.start_search(self.current_query, self.current_page)
    def search_worker(self, query: str, page: int):
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
        downloaded_count = 0; errors = []
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
            self.current_page += 1; self.start_search(self.current_query, self.current_page)
    def action_previous_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1; self.start_search(self.current_query, self.current_page)
    def action_download_all(self) -> None:
        list_view = self.query_one("#search_results_list", ListView)
        songs_on_page = [child.song_data for child in list_view.children if hasattr(child, "song_data")]
        if not songs_on_page: return
        self.app.sub_title = f"Queueing {len(songs_on_page)} songs for download..."
        thread = threading.Thread(target=self.download_worker, args=[songs_on_page])
        thread.start()

# --- 主应用 ---
class MocPlusApp(App):
    BINDINGS = [
        ("q", "quit", "Quit"), ("s", "push_screen('search')", "Search"),
        ("p", "toggle_pause", "Play/Pause"), ("l", "toggle_lyrics", "Show Lyrics"),
        ("r", "import_from_folders", "Import from Folders"), ("delete", "delete_song", "Delete Song"),
        ("ctrl+s", "show_save_screen", "Save Playlist"), ("ctrl+o", "show_load_screen", "Load Playlist"),
    ]
    SCREENS = {"search": SearchScreen, "command": CommandScreen, "lyrics": LyricsScreen}
    CSS_PATH = "tui.css"
    status_text = var("STATUS: Welcome to MOC-Plus!")

    def __init__(self):
        super().__init__()
        self.player: Optional[Player] = None
        self.playlist = Playlist()
        self.config_dir = os.path.expanduser("~/.mpvs"); self.playlist_path = os.path.join(self.config_dir, "default.m3u")
        if not os.path.exists(self.config_dir): os.makedirs(self.config_dir)
        self.music_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '斗破苍穹'))
        self.downloads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'downloads'))
    def compose(self) -> ComposeResult:
        yield Header(name="MOC-Plus Terminal Player"); yield Static(id="status_bar")
        with VerticalScroll(id="playlist_view"):
            yield ListView(id="playlist_listview")
        yield Footer()
    def on_mount(self) -> None:
        self.player = Player(); self.action_load_playlist(self.playlist_path)
    def on_search_finished(self, result) -> None:
        if not isinstance(self.screen, SearchScreen): return
        search_screen = self.screen; list_view = search_screen.query_one("#search_results_list", ListView)
        input_widget = search_screen.query_one(Input); input_widget.disabled = False
        if isinstance(result, Exception):
            self.sub_title = f"Search failed: {result}"; list_view.append(ListItem(Static(f"Error: {result}")))
        else:
            search_results, total_pages, total_songs = result; search_screen.total_pages = total_pages
            self.sub_title = f"Found {total_songs} songs | Page {search_screen.current_page}/{total_pages}"
            if not search_results: list_view.append(ListItem(Static("No results found.")))
            else:
                for song in search_results:
                    list_item = ListItem(Static(song['title'])); list_item.song_data = song; list_view.append(list_item)
        input_widget.focus()
    def on_download_finished(self, result) -> None:
        downloaded_count, errors = result; new_songs_playlist = Playlist()
        new_songs_playlist.scan_directory(self.downloads_dir); added_count = 0
        for song in new_songs_playlist.songs:
            if not any(p_song.path == song.path for p_song in self.playlist.songs):
                self.playlist.songs.append(song); added_count += 1
        if errors: self.sub_title = f"Completed. Downloaded {downloaded_count}. {len(errors)} failed."
        else: self.sub_title = f"Successfully downloaded {downloaded_count} song(s)."
        if isinstance(self.screen, SearchScreen): self.pop_screen()
        self._update_playlist_view()
        if added_count > 0: self.status_text = f"Added {added_count} new song(s). Press Ctrl+S to save."
        else: self.status_text = "Download complete. No new songs added to playlist."
    def _update_playlist_view(self):
        list_view = self.query_one("#playlist_listview", ListView); list_view.clear()
        if not self.playlist.songs: list_view.append(ListItem(Static("Playlist is empty. Press 'r' to import from folders.")))
        else:
            for song in self.playlist.songs:
                list_item = ListItem(Static(song.title)); list_item.song_data = song; list_view.append(list_item)
    def action_show_load_screen(self):
        self.push_screen(CommandScreen("Load playlist from:", self.playlist_path, self.action_load_playlist))
    def action_show_save_screen(self):
        self.push_screen(CommandScreen("Save playlist as:", self.playlist_path, self.action_save_playlist))
    def action_load_playlist(self, path: str):
        self.playlist_path = path; self.playlist.load_m3u(self.playlist_path)
        self._update_playlist_view(); self.status_text = f"Loaded playlist from {self.playlist_path}"
    def action_save_playlist(self, path: str):
        self.playlist_path = path; self.playlist.save_m3u(self.playlist_path)
        self.status_text = f"Playlist saved to {self.playlist_path}"
    def action_import_from_folders(self) -> None:
        self.playlist.scan_directory(self.music_dir); self.playlist.scan_directory(self.downloads_dir)
        self._update_playlist_view(); self.status_text = "Imported songs from local folders. Press Ctrl+S to save."
    def action_toggle_lyrics(self) -> None:
        if isinstance(self.screen, LyricsScreen): self.pop_screen()
        else:
            list_view = self.query_one("#playlist_listview", ListView)
            if list_view.highlighted_child and hasattr(list_view.highlighted_child, 'song_data'):
                current_song = list_view.highlighted_child.song_data
                self.push_screen(LyricsScreen(self.player, current_song))
            else: self.status_text = "Select a song to show lyrics."
    def action_delete_song(self) -> None:
        list_view = self.query_one("#playlist_listview", ListView)
        if list_view.highlighted_child is None: return
        index_to_delete = list_view.index
        if index_to_delete is None: return
        self.playlist.delete_song(index_to_delete); self._update_playlist_view()
        if self.playlist.songs:
            new_index = min(index_to_delete, len(self.playlist.songs) - 1)
            list_view.index = new_index
        self.status_text = "Song removed. Press Ctrl+S to save changes."
    def action_toggle_pause(self) -> None:
        if self.player: self.player.toggle_pause()
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "playlist_listview":
            if hasattr(event.item, 'song_data'):
                song_to_play: Song = event.item.song_data
                if self.player: self.player.play(song_to_play.path); self.status_text = f"Playing: {song_to_play.title}"
    def watch_status_text(self, new_text: str) -> None:
        self.query_one("#status_bar", Static).update(new_text)
    def action_quit(self) -> None:
        if self.player: self.player.quit()
        self.exit()

def main():
    app = MocPlusApp()
    app.run()

if __name__ == "__main__":
    main()
