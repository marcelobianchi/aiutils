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
from optparse import OptionParser

try:
    from seiscomp.db.generic.inventory import Inventory as GInventory
    from seiscomp import logs
except:
    print >>sys.stderr, "Please use the install.sh script to adjust the seiscomp3 folder."
    sys.exit()

from ai.utils import load_xml
from ai.validator import Validator

if __name__ == "__main__":
    parser = OptionParser(usage="aiValidate [-p 0-4] <file 1> [file 2] ... [file n] ", version="0.1.5", add_help_option=True)
    parser.add_option("-p", "--phase", type="int", help="Choose the phase to check (1 == Structure/ 2=Instruments / 3=Stream-Instrument relation / 4=Gain [disabled by default])", dest="phase", default=None)

    # Parsing & Error check
    (options, args) = parser.parse_args()

    if len(args) < 1:
        logs.error("You should supply at least one file to check")
        sys.exit()

    if options.phase:
        if options.phase < 1 or options.phase > 4:
            logs.error("Phase should be between 1-4")
            sys.exit()

    try:

        ## Get the validator
        _validator = Validator()

        ## Get an empty inventory
        _inventory = GInventory()

        ## Merge supplied files
        for filename in args:
            load_xml(filename, _inventory)

        ## Check
        _validator.check(_inventory, None, options.phase)

        ## Print results
        _validator.printer()

    except Exception,e:
        logs.error(str(e))
        sys.exit()
