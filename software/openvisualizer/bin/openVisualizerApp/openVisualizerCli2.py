#!/usr/bin/python
# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import sys
import os

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
        
    def __init__(self,app):
        log.info('Creating OpenVisualizerCli2')
        
        # store params
        self.app                    = app
        
        Cmd.__init__(self)
        self.prompt     = '> '
        self.intro      = '\nOpenVisualizer  (\'help\' for commands)'
        
    #======================== public ==========================================
    
    #======================== private =========================================
    
    #===== callbacks

    def do_help(self, arg):
        """Lists command name and description from help_xxx() methods"""
        names = self.get_names()
        names.sort()
        self.stdout.write(' Command                      Description                                  \n')
        self.stdout.write('----------  ---------------------------------------------------------------\n')
        for name in names:
            if name[:5] == 'help_':
                try:
                    helpFunc = getattr(self, name)
                    (cmdName, description) = helpFunc();
                    self.stdout.write(cmdName)
                    self.stdout.write((12-len(cmdName)) * ' ')
                    self.stdout.write('{0}\n'.format(description))
                except AttributeError:
                    pass
    
    def do_exit(self, arg):
        self.app.close()
        return True
        
    def help_exit(self):
        return ("exit","Exit OpenVisualizer CLI")


#============================ main ============================================

if __name__=="__main__":
    app = openVisualizerApp.main()
    cli = OpenVisualizerCli2(app)
    cli.cmdloop()
