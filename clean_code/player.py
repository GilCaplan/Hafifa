import os
import tkinter as tk
from tkinter.filedialog import askopenfilenames

import pygame
from mutagen import MutagenError
from mutagen.easyid3 import EasyID3

WINDOW_SIZE = "500x500"
WINDOW_TITLE = "MP3 Music Player"
TEXT_COLOR = "Black"
STATUS_FONT = ("Helvetica 12 bold italic", 10)
STATUS_BG = "ivory2"
BUTTON_BG = "AntiqueWhite1"
BUTTON_WIDTH = 40
SONG_LIST_WIDTH = 60


def read_tags(path) -> tuple[str, str]:
    """Return (title, artist) for a song, falling back to the file name if it has no tags."""
    try:
        song = EasyID3(path)
        return song["title"][0], song["artist"][0]
    except (MutagenError, KeyError):
        return os.path.basename(path), "Unknown artist"


class MusicPlayer:
    def __init__(self):
        self.playlist = [] # no current UI design more multiple playlists so keep individual for now.
        self.is_paused = False
        self.current_index = 0
        self.song_end_event = pygame.USEREVENT + 1
        self.song_list_box = ""
        self.status_label = ""

    def add_songs(self, paths):
        self.playlist.extend(paths)

    def play_song(self):
        if not self.playlist:
            return
        song_path = self.playlist[self.current_index]
        try:
            pygame.mixer.music.load(song_path)
        except pygame.error:
            self.status_label["text"] = f"Can't play {os.path.basename(song_path)}"
            return
        pygame.mixer.music.play(1, 0.0)
        pygame.mixer.music.set_endevent(self.song_end_event)
        self.is_paused = False
        self.status_label["text"] = self.now_playing_text()

    def toggle_pause(self):
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
        else:
            pygame.mixer.music.pause()
            self.is_paused = True

    def next_song(self):
        if not self.playlist:
            return
        self.current_index = self.next_index()
        self.play_song()

    def previous_song(self):
        if not self.playlist:
            return
        self.current_index = self.previous_index()
        self.play_song()

    def now_playing_text(self) -> str:
        title, artist = read_tags(self.playlist[self.current_index])
        return f"Now playing {self.current_index + 1} {title}, artist {artist}"

    def check_song_end(self):
        for event in pygame.event.get():
            if event.type == self.song_end_event:
                self.next_song()

    def next_index(self) -> int:
        idx = self.current_index
        return idx + 1 if idx + 2 <= len(self.playlist) else 0

    def previous_index(self) -> int:
        idx = self.current_index - 1
        return idx if idx >= 0 else len(self.playlist) - 1


class PlayerWindow(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.music_player = MusicPlayer()
        self.grid()

        buttons = self._create_buttons()

        self.music_player.status_label = tk.Label(
            self, fg=TEXT_COLOR, font=STATUS_FONT, bg=STATUS_BG
        )
        self.music_player.song_list_box = tk.Text(
            self, wrap=tk.WORD, width=SONG_LIST_WIDTH
        )
        for row, button in enumerate(buttons):
            button.grid(row=row, column=0)

        self.music_player.status_label.grid(row=6, column=0)
        self.music_player.song_list_box.grid(row=8, column=0)

    def _create_buttons(self) -> list[tk.Button]:
        actions = (
            ("ADD TO LIST", self.add_songs),
            ("PLAY SONG", self.music_player.play_song),
            ("PAUSE/UNPAUSE", self.music_player.toggle_pause),
            ("PREVIOUS SONG", self.music_player.previous_song),
            ("NEXT SONG", self.music_player.next_song),
        )
        return [
            tk.Button(self, text=text, command=action, bg=BUTTON_BG, width=BUTTON_WIDTH)
            for text, action in actions
        ]

    def add_songs(self):
        paths = askopenfilenames()
        self.music_player.add_songs(paths)
        self.refresh_song_list()

    def refresh_song_list(self):
        song_list_box = self.music_player.song_list_box
        song_list_box.delete(0.0, tk.END)
        for number, song_path in enumerate(self.music_player.playlist, start=1):
            title, artist = read_tags(song_path)
            song_list_box.insert(tk.END, f"{number} : {title}, {artist}\n")


def init_app() -> PlayerWindow:
    window = tk.Tk()
    window.geometry(WINDOW_SIZE)
    window.title(WINDOW_TITLE)
    pygame.init()
    return PlayerWindow(window)


def run(app):
    while True:
        app.music_player.check_song_end()
        app.update()


def main():
    app = init_app()
    run(app)


if __name__ == "__main__":
    main()
