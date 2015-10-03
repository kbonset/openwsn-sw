#!/usr/bin/python
# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import sys
import os
import traceback

if __name__=="__main__":
    # Update pythonpath if running in in-tree development mode
    basedir  = os.path.dirname(__file__)
    confFile = os.path.join(basedir, "openvisualizer.conf")
    if os.path.exists(confFile):
        import pathHelper
        pathHelper.updatePath()

import logging
log = logging.getLogger('openVisualizerCli2')

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
    """
        
    def __init__(self,app):
        log.info('Creating OpenVisualizerCli2')
        
        # store params
        self.app                    = app
        
        Cmd.__init__(self)
        self.prompt     = '> '
        self.intro      = '\nOpenVisualizer CLI\n\n\'help [cmd]\' for command list'
        
    #======================== public ==========================================
    
    def onecmd(self, line):
        """Extend to print traceback."""
        try:
            return Cmd.onecmd(self, line)
        except:
            tb = traceback.format_exc()
            self.stdout.write('Command failed\n')
            self.stdout.write(tb)
    
    #======================== private =========================================

    def _motelist(self):
        """Returns list of 16-bit IDs for connected motes"""
        motelist = []
        for ms in self.app.moteStates:
            addr = ms.getStateElem(moteState.moteState.ST_IDMANAGER).get16bAddr()
            if addr:
                motelist.append( ''.join(['%02x'%b for b in addr]) )
            else:
                motelist.append(ms.moteConnector.serialport)
        return motelist

    #===== callbacks
    
    def do_mote(self, arg):
        if arg == "list":
            motes = self._motelist()
            if motes:
                for mote in self._motelist():
                    self.stdout.write('{0}\n'.format(mote))
            else:
                self.stdout.write('No connected motes\n')
        else:
            self.do_help('mote')
        
    def help_mote(self):
        return("mote", ("Mote list, active mote, and mote settings",
              "mote list          -- List connected motes",
              "mote set <mode-id> -- Set the active connected mote"))

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


#============================ main ============================================

if __name__=="__main__":
    app = openVisualizerApp.main()
    cli = OpenVisualizerCli2(app)
    cli.cmdloop()
