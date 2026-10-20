import os
import tkinter as tk
from tkinter.filedialog import askopenfilenames

import pygame
from mutagen import MutagenError
from mutagen.easyid3 import EasyID3


def read_tags(path):
    """Return (title, artist) for a song, falling back to the file name if it has no tags."""
    try:
        song = EasyID3(path)
        return song["title"][0], song["artist"][0]
    except (MutagenError, KeyError):
        return os.path.basename(path), "Unknown artist"


class MusicPlayer:
    def __init__(self):
        self.playlist = []
        self.is_paused = False
        self.current_index = 0
        self.song_end_event = pygame.USEREVENT + 1
        self.song_list_box = ""
        self.status_label = ""

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

    def now_playing_text(self):
        title, artist = read_tags(self.playlist[self.current_index])
        return f"Now playing {self.current_index + 1} {title}, artist {artist}"

    def check_song_end(self):
        for event in pygame.event.get():
            if event.type == self.song_end_event:
                self.next_song()

    def next_index(self):
        if self.current_index + 2 <= len(self.playlist):
            return self.current_index + 1
        else:
            return 0

    def previous_index(self):
        if self.current_index - 1 >= 0:
            return self.current_index - 1
        else:
            return len(self.playlist) - 1


class PlayerWindow(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.music_player = MusicPlayer()
        self.grid()

        buttons = {
            "add": PlayerButton(
                self, self.music_player, text="ADD TO LIST", command="add_songs_button"
            ),
            "play": PlayerButton(
                self, self.music_player, text="PLAY SONG", command="play_song_button"
            ),
            "pause": PlayerButton(
                self,
                self.music_player,
                text="PAUSE/UNPAUSE",
                command="toggle_pause_button",
            ),
            "prev": PlayerButton(
                self,
                self.music_player,
                text="PREVIOUS SONG",
                command="previous_song_button",
            ),
            "next": PlayerButton(
                self, self.music_player, text="NEXT SONG", command="next_song_button"
            ),
        }

        self.music_player.status_label = tk.Label(
            self, fg="Black", font=("Helvetica 12 bold italic", 10), bg="ivory2"
        )
        self.music_player.song_list_box = tk.Text(self, wrap=tk.WORD, width=60)
        for row, action in enumerate(["add", "play", "pause", "prev", "next"]):
            buttons[action].widget.grid(row=row, column=0)

        self.music_player.status_label.grid(row=6, column=0)
        self.music_player.song_list_box.grid(row=8, column=0)


class PlayerButton:
    def __init__(
        self, master, music_player, text, command, bg="AntiqueWhite1", width=40
    ):
        self.music_player = music_player
        match command:
            case "add_songs_button":
                action = self.add_songs_button
            case "play_song_button":
                action = self.play_song_button
            case "toggle_pause_button":
                action = self.toggle_pause_button
            case "previous_song_button":
                action = self.previous_song_button
            case "next_song_button":
                action = self.next_song_button
            case _:
                raise ValueError(f"Unknown command: {command}")
        self.widget = tk.Button(master, text=text, command=action, bg=bg, width=width)

    def add_songs_button(self):
        selected_paths = askopenfilenames()
        for song_path in selected_paths:
            self.music_player.playlist.append(song_path)
        self.music_player.song_list_box.delete(0.0, tk.END)

        for number, song_path in enumerate(self.music_player.playlist, start=1):
            title, artist = read_tags(song_path)
            song_line = f"{number} : {title}, {artist}"
            self.music_player.song_list_box.insert(tk.END, song_line + "\n")

    def play_song_button(self):
        self.music_player.play_song()

    def toggle_pause_button(self):
        self.music_player.toggle_pause()

    def next_song_button(self):
        self.music_player.next_song()

    def previous_song_button(self):
        self.music_player.previous_song()


window = tk.Tk()
window.geometry("500x500")
window.title("MP3 Music Player")
pygame.init()

app = PlayerWindow(window)

while True:
    # runs mainloop of program
    app.music_player.check_song_end()
    app.update()
