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
import gi
import sys

gi.require_version('Nautilus', '3.0')
from gi.repository import Nautilus, GObject, Gio
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

# Python 2 or 3
try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

try:
    from subprocess import CompletedProcess
except ImportError:
    # Python 2
    class CompletedProcess:

        def __init__(self, args, returncode, stdout=None, stderr=None):
            self.args = args
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

        def check_returncode(self):
            if self.returncode != 0:
                err = subprocess.CalledProcessError(self.returncode, self.args, output=self.stdout)
                raise err
            return self.returncode

    def sp_run(*popenargs, **kwargs):
        input = kwargs.pop("input", None)
        capture_output = kwargs.pop("capture_output", False)
        check = kwargs.pop("handle", False)
        if input is not None:
            if 'stdin' in kwargs:
                raise ValueError('stdin and input arguments may not both be used.')
            kwargs['stdin'] = subprocess.PIPE

        if capture_output:
            if kwargs.get('stdout') is not None or kwargs.get('stderr') is not None:
                raise ValueError('stdout and stderr arguments may not be used '
                                'with capture_output.')
            kwargs['stdout'] = subprocess.PIPE
            kwargs['stderr'] = subprocess.PIPE

        process = subprocess.Popen(*popenargs, **kwargs)
        try:
            outs, errs = process.communicate(input)
        except:
            process.kill()
            process.wait()
            raise
        returncode = process.poll()
        if check and returncode:
            raise subprocess.CalledProcessError(returncode, popenargs, output=outs)
        return CompletedProcess(popenargs, returncode, stdout=outs, stderr=errs)

    subprocess.run = sp_run
    # ^ This monkey patch allows it work on Python 2 or 3 the same way

# i18n
gettext.textdomain('odrive-integration-common')
_ = gettext.gettext

def which(file_name):
    for path in os.environ["PATH"].split(os.pathsep):
        full_path = os.path.join(path, file_name)
        if os.path.exists(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return None

odriveClientPath = which("odrive")
current_path = os.path.dirname(os.path.abspath(__file__))

print("current path: " + current_path)

class MyWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Hello World")

        self.button = Gtk.Button(label="Click Here")
        self.button.connect("clicked", self.on_button_clicked)
        self.add(self.button)

    def on_button_clicked(self, widget):
        print("Hello World")

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
    def __init__(self, *args, **kwargs):
        print (sys.version)
        GObject.Object.__init__(self)
        super(OdriveMenu, self).__init__(*args, **kwargs)
        self.odrivestatus = OdriveStatus()
        self.all_are_directories = True
        self.all_are_files = True

    def get_file_items(self, window, files):
        if not odriveClientPath:
            odrive_menu = Nautilus.MenuItem(
                name='Odrive::Check', 
                label=_("Odrive: No client found"), 
                tip=_("Unable to find odrive client"),
                sensitive=False
            )
            return odrive_menu,

        if not self._check_generate_menu(files):
            return

        return self._generate_menu(files)

    def _check_generate_menu(self, items):
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
        for item in items:
            print("item: " + item.get_uri_scheme() + ", " + item.get_uri())

        odrive_top_menu = Nautilus.MenuItem(name='Odrive::Top', label=_('Odrive'), icon='folder_color_picker')

        odrive_sub_menu = Nautilus.Menu()
        odrive_top_menu.set_submenu(odrive_sub_menu)

        item_sync = Nautilus.MenuItem(name='Odrive::Sync', label=_("Sync"), icon='refresh')
        item_sync.connect('activate', self._check_odrive_syncState, items)
        item_unsync = Nautilus.MenuItem(name='Odrive::Unsync', label=_("Unsync"), icon='refresh')
        item_unsync.connect('activate', self._check_odrive_syncState, items)
        item_syncstate_selected = Nautilus.MenuItem(name='Odrive::SyncState', label=_("Sync State (selected)"), icon='refresh')
        item_syncstate_selected.connect('activate', self._check_odrive_syncState, items, False)
        item_syncstate_children = Nautilus.MenuItem(name='Odrive::SyncState', label=_("Sync State (children)"), icon='refresh')
        item_syncstate_children.connect('activate', self._check_odrive_syncState, items, True)
        item_refresh = Nautilus.MenuItem(name='Odrive::Refresh', label=_("Refresh"), icon='refresh')
        item_refresh.connect('activate', self._check_odrive_syncState, items)
        item_mount = Nautilus.MenuItem(name='Odrive::Mount', label=_("Mount"), icon='refresh')
        item_mount.connect('activate', self._check_odrive_syncState, items)
        item_unmount = Nautilus.MenuItem(name='Odrive::Unmount', label=_("Unmount"), icon='refresh')
        item_unmount.connect('activate', self._check_odrive_syncState, items)
        item_show = Nautilus.MenuItem(name='Odrive::Show', label=_("Show gtk window"), icon='refresh')
        item_show.connect('activate', self._show_window)
        item_showGlade = Nautilus.MenuItem(name='Odrive::ShowGlade', label=_("Show Glade gtk window"), icon='refresh')
        item_showGlade.connect('activate', self._show_glade_window)
        odrive_sub_menu.append_item(item_syncstate_selected)
        odrive_sub_menu.append_item(item_syncstate_children)
        odrive_sub_menu.append_item(item_show)
        odrive_sub_menu.append_item(item_showGlade)

        return odrive_top_menu,

    def _show_window(self, menu):
        win = MyWindow()
        win.connect("destroy", Gtk.main_quit)
        win.show_all()
        Gtk.main()
    
    def _on_btn_confirm_released(self, button):
        print("btn_confirm released")

    def _on_btn_cancel_released(self, button):
        print("btn_cancel released")

    def _show_glade_window(self, menu):
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(current_path, 'confirmation.glade'))
        window = builder.get_object('main_window')
        window.connect('delete-event', Gtk.main_quit)

        handlers = {
            'on_btn_confirm_released': self._on_btn_confirm_released,
            'on_btn_cancel_released': self._on_btn_cancel_released
            }
        builder.connect_signals(handlers)

        window.show_all()
        Gtk.main()

    def _check_odrive_syncState(self, menu, items, check_children):

        item_path = unquote(items[0].get_uri()[7:])

        dialog = Gtk.MessageDialog(
            transient_for=None,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Sync status of [{}]{}".format(item_path, (""," children")[check_children]),
        )

        output = self._execute_system_odrive_command(["syncstate", "\"{}\"".format(item_path), "--textonly"])
        filtered_output = ""
        if check_children:
            filtered_output = output.split('\n', 1)[1]
        else:
            filtered_output = output.split('\n', 1)[0]
        dialog.format_secondary_text(filtered_output)
        dialog.run()
        dialog.destroy()

    def _execute_system_odrive_command(self, args):
        p = subprocess.run([odriveClientPath] + args, capture_output=True)
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
