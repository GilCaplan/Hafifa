from mutagen.easyid3 import EasyID3
import pygame
from tkinter.filedialog import *
from tkinter import *

class MusicPlayer:
    def __init__(self):
        self.list1 = list()
        self.pausing = False
        self.list_index = 0
        self.SONG_END = pygame.USEREVENT + 1
        self.text1 = ""
        self.label1 = ""

class FrameApp(Frame):
    def __init__(self,master):
        super(FrameApp, self).__init__(master)
        self.music_player = MusicPlayer()
        self.grid()
        b = {
            "b1": Button(self, text="PLAY SONG",command=button2,bg='AntiqueWhite1',width=40),
            "b2": Button(self, text="PREVIOUS SONG",command=button4,bg='AntiqueWhite1',width=40),
            "b3": Button(self, text="PAUSE/UNPAUSE",command=button3,bg='AntiqueWhite1',width=40),
            "b4": Button(self, text="NEXT SONG",command=button5,bg='AntiqueWhite1',width=40),
            "b5": Button(self, text="ADD TO LIST",command=button1,bg='AntiqueWhite1',width=40)
            }
        
        label1 = Label(self, fg='Black',font=('Helvetica 12 bold italic',10),bg='ivory2')
        text1 = Text(self,wrap=WORD,width=60)
        for i in range(5):
            b[f"b{i}"].grid(row=i,column=0)
        
        label1.grid(row=6,column=0)
        text1.grid(row=8,column=0)

#################################################################################

class Button:
    def __init__(self, music_player):
        self.music_player = music_player
    
    def add_songs_button(self):
        try:
            directory = askopenfilenames()
            for song_dir in directory:
                print(song_dir)
                self.music_player.list1.append(song_dir)
            self.music_player.text1.delete(0.0, END)

            for key, item in enumerate(self.music_player.list1):
                song = EasyID3(item)
                song_data = (str(key + 1) + ' : ' + song['title'][0] + ' - '
                            + song['artist'][0])
                self.music_player.text1.insert(END, song_data + '\n')
        except:
            pass
    
    def play_song_button(self):
        try:
            directory = self.music_player.list1[self.music_player.list_index]
            pygame.mixer.music.load(directory)
            pygame.mixer.music.play(1, 0.0)
            pygame.mixer.music.set_endevent(self.music_player.SONG_END)
            self.music_player.pausing = False
            self.music_player.label1['text'] = self.music_player.song_data()
        except:
            pass

    def toggle_pause_button(self):
        try:
            if self.music_player.pausing:
                pygame.mixer.music.unpause()
                self.music_player.pausing = False
            elif not self.music_player.pausing:
                pygame.mixer.music.pause()
                self.music_player.pausing = True
        except:
            pass

    def next_song_button(self):
        try:
            self.music_player.list_index = self.music_player.get_next_song()
            self.button2()
        except:
            pass

    def previous_song_button(self):
        try:
            self.music_player.list_index = self.music_player.get_previous_song()
            self.button2()
        except:
            pass

class Song:
    def __init__(self, music_player):
        self.music_player = music_player

    def song_data(self):
        
        try:
            song = EasyID3(self.music_player.list1[self.music_player.list_index])
            song_data = "Now playing: Nr:" + str(self.music_player.list_index + 1) + " " + \
                        str(song['title']) + " - " + str(song['artist'])
            return song_data
        except:
            pass
        
    def check_music(self):
        try:
            for event in pygame.event.get():
                if event.type == self.music_player.SONG_END:
                    self.music_player.next_song_button()
        except:
            pass

    def get_next_song(self):
        try:
            if self.music_player.list_index + 2 <= len(self.music_player.list1):
                return self.music_player.list_index + 1
            else:
                return 0
        except:
            pass

    def get_previous_song(self):
        try:
            if self.music_player.list_index - 1 >= 0:
                return self.music_player.list_index - 1
            else:
                return len(self.music_player.list1) - 1
        except:
            pass


window = Tk()
window.geometry("500x500")
window.title("MP3 Music Player")
pygame.init()

app = FrameApp(window)

while True:
    # runs mainloop of program
    song = Song()
    song.check_music()
    app.update()

