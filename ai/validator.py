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

from seiscomp.db.generic.inventory import Inventory as GInventory
from seiscomp import logs
from utils import unWrapNSLC, overlaps, isInside,  isReversed, name

class Validator(object):
    def __init__(self, clean = False):
        self._clean = clean
        self.m = {}
        self.p = {}
        self.filterCache = None
        self.accuracy = 10.0

    def collectNSLC(self, n, s, l, c, message):
        nk = None
        sk = None
        lk = None
        ck = None
        
        if n:
            nk = "%2s,%s/%s" % (n.code, n.start, n.end if n.end else "-")
            if s:
                sk = "%5s,%s/%s" % (s.code, s.start, s.end if s.end else "-")
                if l:
                    lk = "%2s,%s/%s" % (l.code if l.code else "--", l.start, l.end if l.end else "-")
                    if c:
                        ck = "%3s,%s/%s" % (c.code, c.start, c.end if c.end else "-")

        try:
            node = self.m[nk]
        except:
            self.m[nk] = {}
            self.m[nk]["messages"] = []
            node = self.m[nk]

        if sk:
            try:
                node = node[sk]
            except:
                node[sk] = {}
                node[sk]["messages"] = []
                node = node[sk]

        if lk:
            try:
                node = node[lk]
            except:
                node[lk] = {}
                node[lk]["messages"] = []
                node = node[lk]

        if ck:
            try:
                node = node[ck]
            except:
                node[ck] = {}
                node[ck]["messages"] = []
                node = node[ck]

        node["messages"].append(message)

    def collectInstrument(self, obj, message):
        id = obj.name if obj.name else obj.publicID
        try:
            node = self.p[id] 
        except:
            node = []
            self.p[id] = node
        node.append(message)

    def _findFilter(self, iv, pid):
        if not self.filterCache:
            self.filterCache = {}
            logs.debug("Creating cache ... ")
            for (name, filter) in iv.responsePAZ.items():
                self.filterCache[filter.publicID] = filter
            for (name, filter) in iv.responsePolynomial.items():
                self.filterCache[filter.publicID] = filter
            for (name, filter) in iv.responseFIR.items():
                self.filterCache[filter.publicID] = filter

        try:
            return self.filterCache[pid]
        except:
            return None

    def _findCalibration(self, cls, stream, sn, channel):
        calibration = None

        try:
            calibrations = cls[sn][channel]
            for cal in calibrations.values():
                if isInside(cal, stream):
                    return cal
        except:
            return None

        return None

    def _computeGain(self, iv, channel):
        sensor = None
        sfilter = None
        datalogger = None
        dfilters = []

        # Find Sensor
        for (name, ss) in iv.sensor.items():
            if ss.publicID == channel.sensor:
                sensor = ss
                break

        # Find Datalogger
        for (name, dt) in iv.datalogger.items():
            if dt.publicID == channel.datalogger:
                datalogger = dt
                break

        if not sensor:
            raise Exception("Could not find sensor object %s" % channel.sensor)

        if not datalogger:
            raise Exception("Could not find datalogger object %s" % channel.datalogger)

        # Go for calibration
        calibration = self._findCalibration(sensor.calibration, channel, channel.sensorSerialNumber, channel.sensorChannel)
        if not calibration:
            # Find Sensor Paz
            sfilter = self._findFilter(iv, sensor.response)
            if not sfilter:
                raise Exception("Cannot find sensor (%s) response filter %s" % (sensor.name, sensor.response))
            sgain = sfilter.gain
        else:
            sgain = calibration.gain

        # Go for calibration
        calibration = self._findCalibration(datalogger.calibration, channel, channel.dataloggerSerialNumber, channel.dataloggerChannel)
        if not calibration:
            dgain = datalogger.gain
        else:
            dgain = calibration.gain

        # Find Datalogger decimation
        try:
            dataloggerDecimation = datalogger.decimation[channel.sampleRateNumerator][channel.sampleRateDenominator]
        except:
            raise Exception("Cannot find datalogger decimation %s %s" % (channel.sampleRateNumerator, channel.sampleRateDenominator) )

        # and filters
        if dataloggerDecimation.analogueFilterChain:
            for pid in dataloggerDecimation.analogueFilterChain.split():
                filter = self._findFilter(iv, pid)
                if not filter:
                    raise Exception("Cannot find datalogger response %s" % pid)
                dfilters.append(filter)

        if dataloggerDecimation.digitalFilterChain:
            for pid in dataloggerDecimation.digitalFilterChain.split():
                filter = self._findFilter(iv, pid)
                if not filter:
                    raise Exception("Cannot find datalogger response %s" % pid)
                dfilters.append(filter)

        gain = sgain * dgain;
        for filter in dfilters:
            gain = gain * filter.gain

        return gain

    def printer(self):
        if self.m:
            logs.warning("\nNSLC issues:")
            logs.warning("------------\n")
            for (nk,net) in self.m.items():
                if len(net["messages"]) == 0:
                    print nk
                else:
                    for line in net["messages"]: print nk,":",line
    
                for (sk,sta) in net.items():
                    if sk == "messages": continue
                    if len(sta["messages"]) == 0:
                        print "  ",sk
                    else:
                        for line in sta["messages"]: print "  ",sk,":",line
    
                    for (lk,loc) in sta.items():
                        if lk == "messages": continue
                        if len(loc["messages"]) == 0:
                            print "       ",lk
                        else:
                            for line in loc["messages"]: print "       ",lk,":",line
    
                        for (ck,cha) in loc.items():
                            if ck == "messages": continue
                            if len(cha["messages"]) == 0:
                                print "         ",ck
                            else:
                                for line in cha["messages"]: print "         ",ck,":",line
        
        if self.p:
            logs.warning("\nInstruments issues:")
            logs.warning("-------------------\n")
            for (k,ms) in self.p.items():
                for m in ms:
                    logs.warning("%s: %s" % (k,m))

    def pass0(self, iv):
        for (name,datalogger) in iv.datalogger.items():
            if not name:
                self.collectInstrument(datalogger, "[0] Invalid datalogger Name for object with PID '%s'" % str(datalogger.publicID))
        
        for (ncode, nstart, net) in unWrapNSLC(iv.network):
            if not ncode: self.collectNSLC(net, None, None, None, "[0] network has no code")
            if not nstart: self.collectNSLC(net, None, None, None, "[0] network has no start time")
            if net.end and net.end < nstart: self.collectNSLC(net, None, None, None, "[0] network end is invalid") 
            for (scode, sstart, sta) in unWrapNSLC(net.station):
                if not scode: self.collectNSLC(net, sta, None, None, "[0] station has no code")
                if not sstart: self.collectNSLC(net, sta, None, None, "[0] station has no start time")
                if sta.end and sta.end < sstart: self.collectNSLC(net, sta, None, None, "[0] station end is invalid") 
                for (lcode, lstart, loc) in unWrapNSLC(sta.sensorLocation):
                    if lcode is None: self.collectNSLC(net, sta, loc, None, "[0] location has no code")
                    if not lstart: self.collectNSLC(net, sta, loc, None, "[0] location has no start time")
                    if loc.end and loc.end < lstart: self.collectNSLC(net, sta, loc, None, "[0] location end is invalid") 
                    for (ccode, cstart, cha) in unWrapNSLC(loc.stream):
                        if not ccode: self.collectNSLC(net, sta, loc, cha, "[0] stream has no code")
                        if not cstart: self.collectNSLC(net, sta, loc, cha, "[0] stream has no start time")
                        if cha.end and cha.end < cstart: self.collectNSLC(net, sta, loc, cha, "[0] location end is invalid") 

        return

    def pass1(self, iv):
        logs.notice("[Phase 1] Checking NSLC structure")
        ## Network
        for (ncode, nstart, net) in unWrapNSLC(iv.network):
            if not len(net.station): self.collectNSLC(net, None, None, None, "[1] network has no stations")
            if isReversed(net): self.collectNSLC(net, None, None, None, "[1] Is Reversed") 
            if net.archive == "": self.collectNSLC(net, None, None, None, "[1] Invalid archive")
            if net.shared != True and net.shared != False: self.collectNSLC(net, None, None, None, "[1] Invalid shared")
            for (ncode2, nstart2, net2) in unWrapNSLC(iv.network):
                if net != net2 and overlaps(net,net2):
                    self.collectNSLC(net, None, None, None, "[1] Overlaps %s %s" % (ncode2, nstart2))
            
            ## Station
            for (scode, sstart, sta) in unWrapNSLC(net.station):
                if not len(sta.sensorLocation): self.collectNSLC(net, sta, None, None, "[1] station has no locations")
                if isReversed(sta): self.collectNSLC(net, sta, None, None, "[1] Is Reversed") 
                if net.archive != sta.archive: self.collectNSLC(net,sta,None,None, "[1] Missmatch in archive flag")
                if sta.archive == "": self.collectNSLC(net, sta, None, None, "[1] Invalid archive")
                if sta.shared != True and sta.shared != False: self.collectNSLC(net, sta, None, None, "[1] Invalid shared")
                if isReversed(sta) or isReversed(net):
                    self.collectNSLC(net, sta, None, None, "[1] Cannot check time span integrity")
                else:
                    if not isInside(net, sta):
                        self.collectNSLC(net, sta, None, None, "[1] Does not fit parent.")
                for (scode2, sstart2, sta2) in unWrapNSLC(net.station):
                    if sta != sta2 and overlaps(sta,sta2):
                        self.collectNSLC(net, sta, None, None, "[1] Overlaps %s %s" % (scode2, sstart2))

                ## Location
                for (lcode, lstart, loc) in unWrapNSLC(sta.sensorLocation):
                    if not len(loc.stream): self.collectNSLC(net, sta, loc, None, "[1] location has no stream")
                    if isReversed(loc): self.collectNSLC(net, sta, loc, None, "[1] Is Reversed") 
                    if isReversed(sta) or isReversed(loc):
                        self.collectNSLC(net, sta, loc, None, "[1] Cannot check time span integrity")
                    else:
                        if not isInside(sta, loc):
                            self.collectNSLC(net, sta, loc, None, "[1] Does not fit parent.")
                    for (lcode2, lstart2, loc2) in unWrapNSLC(sta.sensorLocation):
                        if loc != loc2 and overlaps(loc,loc2):
                            self.collectNSLC(net, sta, loc, None, "[1] Overlaps %s %s" % (lcode2, lstart2))

                    ## Stream
                    for (ccode, cstart, cha) in unWrapNSLC(loc.stream):
                        if isReversed(cha): self.collectNSLC(net, sta, loc, cha, "[1] Is Reversed") 
                        if isReversed(cha) or isReversed(loc):
                            self.collectNSLC(net, sta, loc, cha, "[1] Cannot check time span integrity")
                        else:
                            if not isInside(loc, cha):
                                self.collectNSLC(net, sta, loc, cha, "[1] Does not fit parent.")
                        for (ccode2, cstart2, cha2) in unWrapNSLC(loc.stream):
                            if cha != cha2 and overlaps(cha, cha2):
                                self.collectNSLC(net, sta, loc, cha, "[1] Overlaps %s %s" % (ccode2, cstart2))

    def pass2(self, iv):
        logs.notice("[Phase 2] Checking Instruments structure")
        ss = []
        dt = []
        for (ncode, nstart, net) in unWrapNSLC(iv.network):
            for (scode, sstart, sta) in unWrapNSLC(net.station):
                for (lcode, lstart, loc) in unWrapNSLC(sta.sensorLocation):
                    for (ccode, cstart, cha) in unWrapNSLC(loc.stream):
                        if cha.sensor: ss.append(cha.sensor)
                        if cha.datalogger: dt.append(cha.datalogger)

        #### Check that every sensor/datalogger is used
        ##
                
        ## Sensor
        sref = []
        for (name, sensor) in iv.sensor.items():
            if sensor.response and sensor.response not in sref: sref.append(sensor.response)
            if not sensor.response:
                self.collectInstrument(sensor, "[2] Sensor has no response defined.")
            if sensor.publicID in ss:
                continue
            self.collectInstrument(sensor, "[2] Sensor is not used")

        ## Dataloger
        dref = []
        for (name,datalogger) in iv.datalogger.items():
            for (srn, lsrn) in datalogger.decimation.items():
                for (srd, decimation) in lsrn.items():
                    if decimation.analogueFilterChain:
                        dref.extend(decimation.analogueFilterChain.split(" "))
                    if decimation.digitalFilterChain:
                        dref.extend(decimation.digitalFilterChain.split(" "))
                    if not decimation.digitalFilterChain and not decimation.analogueFilterChain:
                        self.collectInstrument(datalogger, "[2] Datalogger has no filters defined for decimation %s/%s." % (srn,srd))
            if not datalogger.gain:
                self.collectInstrument(datalogger, "[2] Datalogger has no gain defined")
            if not datalogger.decimation:
                self.collectInstrument(datalogger, "[2] Datalogger has no decimation stages.")
            if datalogger.publicID in dt:
                continue
            self.collectInstrument(datalogger, "[2] Datalogger is not used")

        #### Check that every filter is used
        ##
        fref = {}

        ## Paz
        for (name, rpaz) in iv.responsePAZ.items():
            if rpaz.publicID and rpaz.publicID not in fref: fref[rpaz.publicID] = rpaz
            if rpaz.publicID in sref:
                continue
            if rpaz.publicID in dref:
                continue
            self.collectInstrument(rpaz, "[2] Pole and Zero is not used")

        ## Polynomial
        for (name, rpol) in iv.responsePolynomial.items():
            if rpol.publicID and rpol.publicID not in fref: fref[rpol.publicID] = rpol            
            if rpol.publicID in sref:
                continue
            self.collectInstrument(rpol, "[2] Polynomial response is not used")

        ## Fir
        for (name, rfir) in iv.responseFIR.items():
            if rfir.publicID and rfir.publicID not in fref: fref[rfir.publicID] = rfir
            if rfir.publicID in dref:
                continue
            self.collectInstrument(rfir, "[2] Fir-filter is not used")

        #### Check that every filter can be resolved
        ##
        for (name, sensor) in iv.sensor.items():
            if sensor.response not in fref:
                self.collectInstrument(sensor, ("[2] Cannot find filter %s for sensor" % sensor.response))

        for (name,datalogger) in iv.datalogger.items():
            for (srn, lsrn) in datalogger.decimation.items():
                for (srd, decimation) in lsrn.items():
                    if decimation.analogueFilterChain:
                        for decimationId in decimation.analogueFilterChain.split(" "):
                            if decimationId not in fref:
                                 self.collectInstrument(sensor, ("[2] Cannot find filter %s for datalogger" % decimationId))
                    if decimation.digitalFilterChain:
                        for decimationId in decimation.digitalFilterChain.split(" "):
                            if decimationId not in fref:
                                 self.collectInstrument(sensor, ("[2] Cannot find filter %s for datalogger" % decimationId))

    def pass3(self, iv):
        logs.notice("[Phase 3] Checking instruments references from channel & channel/location coordinates consistency")

        ## Sensor
        sref = []
        for (name, sensor) in iv.sensor.items():
            sref.append(sensor.publicID)

        ## Dataloger
        dref = []
        for (name,datalogger) in iv.datalogger.items():
            dref.append(datalogger.publicID)

        for (ncode, nstart, net) in unWrapNSLC(iv.network):
            for (scode, sstart, sta) in unWrapNSLC(net.station):
                try:
                    float(sta.latitude)
                except Exception, e:
                    self.collectNSLC(net, sta, None, None, "[3] Station has invalid Latitude '%s'" % sta.latitude)

                try:
                    float(sta.longitude)
                except Exception, e:
                    self.collectNSLC(net, sta, None, None, "[3] Station has invalid Longitude '%s'" % sta.longitude)

                try:
                    float(sta.latitude)
                except Exception, e:
                    self.collectNSLC(net, sta, None, None, "[3] Station has invalid Elevation '%s'" % sta.elevation)

                for (lcode, lstart, loc) in unWrapNSLC(sta.sensorLocation):
                    try:
                        float(loc.latitude)
                    except Exception, e:
                        self.collectNSLC(net, sta, loc, None, "[3] Location has invalid Latitude '%s'" % loc.latitude)

                    try:
                        float(loc.longitude)
                    except Exception, e:
                        self.collectNSLC(net, sta, loc, None, "[3] Location has invalid Longitude '%s'" % loc.longitude)

                    try:
                        float(loc.latitude)
                    except Exception, e:
                        self.collectNSLC(net, sta, loc, None, "[3] Location has invalid Elevation '%s'" % loc.elevation)

                    for (ccode, cstart, cha) in unWrapNSLC(loc.stream):
                        if cha.sensor:
                            if cha.sensor not in sref:
                                self.collectNSLC(net, sta, loc, cha, "[3] Undefined sensor %s" % cha.sensor)
                        else:
                            self.collectNSLC(net, sta, loc, cha, "[3] Has no sensor defined")
                        
                        if cha.datalogger:
                            if cha.datalogger not in dref:
                                self.collectNSLC(net, sta, loc, cha, "[3] Undefined datalogger %s" % cha.datalogger)
                        else:
                            self.collectNSLC(net, sta, loc, cha, "[3] Has no datalogger defined")

                        try:
                            float(cha.depth)
                        except Exception, e:
                            self.collectNSLC(net, sta, loc, cha, "[3] Stream has invalid Depth '%s'" % cha.depth)

                        try:
                            int(cha.sampleRateNumerator)
                        except Exception, e:
                            self.collectNSLC(net, sta, loc, cha, "[3] Stream has invalid SampleRateNumerator '%s'" % cha.sampleRateNumerator)

                        try:
                            int(cha.sampleRateDenominator)
                        except Exception, e:
                            self.collectNSLC(net, sta, loc, cha, "[3] Stream has invalid SampleRateNumerator '%s'" % cha.sampleRateDenominator)

                        try:
                            float(cha.gain)
                        except Exception, e:
                            self.collectNSLC(net, sta, loc, cha, "[3] Stream has invalid Gain '%s'" % cha.gain)

                        try:
                            float(cha.gainFrequency)
                        except Exception, e:
                            self.collectNSLC(net, sta, loc, cha, "[3] Stream has invalid GainFrequency '%s'" % cha.gainFrequency)

                        try:
                            if not cha.gainUnit: raise Exception("");
                        except Exception, e:
                            self.collectNSLC(net, sta, loc, cha, "[3] Stream has invalid GainUnit '%s'" % cha.gainUnit)

                        try:
                            badDip = False
                            int(cha.dip)
                        except Exception, e:
                            badDip = True
                            self.collectNSLC(net, sta, loc, cha, "[3] Stream has invalid Dip '%s'" % cha.dip)

                        try:
                            int(cha.azimuth)
                        except Exception, e:
                            if badDip is False and cha.dip != 0.0:
                                self.collectNSLC(net, sta, loc, cha, "[3] Stream has invalid Azimuth '%s'" % cha.azimuth)

    def pass4(self, iv):
        logs.warning("[Phase 4] Checking instruments gains at the flat-band [Accuracy == %s %%]" % (self.accuracy))

        ## Reset the filter cache
        self.filterCache = None

        for (ncode, nstart, net) in unWrapNSLC(iv.network):
            for (scode, sstart, sta) in unWrapNSLC(net.station):
                for (lcode, lstart, loc) in unWrapNSLC(sta.sensorLocation):
                    for (ccode, cstart, cha) in unWrapNSLC(loc.stream):
                        try:
                            gain = self._computeGain(iv, cha)
                            perc = (abs(cha.gain - gain) / cha.gain) * 100.0
                            if perc > self.accuracy:
                                self.collectNSLC(net, sta, loc, cha, "[4] Computed gain %g does not match defined %g [%.2f x]" % (gain, cha.gain, gain / cha.gain))
                        except Exception,e:
                            pass

    def checkGain(self, iv):
        self.pass4(iv)

    def check(self, iv, rtn = None, phase = None):
        if phase is not None and (phase > 4 or phase < 1):
            raise Exception("Invalid phase %s to check (1 - 4)" % phase)

        self.pass0(iv)
        if self.m:
            logs.error('Invalid Inventory -- Aborting !')
            return
        
        if not phase or phase == 1: self.pass1(iv)
        if not phase or phase == 2: self.pass2(iv)
        if not phase or phase == 3: self.pass3(iv)
        
        if phase and phase == 4: self.pass4(iv)
        
        return
