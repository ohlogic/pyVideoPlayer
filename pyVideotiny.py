#!/usr/bin/python3

import os
import time

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gst", "1.0")
gi.require_version("GstVideo", "1.0")
from gi.repository import Gst, Gtk, Gdk, GLib, GstVideo, GObject

import sys
import ctypes

Gst.init(None)

if sys.platform == 'win32':
    PyCapsule_GetPointer = ctypes.pythonapi.PyCapsule_GetPointer
    PyCapsule_GetPointer.restype = ctypes.c_void_p
    PyCapsule_GetPointer.argtypes = [ctypes.py_object]
    gdkdll = ctypes.CDLL('libgdk-3-0.dll')
    gdkdll.gdk_win32_window_get_handle.argtypes = [ctypes.c_void_p]
    
    def get_window_handle(widget):
        window = widget.get_window()
        if not window.ensure_native():
            raise Exception('video playback requires a native window')
        
        window_gpointer = PyCapsule_GetPointer(window.__gpointer__, None)
        handle = gdkdll.gdk_win32_window_get_handle(window_gpointer)
        return handle
else:
    def get_window_handle(widget):
        return widget.get_window().get_xid()

class VideoPlayer:
    def __init__(self, window, canvas, filelist, index = 0):
        self.window = window
        self._canvas = canvas
        self._setupplayer()
        self.index = index
        self.files = filelist 
    
    def _setupplayer(self):
        self._video_overlay = None
        self.player = Gst.ElementFactory.make("playbin", "MultimediaPlayer")
        self._setup_signal_handlers()
        
    def _setup_signal_handlers(self):
        self._canvas.connect('realize', self._on_canvas_realize)
        bus = self.player.get_bus()
        bus.enable_sync_message_emission()
        bus.connect('sync-message::element', self._on_sync_element_message)
    
    def _on_sync_element_message(self, bus, message):
        if message.get_structure().get_name() == 'prepare-window-handle':
            self._video_overlay = message.src
            self._video_overlay.set_window_handle(self._canvas_window_handle)
    
    def _on_canvas_realize(self, canvas):
        self._canvas_window_handle = get_window_handle(canvas)

    def start(self):
        self.player.set_property('uri',  self.files[self.index])
        self.player.set_state(Gst.State.PLAYING)
    
    def _openVideo(self):
        self.window.set_title( self.files[self.index] )
        self.player.set_state(Gst.State.NULL)
        self.player.set_property("uri", self.files[self.index] )
        self.player.set_state(Gst.State.PLAYING)

    def previousVideo(self):
        print('previous video')
        self.index -= 1
        if self.index <= -1:
            self.index = 0
            
        print ( self.files[self.index] )
        
        self._openVideo()
        
    def nextVideo(self):
        print('next video')
        self.index += 1
        if self.index >= len(self.files):
            self.index = len(self.files) - 1
            
        print ( self.files[self.index] )
        self._openVideo()
        
    def on_key_press(self, widget, event):

        key = Gdk.keyval_name(event.keyval)
        if key == 'Left':
            self.previousVideo()
            return True
        elif key == 'Right':
            self.nextVideo()
            return True
        elif key == 'f' or key == Gdk.KEY_F11:
            self.toggle_fullscreen()
        elif key == 'Escape':
            Gtk.main_quit()

if __name__ == "__main__":

    if len(sys.argv) > 1:

        ext = (".mp4",".mkv")
        videos = []
        directory = os.path.dirname(   os.path.abspath(sys.argv[1])   )
        print ('directory' + directory )
        print ( 'file:///' + os.path.abspath(os.path.join(directory, sys.argv[1])) )
        videos.append ( 'file:///' + os.path.abspath(os.path.join(directory, sys.argv[1])) )
        
        files = sorted(os.listdir(directory), reverse = True)
        for file in files:
            if file.lower().endswith(ext):
                videos.append('file:///' + os.path.abspath(os.path.join(directory, file)))
            
        print ( 'length of videos:' + str(len(videos)) )
        for v in videos:
            print (v)
        
        window = Gtk.Window()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        window.add(vbox)

        canvas_box = Gtk.Box()
        vbox.add(canvas_box)

        canvas1 = Gtk.DrawingArea()
        canvas1.set_size_request(400, 400)
        canvas_box.add(canvas1)

        player = VideoPlayer(window, canvas1, videos)

        window.connect("key-press-event", player.on_key_press)

        canvas1.connect('realize', lambda *_: player.start())
        
        window.connect('destroy', Gtk.main_quit)
        window.show_all()
        Gtk.main()
        