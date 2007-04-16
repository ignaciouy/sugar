# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
import hippo
import cairo

from sugar.graphics.menushell import MenuShell
from sugar.graphics import units
import sugar

from view.home.MeshBox import MeshBox
from view.home.HomeBox import HomeBox
from view.home.FriendsBox import FriendsBox
from view.home.transitionbox import TransitionBox

_HOME_PAGE       = 0
_FRIENDS_PAGE    = 1
_MESH_PAGE       = 2
_TRANSITION_PAGE = 3

class HomeWindow(gtk.Window):
    def __init__(self, shell):
        gtk.Window.__init__(self)
        self._shell = shell
        self._active = False
        self._level = sugar.ZOOM_HOME

        self.set_default_size(gtk.gdk.screen_width(),
                              gtk.gdk.screen_height())

        self.realize()
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)
        self.connect("key-release-event", self._key_release_cb)
        self.connect('focus-in-event', self._focus_in_cb)
        self.connect('focus-out-event', self._focus_out_cb)

        self._nb = gtk.Notebook()
        self._nb.set_show_border(False)
        self._nb.set_show_tabs(False)

        self.add(self._nb)
        self._nb.show()

        canvas = hippo.Canvas()
        self._home_box = HomeBox(shell)
        canvas.set_root(self._home_box)
        self._nb.append_page(canvas)
        canvas.show()

        canvas = hippo.Canvas()
        box = FriendsBox(shell, MenuShell(canvas))
        canvas.set_root(box)
        self._nb.append_page(canvas)
        canvas.show()

        canvas = hippo.Canvas()
        self._mesh_box = MeshBox(shell, MenuShell(canvas))
        canvas.set_root(self._mesh_box)
        self._nb.append_page(canvas)
        canvas.show()

        canvas = hippo.Canvas()
        self._transition_box = TransitionBox()
        canvas.set_root(self._transition_box)
        self._nb.append_page(canvas)
        canvas.show()
        
        self._transition_box.connect('completed',
                                     self._transition_completed_cb)

    def _key_release_cb(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == "Alt_L":
            self._home_box.release()

    def _update_mesh_state(self):
        if self._active and self._nb.get_current_page() == _MESH_PAGE:
            self._mesh_box.resume()
        else:
            self._mesh_box.suspend()

    def _focus_in_cb(self, widget, event):
        self._active = True
        self._update_mesh_state()

    def _focus_out_cb(self, widget, event):
        self._active = False
        self._update_mesh_state()
            
    def set_zoom_level(self, level):
        self._level = level
    
        self._nb.set_current_page(_TRANSITION_PAGE)

        if level == sugar.ZOOM_HOME:
            scale = units.XLARGE_ICON_SCALE
        elif level == sugar.ZOOM_FRIENDS:
            scale = units.LARGE_ICON_SCALE
        elif level == sugar.ZOOM_MESH:
            scale = units.STANDARD_ICON_SCALE
            
        self._transition_box.set_scale(scale)
    
    def _transition_completed_cb(self, transition_box):
        if self._level == sugar.ZOOM_HOME:
            self._nb.set_current_page(_HOME_PAGE)
        elif self._level == sugar.ZOOM_FRIENDS:
            self._nb.set_current_page(_FRIENDS_PAGE)
        elif self._level == sugar.ZOOM_MESH:
            self._nb.set_current_page(_MESH_PAGE)

        self._update_mesh_state()
        
    def get_home_box(self):
        return self._home_box   
