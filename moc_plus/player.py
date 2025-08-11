import mpv
import os
from typing import Optional

class Player:
    """
    回归到最初的、基于 python-mpv 的强大播放器。
    它通过回调函数自动、实时地更新状态。
    """
    def __init__(self):
        try:
            # log_handler=lambda l, L, p: None 禁用了来自 mpv 的日志输出，避免干扰UI
            self.mpv = mpv.MPV(idle=True, ytdl=False, log_handler=lambda l, L, p: None)
        except FileNotFoundError:
            raise RuntimeError("mpv executable not found. Please install mpv.")

        self._current_time: float = 0.0
        self._is_paused: bool = True
        self._current_song_title: Optional[str] = None

        # 注册回调函数，当 mpv 的属性变化时，会自动调用这些方法
        @self.mpv.property_observer('time-pos')
        def _time_observer(_name, value):
            """当播放时间更新时由mpv回调"""
            self._current_time = value if value is not None else 0.0

        @self.mpv.property_observer('pause')
        def _pause_observer(_name, value):
            """当播放状态改变时由mpv回调"""
            self._is_paused = value if value is not None else True
        
        @self.mpv.property_observer('media-title')
        def _title_observer(_name, value):
            """当曲目名称更新时由mpv回调"""
            self._current_song_title = value

    def get_current_time(self) -> float:
        return self._current_time

    def get_current_song_title(self) -> Optional[str]:
        return self._current_song_title

    def is_paused(self) -> bool:
        return self._is_paused

    def play(self, filepath: str):
        if not os.path.exists(filepath): return
        self.mpv.play(filepath)

    def toggle_pause(self):
        self.mpv.pause = not self.mpv.pause

    def stop(self):
        self.mpv.stop()

    def quit(self):
        self.mpv.quit()