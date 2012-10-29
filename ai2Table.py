#!/usr/bin/python
#
# Copyright (C) 2012 Marcelo Belentani de Bianchi
#
# This file is part of aiUtils.
#
# aiUtils is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# aiUtils is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Foobar.  If not, see <http://www.gnu.org/licenses/>.
#

import sys
import os
import re
import datetime
from optparse import OptionParser

try:
    from seiscomp.db.generic.inventory import Inventory as GInventory
    from seiscomp.logs import *
except:
    print >>sys.stderr, "Please use the install.sh script to adjust the seiscomp3 folder."
    sys.exit()

from ai.utils import *
import string

def info(s):
    print >>sys.stdout,s
    sys.stdout.flush()

def notice(s):
    print >>sys.stderr,s
    sys.stderr.flush()

def debug(s):
    print >>sys.stderr,s
    sys.stderr.flush()

def error(s):
    print >>sys.stderr,s
    sys.stderr.flush()


class base(object):
    def __init__(self, pattern = None, when = None):
        self.when = None
        self.pattern = pattern
        self.npat = None
        self.spat = None
        self.lpat = None
        self.cpat = None

        if pattern:
            parts = pattern.split(".")
            if len(parts) >= 1:
                self.npat = re.compile('^'+string.join(pattern.split(".")[0:1],".").replace('.','[.]').replace('*','.+')+'$')
                
            if len(parts) >= 2:
                self.spat = re.compile('^'+string.join(pattern.split(".")[0:2],".").replace('.','[.]').replace('*','.+')+'$')
                
            if len(parts) >= 3:
                self.lpat = re.compile('^'+string.join(pattern.split(".")[0:3],".").replace('.','[.]').replace('*','.+')+'$')
                
            if len(parts) >= 4:
                self.cpat = re.compile('^'+string.join(pattern.split(".")[0:4],".").replace('.','[.]').replace('*','.+')+'$')
                
            if len(parts) >= 5:
                raise Exception("Invalid pattern filter supplied expect something like [GE.*.--.BH*]")
            
        if when and isinstance(when, datetime.datetime):
            self.when = when

    def name(self, ncode = None, scode = None, lcode = None, ccode = None):
        if lcode == "":
            lcode = "--"
        if ccode:
            s = "%s.%s.%s.%s" % (ncode, scode, lcode, ccode)
        elif lcode:
            s = "%s.%s.%s" % (ncode, scode, lcode)
        elif scode:
            s = "%s.%s" % (ncode, scode)
        elif ncode:
            s = "%s" % (ncode)
        
        return s

    def _match(self, code, start, end):
        if self.when:
            if self.when < start:
                return False
            if end and self.when > end:
                return False

        if self.pattern:
            n = len(code.split("."))
    
            if n == 1:
                if self.npat and not self.npat.match(code): return False
            elif n == 2:
                if self.spat and not self.spat.match(code): return False
            elif n == 3:
                if self.lpat and not self.lpat.match(code): return False
            elif n == 4:
                if self.cpat and not self.cpat.match(code): return False
            elif n >= 5:
                raise Exception("Oops, internal error")

        return True
        
    def date(value):
        if value:
            return value.strftime('%Y-%m-%dT%H:%M:%S')
        else:
            return "None"

class coordinate(base):
    def __init__(self, filter = None, when = None):
        base.__init__(self, filter, when)
        
    def run(self, inv):
        for (ncode, nstart, net) in unWrapNSLC(inv.network):
            if not self._match(self.name(ncode), net.start, net.end): continue

            for (scode, sstart, sta) in unWrapNSLC(net.station):
                if not self._match(self.name(ncode, scode), sta.start, sta.end): continue
                info("[S] %-15s %f %f %f" % (self.name(ncode, scode), sta.longitude, sta.latitude, sta.elevation))

                for (lcode, lstart, loc) in unWrapNSLC(sta.sensorLocation):
                    if not self._match(self.name(ncode, scode, lcode), loc.start, loc.end): continue
                    if loc.longitude != sta.longitude or loc.latitude != sta.latitude or loc.elevation != sta.elevation:
                        info("[L] %-15s %f %f %f" % (self.name(ncode, scode, lcode), loc.longitude, loc.latitude, loc.elevation))

class tree(base):
    def __init__(self, filter = None, when = None, mode = "Pretty", extra = None):
        base.__init__(self, filter, when)
        if mode == "Pretty" or mode == "Diff":
            self.mode = mode
        else:
            raise Exception("Invalid Printing mode")
        self.extra = extra
        
    def run(self, inv):
        node = None
        if self.extra:
            (node, variable) = self.extra.split(".")

        for (ncode, nstart, net) in unWrapNSLC(inv.network):
            if not self._match(self.name(ncode), net.start, net.end): continue
            if node == "n": value = getattr(net, variable)
            if self.mode == "Pretty":
                info("%s,%s/%s" %(ncode,net.start, net.end))
            else:
                if node == "n":
                    info("%s,%s/%s %s %s" % (ncode, net.start, net.end, variable, value))
                    continue

            for (scode, sstart, sta) in unWrapNSLC(net.station):
                if not self._match(self.name(ncode, scode), sta.start, sta.end): continue
                if node == "s": value = getattr(sta, variable)
                if self.mode == "Pretty":
                    info("  %s,%s/%s" % (scode,sta.start, sta.end))
                else:
                    if node == "s":
                        info("%s,%s/%s :: %s,%s/%s %s %s" % (ncode, net.start, net.end, scode,sta.start, sta.end, variable, value))
                        continue
    
                for (lcode, lstart, loc) in unWrapNSLC(sta.sensorLocation):
                    if not self._match(self.name(ncode, scode, lcode), loc.start, loc.end): continue
                    if node == "l": value = getattr(loc, variable)
                    if self.mode == "Pretty":
                        info("       %s,%s/%s" % (lcode if lcode != "" else "--",loc.start, loc.end))
                    else:
                        if node == "l":
                            info("%s,%s/%s :: %s,%s/%s :: %s,%s/%s %s %s" % (ncode, net.start, net.end, scode,sta.start, sta.end, lcode if lcode != "" else "--",loc.start, loc.end, variable, value))
                            continue

                    for (ccode, cstart, cha) in unWrapNSLC(loc.stream):
                        if not self._match(self.name(ncode, scode, lcode, ccode), cha.start, cha.end): continue
                        if node == "c": value = getattr(cha, variable)
                        if self.mode == "Diff":
                            if self.extra:
                                info("%s,%s/%s :: %s,%s/%s :: %s,%s/%s :: %s,%s/%s %s %s" % (ncode,net.start, net.end,
                                                                   scode,sta.start, sta.end,
                                                                   lcode if lcode != "" else "--",loc.start, loc.end,
                                                                   ccode, cha.start, cha.end, variable, value))
                            else:
                                info("%s,%s/%s :: %s,%s/%s :: %s,%s/%s :: %s,%s/%s" % (ncode,net.start, net.end,
                                                                   scode,sta.start, sta.end,
                                                                   lcode if lcode != "" else "--",loc.start, loc.end,
                                                                   ccode, cha.start, cha.end))
                        elif self.mode == "Pretty":
                            info("         %s,%s/%s" % (ccode, cha.start, cha.end))
                        else:
                            raise Exception("Invalid printing mode.")

class gain(base):
    def __init__(self, filter = None, when = None):
        base.__init__(self, filter, when)

    def run(self, inv):
        for (ncode, nstart, net) in unWrapNSLC(inv.network):
            if not self._match(self.name(ncode), net.start, net.end): continue
            for (scode, sstart, sta) in unWrapNSLC(net.station):
                if not self._match(self.name(ncode, scode), sta.start, sta.end): continue
                for (lcode, lstart, loc) in unWrapNSLC(sta.sensorLocation):
                    if not self._match(self.name(ncode, scode, lcode), loc.start, loc.end): continue
                    for (ccode, cstart, cha) in unWrapNSLC(loc.stream):
                        if not self._match(self.name(ncode, scode, lcode, ccode), cha.start, cha.end): continue
                        info("[C] %-15s %g %s %s" % (self.name(ncode, scode, lcode, ccode), cha.gain, cstart, cha.end))

def loadData(args):
    inv = GInventory()
    try:
        for filename in args:
            notice("Loading %s" % filename)
            load_xml(filename, inv)
    except Exception,e:
        error(str(e))
    return inv

if __name__ == "__main__":
    parser = OptionParser(usage="ai2Table  <-c|-g|-t|-sg> [--filter  <channel pattern>] [--when <date>] <file 1> [file 2] ... [file n] ", version="0.1.8", add_help_option=True)

    ## Modes
    parser.add_option("-c", "--coordinates", action="store_true", help="Coordinates table", dest="c", default=False)
    parser.add_option("-g", "--gain", action="store_true", help="Gain Table", dest="g", default=False)
    parser.add_option("-t", "--tree", action="store_true", help="Show tree", dest="t", default=False)
    parser.add_option("-s", "--stage-gain", action="store_true", help="Integrated stages gain table", dest="sg", default=False)

    ## Options
    parser.add_option("-f", "--filter", type="string", help="String to filter the node elements [Network.Station.Location.Stream. Empty locations should be represented as '--', '*/?' are used as wildcards]", dest="filter", default=False)
    parser.add_option("-w", "--when", type="string", help="Time to extract the desired information iso format (2012-12-31T14:10:59)", dest="when", default=False)
    parser.add_option("-e", "--extra", type="string", help="Extra variable to print in the Diff output Mode", dest="extra", default=None)
    parser.add_option("-m", "--mode", type="string", help="Default printing mode for tree output (Pretty, Diff)", dest="mode", default="Pretty")

    # Parsing & Error check
    (options, args) = parser.parse_args()
    
    if len(args) < 1:
        error("You should supply at least one file to check")
        sys.exit()
 
    filter = None
    when = None
    module = None
    
    if options.filter:
        filter = options.filter
    
    if options.when:
        try:
            when = datetime.datetime.strptime(options.when, "%Y-%m-%dT%H:%M:%S")
        except Exception,e:
            error(str(e))
            sys.exit()
    
    try:
        if options.c:
            module = coordinate(filter, when)
        elif options.g:
            module = gain(filter, when)
        elif options.t:
            module = tree(filter, when, options.mode, options.extra)
        elif options.sg:
            raise Exception("Not yet implemented")
        else:
            raise Exception("No action specified")
    except Exception,e:
        error(str(e))
        sys.exit()

    inv = loadData(args)
    try:
        module.run(inv)
    except Exception,e:
        print error("Error:")
        print error(" %s" % e)
