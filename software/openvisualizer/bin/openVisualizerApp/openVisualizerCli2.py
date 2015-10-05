#!/usr/bin/python
# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import sys
import os
import traceback
import types

if __name__=="__main__":
    # Update pythonpath if running in in-tree development mode
    basedir  = os.path.dirname(__file__)
    confFile = os.path.join(basedir, "openvisualizer.conf")
    if os.path.exists(confFile):
        import pathHelper
        pathHelper.updatePath()

import logging
log = logging.getLogger('openVisualizerCli')

try:
    from openvisualizer.moteState import moteState
except ImportError:
    # Debug failed lookup on first library import
    print 'ImportError: cannot find openvisualizer.moteState module'
    print 'sys.path:\n\t{0}'.format('\n\t'.join(str(p) for p in sys.path))

from   cmd         import Cmd
import openVisualizerApp
import openvisualizer.openvisualizer_utils as u


class OpenVisualizerCli2(Cmd):
    """Interactive command line to monitor and manage the OpenVisualizer
    application. 
    
    For help, uses 'help_xxx'-named functions. Each function must return
    a 2-tuple with the name of the command and a description. The description
    itself may be a tuple where each element is an output line. The first 
    element is a summary, and subsequent elements provide details. See 
    help_cli() for an example.
    
    Attributes:
       :motes:      List of connected motes
       :activeMote: User-selected mote. Used as an implict target for commands
                    so the user doesn't need to enter the mote ID for every
                    command.
       :link:       Dictionary of links to remote motes from the active 
                    mote, where the key is the address of the remote.
    """
        
    def __init__(self,app):
        log.info('Creating OpenVisualizerCli2')
        
        # store params
        self.app                    = app
        
        Cmd.__init__(self)
        self.prompt     = '> '
        self.intro      = '\nOpenVisualizer CLI\n\n\'help [cmd]\' for command list'
        self.motes      = [mote(moteState) for moteState in self.app.moteStates]
        self.activeMote = None
        self.links      = {}
        # Must turn off to avoid DAO messages, which may be frequent.
        self.app.rpl.showsInfoOnStdout = False
        
    #======================== public ==========================================
    
    def onecmd(self, line):
        """Extend to print traceback."""
        try:
            return Cmd.onecmd(self, line)
        except:
            tb = traceback.format_exc()
            self.stdout.write('Command failed\n')
            self.stdout.write(tb)

    def emptyline(self):
        """Override to do nothing rather than repeat the last command, which
        is counter-intuitive.
        """
        pass
    
    #======================== private =========================================
                        
    def _getDisplayId(self, mote):
        """Returns a short ID for a mote, for display on the terminal."""
        id = mote.get16bHexAddr()
        if id == mote.UNKNOWN_ADDR:
            id = '<' + mote.getSerialAddr() + '>'
        return id
        
    def _updateLinks(self):
        """Updates the contents for the 'links' attribute, for the active 
        mote, from the moteState neighbors data.
        """
        self.links = {}
        try:
            nbrs = self.activeMote.ms.getStateElem(moteState.moteState.ST_NEIGHBORS).data
            for row in nbrs:
                if row.data:
                    nbr  = row.data[0]
                    addr = nbr['addr']
                    if addr and addr.addr:
                        addrStr = ''.join(["%.2x" % b for b in addr.addr[-2:]])
                        self.links[addrStr] = nbr
            log.info('Found {0} links for mote {1}'.format(len(self.links), 
                                                           self.activeMote.get16bHexAddr()))
        except ValueError:
            log.exception('ValueError when reading neighbor list')

    #===== callbacks
    
    def do_mote(self, arg):
        args = arg.split()
        
        if len(args) == 1 and args[0] == "list":
            if self.motes:
                self.stdout.write('\'*\' = DAG root\n')
                for mote in self.motes:
                    self.stdout.write('{0}{1}\n'.format('* ' if mote.isDagRoot() else '  ',
                                                        self._getDisplayId(mote)))
            else:
                self.stdout.write('No connected motes\n')

        elif len(args) == 1 and args[0] == "root":
            if self.activeMote:
                if not self.activeMote.isDagRoot():
                    self.activeMote.ms.triggerAction(moteState.moteState.TRIGGER_DAGROOT)
                    self.prompt = self._getDisplayId(self.activeMote) + '> '
                else:
                    self.stdout.write('No action; mote already is DAG root\n')
            else:
                self.stdout.write('No action; must first select mote\n')
                
        elif len(args) == 2 and args[0] == "set":
            foundId = False
            for mote in self.motes:
                if args[1] == mote.get16bHexAddr() and mote.isUsable():
                    self.activeMote = mote
                    foundId         = True
                    self.prompt     = self._getDisplayId(mote) + '> '
                    self._updateLinks()
                    break
            if not foundId:
                self.stdout.write('mote-id not found or not usable\n')

        else:
            self.do_help('mote')
        
    def help_mote(self):
        return("mote", ("Mote list, active mote, and mote settings",
              "mote list          -- List connected motes",
              "mote root          -- Make the active mote the DAG root",
              "mote set <mote-id> -- Set the active connected mote"))
              
    def do_link(self, arg):
        args = arg.split()

        if len(args) >= 1 and args[0] == "list":
            self._updateLinks()
            if self.links:
                for addr in self.links.keys():
                    self.stdout.write(addr + '\n')
            else:
                self.stdout.write('No links found\n')
            
        elif len(args) == 2 and args[0] == "stats":
            link = self.links[args[1]]
            if link:
                numTx    = link['numTx']
                numTxACK = link['numTxACK']
                par      = (numTxACK / float(numTx)) if numTx > 0 else 0
                
                self.stdout.write('  AllRX  RSS  UniTX  TXack   PAR\n')
                self.stdout.write('  -----  ---  -----  -----  ----\n')
                self.stdout.write('  {0:5d}  {1:3d}  {2:5d}  {3:5d}  {4:4.2f}\n'.format(
                                                                     link['numRx'], 
                                                                     link['rssi'].rssi,
                                                                     numTx,
                                                                     numTxACK,
                                                                     par))
            else:
                self.stdout.write('link not found\n')
        else:
            self.do_help('link')
        
    def help_link(self):
        return("link", ("Link list and stats for a link to the selected mote",
              "link list          -- List linked motes",
              "link stats <remote-id> [frequency]",
              "                   -- Show statistics for the link to mote 'remote-id'.",
              "                      Optionally, update the display every 'frequency' seconds",
              "link stats off",
              "link stats reset",
              "",
              "Legend for stats output:",
              "   AllRX     RSS      UniTX    TXack    PAR  ",
              "  -------  --------  -------  -------  ------",
              "  All RX   RSS for   Unicast  ACKed    TX pkt",
              "  packets  last RX   TX       unicast  ACK   ",
              "           packet    packets  TX pkts  rate  "))
              
    def do_cli(self, arg):
        args = arg.split()
        
        if args and args[0] == "stdout":
            if len(args) == 1:
                self.stdout.write('cli stdout is ' 
                        + ('on\n' if self.app.rpl.showsInfoOnStdout else 'off\n'))
            elif len(args) == 2 and args[1] == 'on':
                self.app.rpl.showsInfoOnStdout = True
            elif len(args) == 2 and args[1] == 'off':
                self.app.rpl.showsInfoOnStdout = False
            else:
                self.do_help('cli')
        else:
            self.do_help('cli')
        
    def help_cli(self):
        return("cli", ("CLI application settings",
              "cli stdout [on|off] -- Enable/Disable messages to stdout from other",
              "                       OpenVisualizer modules"))

    def do_help(self, arg):
        """Lists command name and description from help_xxx() methods.
        Include command details if 'arg' identifies a single command.
        """
        cliNames = self.get_names()
        cliNames.sort()
        if not arg:
            self.stdout.write(' Commands                      Description                                  \n')
            self.stdout.write('----------  ---------------------------------------------------------------\n')
        for name in cliNames:
            if name[:5] != 'help_':
                continue
            if arg and arg != name[5:]:
                continue

            helpFunc = getattr(self, name)
            (cmdName, description) = helpFunc();
            self.stdout.write(cmdName)
            self.stdout.write((12-len(cmdName)) * ' ')
            
            if isinstance(description, str):
                self.stdout.write('{0}\n'.format(description))
            else:
                # Include multiline details if for a single command
                last = len(description) if arg else 1
                for i in range(0, last):
                    self.stdout.write('{0}\n'.format(description[i]))
                    if arg and i == 0:
                        self.stdout.write('\n')
    
    def do_exit(self, arg):
        self.app.close()
        # True means to stop CLI.
        return True
        
    def help_exit(self):
        return ("exit", "Exit OpenVisualizer CLI")

#============================ mote ============================================

class mote(object):
    """Model for a mote. Provides application level semantics missing from
    moteState. Would be appropriate to integrate this class into openVisualizerApp,
    but that is a major change to the application structure.
    """
    UNKNOWN_ADDR = "Unknown"
    
    def __init__(self,moteState):
        self.ms      = moteState
    
    def get16bHexAddr(self):
        """Returns a 2-byte hex string address in the form 'xxxx'."""
        addr = self.ms.getStateElem(moteState.moteState.ST_IDMANAGER).get16bAddr()
        return ''.join(['%02x'%b for b in addr]) if addr else self.UNKNOWN_ADDR
        
    def getSerialAddr(self):
        return self.ms.moteConnector.serialport
        
    def isDagRoot(self):
        """Returns True if this mote is RPL DAG root for the network."""
        return self.ms.getStateElem(moteState.moteState.ST_IDMANAGER).isDAGroot
        
    def isUsable(self):
        """Returns True if mote state indicates we can communicate with it."""
        return self.get16bHexAddr() != self.UNKNOWN_ADDR
        
        
class moteLink(object):
    """A wireless link to a remote mote.
    
    Attributes:
       :linkData:      Dictionary of moteState.StateNeighborsRow data for the link
    """
    
    def __init__(self,linkData):
        self.linkData = linkData
        
    def getHexAddr(self):
        return linkData['addr']
    
    

#============================ main ============================================

if __name__=="__main__":
    app = openVisualizerApp.main()
    cli = OpenVisualizerCli2(app)
    cli.cmdloop()
