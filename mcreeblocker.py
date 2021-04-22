# ################################################################### #
#                                                                     #
#  BigBrotherBot(B3) (www.bigbrotherbot.net)                          #
#  Copyright (C) 2005 Michael "ThorN" Thornton                        #
#                                                                     #
#  This program is free software; you can redistribute it and/or      #
#  modify it under the terms of the GNU General Public License        #
#  as published by the Free Software Foundation; either version 2     #
#  of the License, or (at your option) any later version.             #
#                                                                     #
#  This program is distributed in the hope that it will be useful,    #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of     #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the       #
#  GNU General Public License for more details.                       #
#                                                                     #
#  You should have received a copy of the GNU General Public License  #
#  along with this program; if not, write to the Free Software        #
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA      #
#  02110-1301, USA.                                                   #
#                                                                     #
# ################################################################### #

__author__ = 'donna30'
__version__ = '1.0' # Release

import b3
import b3.events
import b3.plugin

from threading import Timer

class McreeblockerPlugin(b3.plugin.Plugin):

    requiresConfigFile = False
    requiresPlugins = ['geolocation']
    
    def onStartup(self):

        self._adminPlugin = self.console.getPlugin('admin')

        if not self._adminPlugin:
            self.error('Could not find admin plugin')
            return
 
        # Registering Commands
        self._adminPlugin.registerCommand(self, 'unlockplayer', 20, self.cmd_unlockPlayer)
        self._adminPlugin.registerCommand(self, 'lockplayer', 20, self.cmd_lockPlayer)

        # Registering Events
        self.registerEvent('EVT_CLIENT_GEOLOCATION_SUCCESS', self.onAuthed)
        self.registerEvent(self.console.getEventID('EVT_CLIENT_JOIN'), self.onChange)


    ###################
    #      Events     #
    ###################

    # onAuthed
    def onAuthed(self, event):
        client = event.client
        if client.bot:
            # We don't need to check bots
            return
        
        # Checking if the clients name is mcree
        self.checkName(client)

        blockstatus = self.checkBlockedStatus(client)
        if blockstatus:
            # This client has been checked already and should be blocked right away.
            self.console.write('forceteam %s spec lock' % client.cid)
            self.announceToClient(client)
            t = Timer(120, self.announceToClient, (client, ))
            t.start()
            return

        allowstatus = self.checkAllowedStatus(client)
        if allowstatus:
            # Client is allowed to play, just return here.
            return

        # Checking now if the client is connecting from Tel Aviv, Israel and making sure he has less than 25 connections
        # Note: It is unlikely that he will figure out that more than 25 connections will bypass this.
        if (client.location.country == "Israel") and (client.location.city == "Tel Aviv") and (client.connections <= 25):
            # Locking the player as a spectator
            self.console.write('forceteam %s spec lock' % client.cid)
            # Announcing that he is locked as a spectator and should contact an Admin in order to play.
            # This will be done right away as well as every 2 minutes.
            self.announceToClient(client)
            t = Timer(120, self.announceToClient, (client, ))
            t.start()

    # onChange
    def onChange(self, event):
        client = event.client
        # Client is switching a team, lock him as a spectator if he's not allowed to play
        val = client.var(self, 'speclocked').value
        if val:
            self.console.write('forceteam %s spec' % client.cid)

    ###################
    #    Commands     #
    ###################

    # cmd_unlockPlayer
    def cmd_unlockPlayer(self, data, client, cmd=None):
        if not data:
            client.message('^2!unlockplayer ^5<client>')
            return

        handler = self._adminPlugin.parseUserCmd(data)
        sclient = self._adminPlugin.findClientPrompt(handler[0], client)
        if not sclient:
            client.message('^3No client found matching your request.')
            return

        cursor = self.console.storage.query('SELECT * FROM BlockedPlayers WHERE iduser = %s' % sclient.id)
        if cursor.rowcount == 0:
            # Client is not in the blocking list, insert him into the pass list instead
            cursor.close()
            self.console.storage.query('INSERT INTO AllowedPlayers (iduser, name) VALUES (%s , \'%s\')' % (sclient.id, sclient.name))
            client.message('^2Allowing ^5%s ^3to play again.' % sclient.name)
            return

        # Client is in the blocking list, remove him and insert him into the pass list
        cursor = self.console.storage.query('DELETE FROM BlockedPlayers WHERE iduser = %s' % sclient.id)
        cursor.close()
        self.console.storage.query('INSERT INTO AllowedPlayers (iduser, name) VALUES (%s , \'%s\')' % (sclient.id, sclient.name))
        client.message('^2Allowing ^5%s ^3to play again.' % sclient.name)

        try:
            # Trying to force the client into a team
            sclient.message('^2You may now play again.')
            self.console.write('forceteam %s r' % sclient.cid)
            client.setvar(self, 'speclocked', False)
        except:
            # Sclient is not connected, just return
            return

    # cmd_lockPlayer
    def cmd_lockPlayer(self, data, client, cmd=None):
        if not data:
            client.message('^2!lockplayer ^5<client>')
            return

        handler = self._adminPlugin.parseUserCmd(data)
        sclient = self._adminPlugin.findClientPrompt(handler[0], client)
        if not sclient:
            client.message('^3No client found matching your request.')
            return

        cursor = self.console.storage.query('SELECT * FROM AllowedPlayers WHERE iduser = %s' % sclient.id)
        if cursor.rowcount == 0:
            # Client is not in the allowed list, insert him into the block list instead
            cursor.close()
            self.console.storage.query('INSERT INTO BlockedPlayers (iduser, name) VALUES (%s , \'%s\')' % (sclient.id, sclient.name))
            try:
                # Trying to force the client as a spectator and lock him there
                sclient.message('^1You are not allowed to play anymore.')
                self.console.write('forceteam %s spec lock' % sclient.cid)
                return

            except:
                # Sclient is not connected, just return
                return

        # Client is in the allowed list, remove him and insert him into the block list
        cursor = self.console.storage.query('DELETE FROM AllowedPlayers WHERE iduser = %s' % sclient.id)
        cursor.close()
        self.console.storage.query('INSERT INTO BlockedPlayers (iduser, name) VALUES (%s , \'%s\')' % (sclient.id, sclient.name))
        client.message('^1Blocking ^5%s ^3from playing.')

        try:
            # Trying to force the client as a spectator and lock him there
            sclient.message('^1You are not allowed to play anymore.')
            self.console.write('forceteam %s spec lock' % sclient.cid)
            client.setvar(self, 'speclocked', True)
 
        except:
            # Sclient is not connected, just return
            return


    ###################
    # Other Functions #
    ###################

    # announceToClient
    def announceToClient(self, client):
        if not client:
            return
        client.message('^3You\'re ^1LOCKED ^3as a spectator!')
        client.message('^3Contact an ^2Admin ^3 to verify yourself')
        client.message('^3Alraja\' alaitisal bimaswuwl ^2liltahaquq ^3min nafsak')
        t = Timer(120, self.announceToClient, (client, ))
        t.start()

    # checkBlockedStatus
    def checkBlockedStatus(self, client):
        cursor = self.console.storage.query('SELECT * FROM BlockedPlayers WHERE iduser = %s' % client.id)
        if cursor.rowcount == 0:
            cursor.close()
            return False
        cursor.close()
        client.setvar(self, 'speclocked', True)
        return True

    # checkAllowedStatus
    def checkAllowedStatus(self, client):
        cursor = self.console.storage.query('SELECT * FROM AllowedPlayers WHERE iduser = %s' % client.id)
        if cursor.rowcount == 0:
            cursor.close()
            return False
        cursor.close()
        client.setvar(self, 'speclocked', False)
        return True

    def checkName(self, client):
        if client.name == "mcree":
            client.setvar(self, 'speclocked', True)
            self.console.write('forceteam %s spec lock' % client.cid)