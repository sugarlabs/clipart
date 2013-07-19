# -*- coding: utf-8 -*-
#Copyright (c) 2011-2013 Walter Bender

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA

import os
import glob

from sugar3.activity import activity
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import StopButton
from sugar3.graphics.toolbutton import ToolButton
from sugar3.activity.widgets import _create_activity_icon as ActivityIcon
from sugar3.graphics.alert import NotifyAlert
from sugar3.graphics import style
from sugar3.datastore import datastore
from sugar3 import profile

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject

from gettext import gettext as _

MIME_TYPES = {'svg': 'image/svg+xml', 'png': 'image/png', 'gif': 'image/gif',
              'jpg': 'image/jpeg'}


class ClipArtActivity(activity.Activity):

    def __init__(self, handle):
        activity.Activity.__init__(self, handle, False)

        self._selected_image = None
        self.max_participants = 1

        self.toolbar_box = ToolbarBox()
        self.toolbar = self.toolbar_box.toolbar

        activity_button = ToolButton()
        icon = ActivityIcon(None)
        activity_button.set_icon_widget(icon)
        activity_button.set_tooltip(self.get_title())
        stop_button = StopButton(self)

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)

        self.save_button = ToolButton('image-save')
        self.save_button.set_tooltip(_('Save to Journal'))
        self.save_button.connect('clicked', self._save_to_journal)
        self.save_button.set_sensitive(False)

        self.toolbar.insert(activity_button, 0)
        self.toolbar.insert(Gtk.SeparatorToolItem(), -1)
        self.toolbar.insert(self.save_button, -1)

        self.toolbar.insert(separator, -1)
        self.toolbar.insert(stop_button, -1)

        artwork_paths = self._scan()

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                   Gtk.PolicyType.AUTOMATIC)
        self.set_canvas(scrolled_window)
        scrolled_window.show()

        store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)

        icon_view = Gtk.IconView.new_with_model(store)
        icon_view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        icon_view.connect('selection-changed', self._clipart_selected,
                          store)
        icon_view.set_pixbuf_column(0)
        icon_view.grab_focus()
        scrolled_window.add(icon_view)
        icon_view.show()

        self.set_toolbar_box(self.toolbar_box)
        self.set_canvas(self.canvas)
        self.show_all()

        self._notify()
        GObject.idle_add(fill_clipart_list, store, artwork_paths)

    def _save_to_journal(self, widget):
        if self._selected_image is None:
            return

        basename = os.path.basename(self._selected_image)
        dsobject = datastore.create()
        dsobject.metadata['title'] = basename[:-4]
        dsobject.metadata['icon-color'] = profile.get_color().to_string()
        dsobject.metadata['mime_type'] = MIME_TYPES[basename.split('.')[-1]]
        dsobject.set_file_path(self._selected_image)
        datastore.write(dsobject)
        dsobject.destroy()

        self.save_button.set_sensitive(False)

    def _get_selected_path(self, widget, store):
        try:
            iter_ = store.get_iter(widget.get_selected_items()[0])
            image_path = store.get(iter_, 1)[0]

            return image_path, iter_
        except:
            return None

    def _clipart_selected(self, widget, store):
        selected = self._get_selected_path(widget, store)

        if selected is None:
            self._selected_image = None
            self.save_button.set_sensitive(False)
            return

        image_path, _iter = selected
        iter_ = store.get_iter(widget.get_selected_items()[0])
        image_path = store.get(iter_, 1)[0]

        self._selected_image = image_path
        self.save_button.set_sensitive(True)

    def _scan(self):
        # We need a list of all the .png, .jpg, .gif, and .svg files
        # in ~/Activities. We don't need to search Documents since
        # that is already available through the Journal.
        root_path = os.path.join(os.path.expanduser('~'), 'Activities')
        artwork_paths = []
        for suffix in ['.png', '.jpg', '.gif', '.svg']:
            # Look in ~/Activities/* and ~/Activities/*/*
            file_list = glob.glob(os.path.join(root_path, '*', '*' + suffix))
            for f in file_list:
                artwork_paths.append(f)
            file_list = glob.glob(os.path.join(root_path, '*', '*',
                                               '*' + suffix))
            for f in file_list:
                artwork_paths.append(f)
        return artwork_paths

    def _notify(self):
        alert = NotifyAlert()
        alert.props.title = _('Scanning for clipart')
        msg = _('Please wait.')
        alert.props.msg = msg

        def remove_alert(alert, response_id):
            self.remove_alert(alert)

        alert.connect('response', remove_alert)
        self.add_alert(alert)


def fill_clipart_list(store, artwork_paths):
    '''
    Append images from the artwork_paths to the store.
    '''
    for filepath in artwork_paths:
        pixbuf = None
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                filepath, style.XLARGE_ICON_SIZE,
                style.XLARGE_ICON_SIZE)
        except:
            pass
        else:
            store.append([pixbuf, filepath])
