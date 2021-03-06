#! /usr/bin/python2
# -*- coding: utf8 -*-
#
# Rhythmbox-Microblogger - <http://github.com/aliva/Rhythmbox-Microblogger>
# Copyright (C) 2010 Ali Vakilzade <ali.vakilzade in Gmail>
#
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
#


__auther__ ='Ali Vakilzade'
__name__   ='rhythmbox-microblogger'
from rbmbSettings import __version__

import gtk
import pynotify
import rb
import rhythmdb
import threading
import urllib
from rbmbConfigDialog import ConfigDialog
from rbmbSettings import Settings
from rbmbSettings import DEFAULT
from rbmbRequest import Post

UI_TOOLBAR='''
<ui>
    <toolbar name='ToolBar'>
        <placeholder name='PluginPlaceholder'>
            <toolitem name='rbmb-toolitem-%s' action='rbmb-action-%s'/>
        </placeholder>
    </toolbar>
</ui>
'''

class microblogger(rb.Plugin):
    ACCOUNT_TYPE=('twitter', 'identica', 'getglue')
    def __init__(self):
        rb.Plugin.__init__(self)

    def activate(self, shell):
        gtk.gdk.threads_init()
        pynotify.init('Rhythmbox')
        
        self.shell=shell
        self.pl=shell.get_property('shell-player')
        self.db=shell.get_property('db')

        
        self.config_dialog=ConfigDialog(self)
        self.settings=Settings()
        self.post=Post(self)
        
        self.get_conf=self.settings.get_conf

        self.uim = shell.get_ui_manager()
                        
        self._register_icons()
        
        self.add_ui()
        self._attach_box()
        
        self.sending=False
        
        threading.Thread(target=self._check_4_update).start()

    def deactivate(self, shell):
        self.remove_ui()
        
        pynotify.uninit()
        
        del self.boxui
        del self.config_dialog
        del self.settings
    
    def create_configure_dialog(self, dialog=None):
        if dialog==None:
            dialog=self.config_dialog.create_main_window()
        return dialog

    def _register_icons(self):
        IconFactory=gtk.IconFactory()
        IconFactory.add_default()

        for account in self.ACCOUNT_TYPE:
            gtk.stock_add([('rbmb-%s' % account, account, 0, 0, '')])
            IconSource=gtk.IconSource()
            IconSet=gtk.IconSet()
            IconSource.set_filename(self.find_file('icon/%s.png' % account))
            IconSet.add_source(IconSource)
            IconFactory.add('rbmb-%s' % account, IconSet)
            
    def add_ui(self):
        self.ui_id=[]
        self.action_groups=[]

        for alias in self.get_conf('a_list'):
            action=gtk.Action('rbmb-action-%s' % alias,
                              alias,
                              'Microblogger plugin',
                              'rbmb-%s' % self.get_conf('a', alias)['type'])
            activate_id = action.connect('activate', self._send_clicked, alias)
            action_group = gtk.ActionGroup('rbmb-actiongroup-%s'% alias)
            action_group.add_action(action)
            self.uim.insert_action_group(action_group, 0)

            self.ui_id.append(self.uim.add_ui_from_string(UI_TOOLBAR % (alias, alias)))
            self.action_groups.append(action_group)

        self.uim.ensure_update()
        
    def remove_ui(self):
        for key in self.ui_id:
            self.uim.remove_ui(key)

        for key in self.action_groups:
            self.uim.remove_action_group(key)

        del self.ui_id
        del self.action_groups

        self.uim.ensure_update()
    
    def _attach_box(self):
        self.boxui=gtk.Builder()
        self.boxui.add_from_file(self.find_file('ui/rbmb-box.ui'))
        self.boxui.connect_signals(self)
        
        box=self.boxui.get_object('general')

        self.shell.add_widget (box, rb.SHELL_UI_LOCATION_MAIN_TOP)
        
        w=self.boxui.get_object('cancel-image')
        w.set_from_stock(gtk.STOCK_CANCEL, gtk.ICON_SIZE_BUTTON)
		
        box.hide_all()
        
    def _send_clicked(self, button, alias):
        if self.sending:
            return
           
        box=self.boxui.get_object('general')
        box.set_sensitive(True)
        box.hide_all()
        
        if not self.pl.get_playing():
            return
     
        self.alias=alias
        
        get=self.boxui.get_object
        
        conf=self.get_conf('a', alias)
        
        self.pl_entry=self.pl.get_playing_entry()

        w=get('type')
        w.set_from_stock('rbmb-'+ conf['type'], gtk.ICON_SIZE_BUTTON)
        
        w=get('alias')
        w.set_text(alias)
        
        w=get('len')
        w.set_text('')
        
        w=get('entry')
        w.set_progress_fraction(0)
        w.set_sensitive(True)
        w.set_text(self.get_conf('template'))
        w.grab_focus()
        
        w=get('send')
        w.set_sensitive(True)

        box.show_all()

        if conf['type']=='getglue':
            w=get('entry')
            w.set_sensitive(False)
            w.set_text('  ')
        
    def _send_thread(self, button):
        self.sending=True
        
        threading.Thread(target=self.post.post,
                         args=(self.boxui,
                               self.artist, self.title, self.album,
                               self.alias, self.get_conf('proxy'))
                         ).start()
        
    def _cancel_clicked(self, button):
        self.sending=False
        
        box=self.boxui.get_object('general')
        box.hide_all()
        
    def _entry_changed(self, entry):
        maxlen=140
        
        len=entry.get_text_length()
        
        label=self.boxui.get_object('len')
        label.set_text('%d' % (maxlen-len))
        
        if self.get_conf('progress'):
            entry.set_progress_fraction(float(len)/maxlen)
        
        send=self.boxui.get_object('send')
        send.set_sensitive(0<len<=maxlen)
        
        text=entry.get_text()
        pl_entry=self.pl_entry
        if pl_entry==None:
            return

        get=self.db.entry_get
        items={
            '{title}' :get(pl_entry, rhythmdb.PROP_TITLE),
            '{genre}' :get(pl_entry, rhythmdb.PROP_GENRE),
            '{artist}':get(pl_entry, rhythmdb.PROP_ARTIST),
            '{album}' :get(pl_entry, rhythmdb.PROP_ALBUM),
            '{rate}'  :get(pl_entry, rhythmdb.PROP_RATING),
            '{year}'  :get(pl_entry, rhythmdb.PROP_YEAR),
            '{pcount}':get(pl_entry, rhythmdb.PROP_PLAY_COUNT),
        }
        self.artist = get(pl_entry, rhythmdb.PROP_ARTIST)
        self.title = get(pl_entry, rhythmdb.PROP_TITLE)
        self.album = get(pl_entry, rhythmdb.PROP_ALBUM)
        del get
        
        for item in items:
            # if has tag
            tmp=str(items[item])
            tmp=self._remove_forbidden_chars(tmp)
            text=text.replace('#'+item, '#'+tmp)

            # if hasn't tag
            text=text.replace(item, str(items[item]))

        entry.set_text(text)

    def _entry_key_press_event(self, entry, event):
        if gtk.gdk.keyval_name(event.keyval)=='Escape':
            self._cancel_clicked(None)

    def _remove_forbidden_chars(self, text):
        chars='!@#$%^&*()-+=\\|/[]{};:\'"<>,? '

        for c in chars:
            text=text.replace(c, '_')

        for c in ('____', '___', '__'):
            text=text.replace(c, '_')

        return text.strip(chars+'_')
    
    def _entry_icon_press(self, entry, pos, event): 
        entry.set_text('')
        
    def _check_4_update(self):        
        print 'Checking for updates...'
        
        try:
            link=urllib.urlopen('https://github.com/downloads/aliva/rhythmbox-microblogger/VERSION')
        except Exception as err:
            print 'Coudn\'t get update info from rbmb'
            return      
        if link.code!=200:
            print 'Coudn\'t get update info from rbmb'
            return
        
        f=link.read()
        link.close()
        
        f=f.split('\n')[0]
        f=f.split('=')
        
        if f[0]!='version':
            print 'Errors in update info file'
            return
        
        f=f[1]
        f=f.split('.')
        f=[int(x) for x in f]
        

        old=False
       
        ver=__version__.split('.')
        ver=[int(x) for x in ver]
        
        if   f[0]>ver[0]:
            old=True
        elif f[0]==ver[0] and f[1]>ver[1]:
            old=True
        elif f[0]==ver[0] and f[1]==ver[1] and f[2]>ver[2]:
            old=True

        if not old:
            return

        notif=pynotify.Notification('Updates available for MicroBlogger Plugin',
                                    'version %d.%d.%d is ready!' % (f[0], f[1], f[2]))
        notif.show()
