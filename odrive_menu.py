# Odrive nautilus integration 0.0.88
# Copyright (C) 2022 Casimir Bonnet https://github.com/cazzoo
#
# Odrive nautilus integration is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Odrive nautilus integration is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Odrive nautilus integration; if not, see http://www.gnu.org/licenses
# for more information.

import gettext
import os
import subprocess

from gi.repository import Nautilus, Gtk, GObject, Gio

# Python 2 or 3
try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

# i18n
gettext.textdomain('folder-color-common')
_ = gettext.gettext


class OdriveStatus:
    """Odrive Status Class"""

    def __init__(self):
        # Emblems
        self.EMBLEMS = [
            'emblem-important',
            'emblem-urgent',
            'emblem-favorite',
            'emblem-default',
            'emblem-new'
        ]
        self.I18N_EMBLEMS = {
            'emblem-important': _("Important"),
            'emblem-urgent': _("In Progress"),
            'emblem-favorite': _("Favorite"),
            'emblem-default': _("Finished"),
            'emblem-new': _("New")
        }

    def get_icon(self, icon_name):
        """Get icon name and filename (used for check if exists an icon)"""
        icon_theme = Gtk.IconTheme.get_default()
        icon = icon_theme.lookup_icon(icon_name, 48, 0)
        if icon is not None:
            return {'name': os.path.splitext(os.path.basename(icon.get_filename()))[0],
                    'filename': icon.get_filename()}
        else:
            return {'name': '', 'filename': ''}

    def set_emblem(self, item_path, emblem_name=''):
        """Set emblem"""
        # Restore
        self.restore_emblem(item_path)
        # Set
        if emblem_name:
            emblem = [emblem_name]
            emblems = list(emblem)
            emblems.append(None)  # Needs
            item = Gio.File.new_for_path(item_path)
            info = item.query_info('metadata::emblems', 0, None)
            info.set_attribute_stringv('metadata::emblems', emblems)
            item.set_attributes_from_info(info, 0, None)
        # Refresh
        self._refresh(item_path)

    def restore_emblem(self, item_path):
        """Restore emblem to default"""
        item = Gio.File.new_for_path(item_path)
        info = item.query_info('metadata::emblems', 0, None)
        info.set_attribute('metadata::emblems', Gio.FileAttributeType.INVALID, 0)
        item.set_attributes_from_info(info, 0, None)
        self._refresh(item_path)

    def _refresh(self, item_path):
        """Reload the current file/directory icon"""
        os.utime(item_path, None)


class OdriveMenu(GObject.GObject, Nautilus.MenuProvider):
    """File Browser Menu"""

    def __init__(self, *args, **kwargs):
        GObject.Object.__init__(self)
        super().__init__(*args, **kwargs)
        self.odrivestatus = OdriveStatus()
        self.all_are_directories = True
        self.all_are_files = True

    def get_file_items(self, window, files):
        print("debug get_file_items")
        """Nautilus invokes this function in its startup > Create menu entry"""
        # Checks
        if not self._check_generate_menu(files):
            return

        return self._generate_menu(files)

    def _check_generate_menu(self, items):
        print("debug _check_generate_menu")
        """Menu: Show it?"""
        # No items selected
        if not len(items):
            return False

        self.all_are_directories = True
        self.all_are_files = True
        for item in items:
            # GNOME can only handle files
            if item.get_uri_scheme() != 'file':
                return False

            if item.is_directory():
                self.all_are_files = False
            else:
                self.all_are_directories = False

        # All OK? > Generate menu
        return True

    def _generate_menu(self, items):
        """Menu for [directories|files]: [Color,Custom,Restore,Emblems|Emblems,Restore]"""
        print("debug _generate_menu")
        for item in items:
            print("item: " + item.get_uri_scheme() + ", " + item.get_uri())

        print("Odrive specific menu generation")

        odrive_top_menu = Nautilus.MenuItem(name='Odrive::Top', label=_('Odrive'), icon='folder_color_picker')

        odrive_sub_menu = Nautilus.Menu()
        odrive_top_menu.set_submenu(odrive_sub_menu)

        item_check = Nautilus.MenuItem(name='Odrive::Check', label=_("Check"), icon='refresh')
        item_check.connect('activate', self._check_odrive_status, items)
        odrive_sub_menu.append_item(item_check)

        return odrive_top_menu,

    def _check_odrive_status(self, menu, items):

        item_path = unquote(items[0].get_uri()[7:])

        dialog = Gtk.MessageDialog(
            transient_for=None,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Sync status of [{}]".format(item_path),
        )

        output = self._execute_system_odrive_command(["syncstate", "\"{}\"".format(item_path), "--textonly"])

        dialog.format_secondary_text(output)
        dialog.run()
        dialog.destroy()

    def _execute_system_odrive_command(self, args):
        p = subprocess.run(["/home/caz/.odrive-agent/bin/odrive.py"] + args, capture_output=True)
        output = p.stdout.decode("utf-8")
        return output

    def _check_generate_restore(self, items):
        """Menu: Show restore?"""
        # For each dir, search custom icon or emblem
        for item in items:
            if item.is_gone():
                continue

            # Get metadata file/folder
            item_path = unquote(item.get_uri()[7:])
            item = Gio.File.new_for_path(item_path)
            info = item.query_info('metadata', 0, None)
            # If any metadata > restore menu
            if info.get_attribute_as_string('metadata::custom-icon-name'):
                return True
            if info.get_attribute_as_string('metadata::custom-icon'):
                return True
            if info.get_attribute_as_string('metadata::emblems'):
                return True

        return False

    def _menu_activate_restore_all(self, menu, items):
        """Menu: Clicked restore"""
        for each_item in items:
            if each_item.is_gone():
                continue

            item_path = unquote(each_item.get_uri()[7:])
            self.odrivestatus.restore_emblem(item_path)

    def _menu_activate_restore_emblem(self, menu, items):
        """Menu: Clicked restore"""
        for each_item in items:
            if each_item.is_gone():
                continue

            item_path = unquote(each_item.get_uri()[7:])
            self.odrivestatus.restore_emblem(item_path)

    def _menu_activate_emblem(self, menu, emblem, items):
        """Menu: Clicked emblem"""
        for each_item in items:
            if each_item.is_gone():
                continue

            item_path = unquote(each_item.get_uri()[7:])
            self.odrivestatus.set_emblem(item_path, emblem)
