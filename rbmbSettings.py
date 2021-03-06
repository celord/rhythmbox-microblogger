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
__version__='0.5.2'

import base64
import gconf
import httplib2

KEYS={
    'version'     :'/apps/rhythmbox/plugins/%s/version'      % __name__,
    'template'    :'/apps/rhythmbox/plugins/%s/template'     % __name__,
    'progress'    :'/apps/rhythmbox/plugins/%s/progress'     % __name__,
    'a_list'      :'/apps/rhythmbox/plugins/%s/accounts'     % __name__,
    'a'           :'/apps/rhythmbox/plugins/%s/account/'     % __name__,
    'proxy'       :'/apps/rhythmbox/plugins/%s/proxy'        % __name__,
    'proxy_server':'/apps/rhythmbox/plugins/%s/proxy_server' % __name__,
    'proxy_port'  :'/apps/rhythmbox/plugins/%s/proxy_port'   % __name__,
}

DEFAULT={
    'template'    :'[Rhythmbox] {title} by #{artist} from #{album}',
    'a_list'      :[],
    'progress'    :True,
    'proxy'       :'none',
    'proxy_server':'127.0.0.1',
    'proxy_port'  :8080,
}

class Settings:
    def __init__(self):
        #self._remove_conf(None)
        self._conf=self._read_conf()
        if self._conf is None:
            self._conf=self._create_conf()
        
    def __del__(self):
        del self._conf
        
    def _read_conf(self):
        conf={}

        client=gconf.client_get_default()
        if client.get_string(KEYS['version'])==None:
            return None
        
        ver=client.get_string(KEYS['version'])

        ver=ver.split('.')
        ver[0], ver[1], ver[2]=int(ver[0]), int(ver[1]), int(ver[2])
        if ver[1]<5:
            self._remove_conf(None)
            return None

        if ver[0]==0:
            if ver[1]==5:
                if ver[2]==0:
                    client.set_string(KEYS['template'], DEFAULT['template'])
                if ver[2]<=1:
                    client.set_bool(KEYS['progress'], DEFAULT['progress'])
                    client.set_string(KEYS['proxy'], DEFAULT['proxy'])
                    client.set_string(KEYS['proxy_server'], DEFAULT['proxy_server'])
                    client.set_int(KEYS['proxy_port'], DEFAULT['proxy_port'])

        
        client.set_string(KEYS['version'], __version__)
        
        conf['template']    =client.get_string(KEYS['template'])
        conf['proxy']       =client.get_string(KEYS['proxy'])
        conf['proxy_server']=client.get_string(KEYS['proxy_server'])
        conf['progress']    =client.get_bool  (KEYS['progress'])
        conf['proxy_port']  =client.get_int(KEYS['proxy_port'])
        conf['a_list']      =client.get_list  (KEYS['a_list'], gconf.VALUE_STRING)
        
        conf['a']={}
        
        for alias in conf['a_list']:
            conf['a'][alias]={}
            
            ad=KEYS['a']+alias+'/'
        
            conf['a'][alias]['type']=client.get_string(ad + 'type')
            conf['a'][alias]['alias']=client.get_string(ad + 'alias')
            conf['a'][alias]['token_key']=client.get_string(ad + 'token_key')
            conf['a'][alias]['token_secret']=client.get_string(ad + 'token_secret')
            conf['a'][alias]['url']=client.get_string(ad + 'url')
            conf['a'][alias]['maxlen']=client.get_int(ad + 'maxlen')
        
        return conf
    
    def update_conf(self, text, val):
        client=gconf.client_get_default()

        if text=='progress':
            client.set_bool(KEYS['progress'], val)
        elif text in ('proxy', 'proxy_server'):
            client.set_string(KEYS[text], val)
        elif text=='proxy_port':
            client.set_int(KEYS[text], val)
        elif text=='template':
            if len(val)==0:
                val=DEFAULT['template']
            client.set_string(KEYS['template'], val)
        self._conf[text]=val

    def _create_conf(self):
        client=gconf.client_get_default()
        
        client.set_string(KEYS['version'], __version__)
        client.set_string(KEYS['template'], DEFAULT['template'])
        client.set_bool  (KEYS['progress'], DEFAULT['progress'])
        client.set_list  (KEYS['a_list'], gconf.VALUE_STRING, DEFAULT['a_list'])

        return DEFAULT
    
    def remove_account(self, alias):
        self._conf['a_list'].remove(alias)
        del self._conf['a'][alias]

        self._remove_conf(alias)

        client=gconf.client_get_default()
        client.set_list(KEYS['a_list'], gconf.VALUE_STRING, self._conf['a_list'])
            
    def _remove_conf(self, key):
        client=gconf.client_get_default()
        if key==None:
            add='/apps/rhythmbox/plugins/%s' % __name__
        else:
            add=KEYS['a'] + str(key)
        client.recursive_unset(add, gconf.UNSET_INCLUDING_SCHEMA_NAMES)
        client.remove_dir(add)

        if key==None:
            for i in range(100):
                client.remove_dir(add)
                
    def add_account(self,
                    type,
                    alias,
                    token,
                    token_secret,
                    url,
                    maxlen):
        
        self._conf['a_list'].append(alias)
        
        ad=KEYS['a']+alias+'/'
        
        client=gconf.client_get_default()
        client.set_string(ad + 'type'        , type)
        client.set_string(ad + 'alias'       , alias)
        client.set_string(ad + 'token_key'   , token)
        client.set_string(ad + 'token_secret', token_secret)
        client.set_string(ad + 'url'         , url)
        client.set_int   (ad + 'maxlen'      , maxlen)
        client.set_list  (KEYS['a_list'], gconf.VALUE_STRING, self._conf['a_list'])
        
        self.__init__()

    def get_conf(self, key, alias='object'):
        # a means account
        if key=='a':
            return self._conf['a'][alias]
        elif key=='proxy' and alias=='object':
            return self._get_proxy_configs()
        return self._conf[key]

    def _get_proxy_configs(self):
        try:
            import socks
            proxy=self._conf['proxy']
            if proxy=='none':
                return None
            if proxy=='socks5':
                socks=socks.PROXY_TYPE_SOCKS5
            elif proxy=='socks4':
                socks=socks.PROXY_TYPE_SOCKS4
            else:
                socks=socks.PROXY_TYPE_HTTP

            return httplib2.ProxyInfo(proxy_type=socks,
                                      proxy_host=self._conf['proxy_server'],
                                      proxy_port=self._conf['proxy_port'])
            return None
        except ImportError:
            return None
