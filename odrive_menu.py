from __future__ import print_function
from builtins import str
from builtins import object
from future import standard_library
from gi.repository import Gtk
from gi.repository import Nautilus, GObject, Gio
import gettext
import os
import subprocess
import gi
import sys
import re
import types

standard_library.install_aliases()
gi.require_version('Nautilus', '3.0')
gi.require_version("Gtk", "3.0")

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

try:
    from urllib.parse import urlparse, unquote
    from urllib.request import url2pathname
except ImportError:
    # backwards compatibility
    from urllib.parse import urlparse
    from urllib.parse import unquote
    from urllib.request import url2pathname

# Python 2 or 3
try:
    from urllib.parse import unquote
except ImportError:
    from urllib.parse import unquote

try:
    from subprocess import CompletedProcess
except ImportError:
    # Python 2
    class CompletedProcess(object):

        def __init__(self, args, return_code, stdout=None, stderr=None):
            self.args = args
            self.return_code = return_code
            self.stdout = stdout
            self.stderr = stderr

        def check_return_code(self):
            if self.return_code != 0:
                err = subprocess.CalledProcessError(self.return_code, self.args, output=self.stdout)
                raise err
            return self.return_code


    def sp_run(*popenargs, **kwargs):
        command_input = kwargs.pop("input", None)
        capture_output = kwargs.pop("capture_output", False)
        check = kwargs.pop("handle", False)
        if command_input is not None:
            if 'stdin' in kwargs:
                raise ValueError('stdin and input command_arguments may not both be used.')
            kwargs['stdin'] = subprocess.PIPE

        if capture_output:
            if kwargs.get('stdout') is not None or kwargs.get('stderr') is not None:
                raise ValueError('stdout and stderr command_arguments may not be used '
                                 'with capture_output.')
            kwargs['stdout'] = subprocess.PIPE
            kwargs['stderr'] = subprocess.PIPE

        process = subprocess.Popen(*popenargs, **kwargs)
        try:
            outs, errs = process.communicate(command_input)
        except:
            process.kill()
            process.wait()
            raise
        return_code = process.poll()
        if check and return_code:
            raise subprocess.CalledProcessError(return_code, popenargs, output=outs)
        return CompletedProcess(popenargs, return_code, stdout=outs, stderr=errs)


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


def uri_to_path(uri):
    parsed = urlparse(uri)
    host = "{0}{0}{mnt}{0}".format(os.path.sep, mnt=parsed.netloc)
    return os.path.normpath(
        os.path.join(host, url2pathname(unquote(parsed.path)))
    )


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


class MountPathWindow(Gtk.Window):
    def __init__(self, caller):
        super(MountPathWindow, self).__init__(title="Mount remote location")

        self.set_default_size(150, 100)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        label_local_path = Gtk.Label(label="Selected local path:\n{}".format(caller.localPath))
        vbox.pack_start(label_local_path, True, True, 0)
        self.label = Gtk.Label(
            label="Please enter remote path for the mount point.\n ex: /Google Drive/Pictures or just / for odrive root")
        vbox.pack_start(self.label, True, True, 0)

        self.entry = Gtk.Entry()
        self.entry.set_text("")
        vbox.pack_start(self.entry, True, True, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vbox.pack_end(hbox, True, True, 0)

        button1 = Gtk.Button(label="Cancel")
        button1.connect("clicked", self.on_cancel_clicked, caller)
        hbox.pack_start(button1, True, True, 0)

        button2 = Gtk.Button(label="Ok")
        button2.connect("clicked", self.on_confirm_clicked, caller)
        hbox.pack_start(button2, True, True, 0)

    def on_cancel_clicked(self, widget, caller):
        caller.windowReturnObject.action = "Cancel"
        self.destroy()

    def on_confirm_clicked(self, widget, caller):
        print("value from field: " + self.entry.get_text())
        caller.windowReturnObject.action = "Confirm"
        caller.windowReturnObject.value = self.entry.get_text()
        self.destroy()


class FolderSyncOptionsWindow(Gtk.Window):
    def __init__(self, caller):
        super(FolderSyncOptionsWindow, self).__init__(title="Folder sync options")

        self.set_default_size(300, 200)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        hbox_recursive = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_recursive = Gtk.Label.new(_("Sync all sub-folders."))
        self.chk_recursiveSync = Gtk.CheckButton.new_with_mnemonic(_("Recursive"))
        self.chk_recursiveSync.connect("toggled", self.on_chk_recursive_toggled)
        hbox_recursive.pack_start(lbl_recursive, True, True, 0)
        hbox_recursive.pack_start(self.chk_recursiveSync, True, True, 0)
        vbox.pack_start(hbox_recursive, True, True, 0)

        hbox_nodownload = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl_nodownload = Gtk.Label.new(_("Do not download files, just placeholders. (to use in conjunction with \"Recursive\""))
        self.chk_nodownloadSync = Gtk.CheckButton.new_with_mnemonic(_("No download"))
        self.chk_nodownloadSync.set_sensitive(False)
        hbox_nodownload.pack_start(lbl_nodownload, True, True, 0)
        hbox_nodownload.pack_start(self.chk_nodownloadSync, True, True, 0)
        vbox.pack_start(hbox_nodownload, True, True, 0)

        hbox_btn = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vbox.pack_end(hbox_btn, True, True, 0)

        btn_cancel = Gtk.Button(label=_("Cancel"))
        btn_cancel.connect("clicked", self.on_cancel_clicked, caller)
        hbox_btn.pack_start(btn_cancel, True, True, 0)

        btn_confirm = Gtk.Button(label=_("Confirm"))
        btn_confirm.connect("clicked", self.on_confirm_clicked, caller)
        hbox_btn.pack_start(btn_confirm, True, True, 0)

    def on_chk_recursive_toggled(self, widget):
        self.chk_nodownloadSync.set_sensitive(self.chk_recursiveSync.get_active())

    def on_cancel_clicked(self, widget, caller):
        caller.windowReturnObject.action = "Cancel"
        self.destroy()

    def on_confirm_clicked(self, widget, caller):
        caller.windowReturnObject.action = "Confirm"
        caller.windowReturnObject.value = {
            "recursive": str(self.chk_recursiveSync.get_active()),
            "nodownload": str(self.chk_nodownloadSync.get_active())
        }
        self.destroy()


class OdriveStatus(object):
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
        print(sys.version)
        GObject.Object.__init__(self)
        super(OdriveMenu, self).__init__(*args, **kwargs)
        self.odrivestatus = OdriveStatus()
        self.all_are_directories = True
        self.all_are_files = True
        self.windowReturnObject = types.SimpleNamespace()
        self.localPath = ""

    def get_file_items(self, window, files):
        if not odriveClientPath:
            odrive_menu = Nautilus.MenuItem(
                name='Odrive::Check',
                label=_("Odrive: No client found"),
                tip=_("Unable to find odrive client"),
                sensitive=False
            )
            return odrive_menu,

        # Is agent running?
        # Is activated?

        if not self._check_generate_menu(files):
            return

        return self._generate_menu(files)

    def _selected_files_in_mounted(self, items):
        all_selected_in_mounted_path = False

        odrive_mounts = self._odrive_get_mounts()

        # only checking first item, since we may select multiple items but all in same folder
        path = uri_to_path(items[0].get_uri())

        print("item path: " + path)
        for mount in odrive_mounts:
            print("mount point: " + mount)

            all_selected_in_mounted_path = mount in path
            print("aaaa: " + str(all_selected_in_mounted_path))
            print(all_selected_in_mounted_path)
            if all_selected_in_mounted_path:
                print(("selected file is in mount [{}]", mount))
                break

        return all_selected_in_mounted_path

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

        return True

    def _generate_menu(self, items):
        menu_items = []

        # Is selected file(s) part of any odrive mounts?
        if not self._selected_files_in_mounted(items):
            # If we selected only one item
            if len(items) == 1:
                if items[0].is_directory():
                    # Propose to mount folder
                    item_mount = Nautilus.MenuItem(name='Odrive::Mount', label=_("Mount"), icon='refresh')
                    item_mount.connect('activate', self._odrive_mount, items[0])
                    menu_items.append(item_mount)
            else:
                return False
        else:
            # Propose to unmount
            # If we selected only one item
            if len(items) == 1:
                if items[0].is_directory():
                    item_unmount = Nautilus.MenuItem(name='Odrive::Unmount', label=_("Unmount"), icon='refresh')
                    item_unmount.connect('activate', self._odrive_unmount, items[0])
                    menu_items.append(item_unmount)

        # If we selected only one item
        can_sync = False
        can_unsync = False
        for item in items:
            filename, file_extension = os.path.splitext(item.get_uri())
            print("for loop item filename: " + filename)
            if file_extension == ".cloudf" or file_extension == ".cloud":
                if not can_sync:
                    can_sync = True
                continue
            else:
                if not can_unsync:
                    can_unsync = True
                continue

        print("can_sync: " + str(can_sync))
        print("can_unsync: " + str(can_unsync))

        if can_sync:
            item_sync = Nautilus.MenuItem(name='Odrive::Sync', label=_("Sync"), icon='refresh')
            item_sync.connect('activate', self._odrive_sync, items, False)
            menu_items.append(item_sync)

            item_sync_options = Nautilus.MenuItem(name='Odrive::Sync_With_Options', label=_("Sync..."), icon='refresh')
            item_sync_options.connect('activate', self._odrive_sync, items, True)
            menu_items.append(item_sync_options)

        if can_unsync:
            item_unsync = Nautilus.MenuItem(name='Odrive::Unsync', label=_("Unsync"), icon='refresh')
            item_unsync.connect('activate', self._odrive_unsync, items)
            menu_items.append(item_unsync)

        for item in items:
            filename, file_extension = os.path.splitext(item.get_uri())
            if item.is_directory():
                print("item: dir, " + item.get_uri())
            else:
                print("item: " + item.get_uri_scheme() + ", " + item.get_uri() + ", ext: " + file_extension)

        odrive_top_menu = Nautilus.MenuItem(name='Odrive::Top', label=_('Odrive'), icon='folder_color_picker')

        odrive_sub_menu = Nautilus.Menu()
        odrive_top_menu.set_submenu(odrive_sub_menu)

        item_syncstate_selected = Nautilus.MenuItem(name='Odrive::SyncState', label=_("Sync State (selected)"),
                                                    icon='refresh')
        item_syncstate_selected.connect('activate', self._check_odrive_syncState, items, False)
        item_syncstate_children = Nautilus.MenuItem(name='Odrive::SyncState', label=_("Sync State (children)"),
                                                    icon='refresh')
        item_syncstate_children.connect('activate', self._check_odrive_syncState, items, True)
        item_refresh = Nautilus.MenuItem(name='Odrive::Refresh', label=_("Refresh"), icon='refresh')
        item_refresh.connect('activate', self._check_odrive_syncState, items)

        item_show = Nautilus.MenuItem(name='Odrive::Show', label=_("Show gtk window"), icon='refresh')
        item_show.connect('activate', self._show_window)
        item_show_glade = Nautilus.MenuItem(name='Odrive::ShowGlade', label=_("Show Glade gtk window"), icon='refresh')
        item_show_glade.connect('activate', self._show_glade_window)
        odrive_sub_menu.append_item(item_syncstate_selected)
        odrive_sub_menu.append_item(item_syncstate_children)
        odrive_sub_menu.append_item(item_show)
        odrive_sub_menu.append_item(item_show_glade)
        for menu_item in menu_items:
            odrive_sub_menu.append_item(menu_item)

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

    def _odrive_mount(self, menu, item):
        item_path = unquote(item.get_uri()[7:])
        self.localPath = item_path

        remote_path_window = MountPathWindow(self)
        remote_path_window.connect("destroy", Gtk.main_quit)
        remote_path_window.show_all()
        Gtk.main()

        if self.windowReturnObject.action == "Confirm":
            # Sanitize user input to ensure there's nothing wrong in the path.
            user_input = self.windowReturnObject.value

            output = self._execute_system_odrive_command(["mount", item_path, user_input])
            print("command output:\n{}".format(output))
            # update icon to "syncing"
            # detach process: while output is empty, wait. otherwise, update icon to "synced"
        else:
            print("Canceled mount")

    def _odrive_unmount(self, menu, item):
        item_path = unquote(item.get_uri()[7:])
        self.localPath = item_path

        output = self._execute_system_odrive_command(["unmount", "\"{}\"".format(item_path)])
        print("command output:\n{}".format(output))
        # reset icon to normal folder

    def _odrive_sync(self, menu, items, prompt_options):

        if prompt_options:
            threshold_select_window = FolderSyncOptionsWindow(self)
            threshold_select_window.connect("destroy", Gtk.main_quit)
            threshold_select_window.show_all()
            Gtk.main()

            if self.windowReturnObject.action is not None and self.windowReturnObject.action == "Confirm":
                recursive = eval(self.windowReturnObject.value.get("recursive"))
                no_download = eval(self.windowReturnObject.value.get("nodownload"))
                # detach process we we don't get nautilus stuck during sync
                self.sync_files(items, recursive, no_download)
                # detach process: while output is empty, wait. otherwise, update icon to "synced"
                # update icon to "syncing"
            else:
                print("Canceled mount")
        else:
            # Do a single sync (default options)
            self.sync_files(items, False, False)

    def sync_files(self, items, recursive, no_download):
        for item in items:
            item_path = unquote(item.get_uri()[7:])
            filename, file_extension = os.path.splitext(item.get_uri())
            if file_extension == ".cloudf" or file_extension == ".cloud":
                command_arguments = ["sync", "\"{}\"".format(item_path)]
                if recursive:
                    command_arguments.append("--recursive")
                if no_download:
                    command_arguments.append("--nodownload")
                output = self._execute_system_odrive_command(command_arguments)
                print(output)

    def _odrive_unsync(self, menu, items):
        for item in items:
            item_path = unquote(item.get_uri()[7:])
            filename, file_extension = os.path.splitext(item.get_uri())
            if file_extension != ".cloudf" or file_extension != ".cloud":
                output = self._execute_system_odrive_command(["unsync", "\"{}\"".format(item_path)])
                print(output)
                # update icon to "un-syncing"
                # detach process: while output is empty, wait. otherwise, update icon to "unsynced"

    def _odrive_get_mounts(self):
        output = self._execute_system_odrive_command(["status", "--mounts"])
        regex = r"^(.+\/\w+).*"
        mounts = []
        for line in output.splitlines():
            result = re.search(regex, line)
            if result is not None and result.group(1) is not None:
                mounts.append(result.group(1))
            else:
                continue
        return mounts

    def _check_odrive_syncState(self, menu, items, check_children):
        item_path = unquote(items[0].get_uri()[7:])

        dialog = Gtk.MessageDialog(
            transient_for=None,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Sync status of [{}]{}".format(item_path, ("", " children")[check_children]),
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
        print("odrive args: " + ",".join(args))
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
