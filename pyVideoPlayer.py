#!/usr/bin/python3
#
# Copyright 2019 Stan S
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# You may contact Stan S via electronic mail with the address vfpro777@yahoo.com

import os
import time

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gst", "1.0")
gi.require_version("GstVideo", "1.0")
from gi.repository import Gst, Gtk, Gdk, GLib, GstVideo, GObject

import sys
import ctypes

class GenericException(Exception):
    pass


class Handler:

    def on_window_destroy(self, *args):
        Gtk.main_quit()

    def on_playpause_togglebutton_toggled(self, widget):
        if app.playpause_button.get_active():
            img = Gtk.Image.new_from_icon_name(Gtk.STOCK_MEDIA_PLAY,
                                               Gtk.IconSize.BUTTON)
            widget.set_property("image", img)
            app.pause()
        else:
            img = Gtk.Image.new_from_icon_name(Gtk.STOCK_MEDIA_PAUSE,
                                               Gtk.IconSize.BUTTON)
            widget.set_property("image", img)
            app.play()
       
    def on_forward_clicked(self, widget):
        app.skip_time()

    def on_backward_clicked(self, widget):
        app.skip_time(-1)
    
    def on_progress_value_changed(self, widget):
        app.on_slider_seek

    def on_vbutton_clicked(self, widget):
        app.clear_playbin()
        app.setup_player("")
        if app.playpause_button.get_active() is True:
            app.playpause_button.set_active(False)
        else:
            app.play()


class GstPlayer:

    is_fullscreen = False

    def __init__(self):
        
        # init GStreamer
        Gst.init(None)
        
        # setting up builder
        builder = Gtk.Builder()
        self.builder = builder
        builder.add_from_string(Glade_file().get_string())
        
        builder.connect_signals(Handler())

        self.movie_window = builder.get_object("play_here")
        self.movie_window.set_double_buffered (True)
        self.playpause_button = builder.get_object("playpause_togglebutton")
        self.slider = builder.get_object("progress")
        self.slider_handler_id = self.slider.connect("value-changed", self.on_slider_seek)

        window = builder.get_object("window")
        self.window = window
        
        window.show_all()
        window.connect("key-press-event", self.on_key_press)
        
        # setting up videoplayer
        self.player = Gst.ElementFactory.make("playbin", "player")
        if sys.platform == "win32":
            window.maximize() # a somewhat "fix" to 'glimagesink' not resizing
            self.sink = Gst.ElementFactory.make("glimagesink")  # xvimagesink, autovideosink, d3dvideosink, osxvideosink, gtksink, gtkglsink, glimagesink
        else:
            self.sink = Gst.ElementFactory.make("xvimagesink")
        #self.sink.set_property("force-aspect-ratio", True)

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.window.unfullscreen()
            self.builder.get_object("box2").show()
            self.builder.get_object("box3").show()

            self.is_fullscreen = False
        else:
            self.window.fullscreen()
            self.builder.get_object("box2").hide()
            self.builder.get_object("box3").hide()
            self.is_fullscreen = True        
          
    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
        elif event.keyval == Gdk.KEY_F11:
            self.toggle_fullscreen()
            
    def setup_player(self,f):
        # file to play must be transmitted as uri
        dialog = Gtk.FileChooserDialog("Please choose a file", self.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("Open clicked")
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")
            
        uri = dialog.get_uri()
        dialog.destroy()
        #uri = "file://" + os.path.abspath(f)
        self.player.set_property("uri", uri)
        
        video_window = self.movie_window.get_property('window')
        if sys.platform == "win32":
            if not video_window.ensure_native():
                print("Error - video playback requires a native window")
            ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.c_void_p
            ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object]
            drawingarea_gpointer = ctypes.pythonapi.PyCapsule_GetPointer(video_window.__gpointer__, None)
            gdkdll = ctypes.CDLL ("libgdk-3-0.dll")
            win_id = gdkdll.gdk_win32_window_get_handle(drawingarea_gpointer)
        else: # Linux
            # make playbin play in specified DrawingArea widget instead of
            # separate, GstVideo needed
            win_id = self.movie_window.get_window().get_xid()

        self.sink.set_window_handle(win_id)
        self.player.set_property("video-sink", self.sink)
            
    def play(self):
        self.is_playing = True
        self.player.set_state(Gst.State.PLAYING)
        #starting up a timer to check on the current playback value
        GLib.timeout_add(1000, self.update_slider)
        
    def pause(self):
        self.is_playing = False
        self.player.set_state(Gst.State.PAUSED)
        
    def current_position(self):
        status,position = self.player.query_position(Gst.Format.TIME)
        return position

    def skip_time(self,direction=1):
        #skip 20 seconds on forward/backward button
        app.player.seek_simple(Gst.Format.TIME,  Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 
            self.current_position() + float(20) * Gst.SECOND * direction )

    def update_slider(self):
        if not self.is_playing:
            return False # cancel timeout
        else:
            success, self.duration = self.player.query_duration(Gst.Format.TIME)
            # adjust duration and position relative to absolute scale of 100
            self.mult = 100 /  (1 if (self.duration / Gst.SECOND) == 0 else (self.duration / Gst.SECOND))
            
            if not success:
                raise GenericException("Couldn't fetch duration")
            # fetching the position, in nanosecs
            success, position = self.player.query_position(Gst.Format.TIME)
            if not success:
                raise GenericException("Couldn't fetch current position to update slider")
            
            # block seek handler so we don't seek when we set_value()
            self.slider.handler_block(self.slider_handler_id)
            self.slider.set_value(float(position) / Gst.SECOND * self.mult)
            self.slider.handler_unblock(self.slider_handler_id)
        return True # continue calling every x milliseconds

    def on_slider_seek(self, slider):
        success, self.duration = self.player.query_duration(Gst.Format.TIME)
        seek_time_secs = slider.get_value()
        self.player.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 
            self.duration * (seek_time_secs/100)  )
        #self.player.seek(1.0, Gst.Format.TIME, (Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE),
        #    Gst.SeekType.SET, self.duration * (seek_time_secs/100), Gst.SeekType.NONE, -1)
    
    def clear_playbin(self):
        try:
            self.player.set_state(Gst.State.NULL)
        except:
            pass

    def main(self):
        Gtk.main()


class Glade_file:
    gladestring = """
<?xml version="1.0" encoding="UTF-8"?>
<!-- Generated with glade 3.20.0 -->
<interface>
  <requires lib="gtk+" version="3.16"/>
  <object class="GtkAdjustment" id="adjustment">
    <property name="upper">100</property>
    <property name="step_increment">1</property>
    <property name="page_increment">10</property>
  </object>
  <object class="GtkImage" id="image1">
    <property name="visible">True</property>
    <property name="can_focus">False</property>
    <property name="stock">gtk-media-rewind</property>
  </object>
  <object class="GtkImage" id="image2">
    <property name="visible">True</property>
    <property name="can_focus">False</property>
    <property name="stock">gtk-media-forward</property>
  </object>
  <object class="GtkImage" id="image3">
    <property name="visible">True</property>
    <property name="can_focus">False</property>
    <property name="stock">gtk-media-pause</property>
  </object>
  <object class="GtkWindow" id="window">
    <property name="can_focus">False</property>
    <property name="title" translatable="yes">GStreamer media player</property>
    <property name="default_width">600</property>
    <property name="default_height">350</property>
    <signal name="destroy" handler="on_window_destroy" swapped="no"/>
    <child>
      <object class="GtkBox" id="box1">
        <property name="visible">True</property>
        <property name="can_focus">False</property>
        <property name="orientation">vertical</property>
        <child>
          <object class="GtkDrawingArea" id="play_here">
            <property name="visible">True</property>
            <property name="can_focus">False</property>
          </object>
          <packing>
            <property name="expand">True</property>
            <property name="fill">True</property>
            <property name="position">0</property>
          </packing>
        </child>
        <child>
          <object class="GtkSeparator" id="separator1">
            <property name="visible">True</property>
            <property name="can_focus">False</property>
          </object>
          <packing>
            <property name="expand">False</property>
            <property name="fill">True</property>
            <property name="position">1</property>
          </packing>
        </child>
        <child>
          <object class="GtkBox" id="box3">
            <property name="visible">True</property>
            <property name="can_focus">False</property>
            <child>
              <object class="GtkButtonBox" id="buttonbox1">
                <property name="visible">True</property>
                <property name="can_focus">False</property>
                <property name="layout_style">start</property>
                <child>
                  <object class="GtkButton" id="backward">
                    <property name="visible">True</property>
                    <property name="can_focus">True</property>
                    <property name="receives_default">True</property>
                    <property name="image">image1</property>
                    <property name="always_show_image">True</property>
                    <signal name="clicked" handler="on_backward_clicked" swapped="no"/>
                  </object>
                  <packing>
                    <property name="expand">True</property>
                    <property name="fill">True</property>
                    <property name="position">0</property>
                  </packing>
                </child>
                <child>
                  <object class="GtkButton" id="forward">
                    <property name="visible">True</property>
                    <property name="can_focus">True</property>
                    <property name="receives_default">True</property>
                    <property name="image">image2</property>
                    <property name="always_show_image">True</property>
                    <signal name="clicked" handler="on_forward_clicked" swapped="no"/>
                  </object>
                  <packing>
                    <property name="expand">True</property>
                    <property name="fill">True</property>
                    <property name="position">1</property>
                  </packing>
                </child>
                <child>
                  <object class="GtkToggleButton" id="playpause_togglebutton">
                    <property name="visible">True</property>
                    <property name="can_focus">True</property>
                    <property name="receives_default">True</property>
                    <property name="image">image3</property>
                    <signal name="toggled" handler="on_playpause_togglebutton_toggled" swapped="no"/>
                  </object>
                  <packing>
                    <property name="expand">True</property>
                    <property name="fill">True</property>
                    <property name="position">2</property>
                  </packing>
                </child>
              </object>
              <packing>
                <property name="expand">False</property>
                <property name="fill">False</property>
                <property name="position">0</property>
              </packing>
            </child>
            <child>
              <object class="GtkScale" id="progress">
                <property name="width_request">300</property>
                <property name="visible">True</property>
                <property name="can_focus">True</property>
                <property name="halign">center</property>
                <property name="margin_left">5</property>
                <property name="margin_right">5</property>
                <property name="adjustment">adjustment</property>
                <property name="fill_level">100</property>
                <property name="round_digits">1</property>
                <property name="draw_value">False</property>
              </object>
              <packing>
                <property name="expand">False</property>
                <property name="fill">False</property>
                <property name="position">1</property>
              </packing>
            </child>
          </object>
          <packing>
            <property name="expand">False</property>
            <property name="fill">True</property>
            <property name="position">2</property>
          </packing>
        </child>
        <child>
          <object class="GtkBox" id="box2">
            <property name="visible">True</property>
            <property name="can_focus">False</property>
            <property name="homogeneous">True</property>
            <child>
              <object class="GtkButton" id="vbutton">
                <property name="label" translatable="yes">Play video</property>
                <property name="visible">True</property>
                <property name="can_focus">True</property>
                <property name="receives_default">True</property>
                <signal name="clicked" handler="on_vbutton_clicked" swapped="no"/>
              </object>
              <packing>
                <property name="expand">True</property>
                <property name="fill">True</property>
                <property name="position">0</property>
              </packing>
            </child>
          </object>
          <packing>
            <property name="expand">False</property>
            <property name="fill">True</property>
            <property name="position">3</property>
          </packing>
        </child>
      </object>
    </child>
    <child>
      <placeholder/>
    </child>
  </object>
</interface>
"""
    def get_string(self):
        return self.gladestring

app = GstPlayer()
app.main()
