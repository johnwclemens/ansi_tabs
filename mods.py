'''mods.py module.  class list: [Mods].  Users are encouraged to modify this module to customize the tabs mods dictionary as desired'''

'''Note, tab mods are essentially opaque to the tabs application.  However, the key and value are displayed at the bottom of the tabs console 
when the cursor is on any of the tab mod keys that are displayed in the tabs section.  Thus they are essentially self documenting.  
The tab mod characters are assumed to apply to the previous tab or between the previous and the next tab.  Note the lower case letters 
[a-o] are used to denote tabs [10-24] and some upper case letters are reserved for user interactive commands, thus tab mods should avoid 
overriding defined alphabetic characters as keys.'''

class Mods(object):
    '''Model playing techniques and expression using a dictionary of tab modifier keys with contextually descriptive values.'''
    def __init__(self, tabsObj):
        self.tabsObj = tabsObj
        self.txts = {}
        self.mods = {}
        self.setMods()
    
    def _setMods(self, pn, nn, ph, nh):
        '''Internal method to update tab modifiers dictionary with contextual data.'''
        self.mods['#']  = self._frmt1(' mute ', pn, nn, ph, nh, shrt=1)
        self.txts['#']  = self._frmt2(' mute ', pn, nn, ph, nh, shrt=1)
        self.mods['=']  = self._frmt1(' vibrato ', pn, nn, ph, nh, shrt=1)
        self.txts['=']  = self._frmt2(' vibrato ', pn, nn, ph, nh, shrt=1)
        self.mods['.']  = self._frmt1(' staccato ', pn, nn, ph, nh, shrt=1)
        self.txts['.']  = self._frmt2(' staccato ', pn, nn, ph, nh, shrt=1)
        self.mods['_']  = self._frmt1(' legato ', pn, nn, ph, nh, shrt=1)
        self.txts['_']  = self._frmt2(' legato ', pn, nn, ph, nh, shrt=1)
        self.mods['+']  = self._frmt1(' hammer {} to '.format(self.dir2), pn, nn, ph, nh)
        self.txts['+']  = self._frmt2(' hammer {} to '.format(self.dir2), pn, nn, ph, nh)
        self.mods['/']  = self._frmt1(' slide {} to '.format(self.dir1), pn, nn, ph, nh)
        self.txts['/']  = self._frmt2(' slide {} to '.format(self.dir1), pn, nn, ph, nh)
        self.mods['\\'] = self._frmt1(' bend {} to '.format(self.dir1), pn, nn, ph, nh)
        self.txts['\\'] = self._frmt2(' bend {} to '.format(self.dir1), pn, nn, ph, nh)
        self.mods['[']  = self._frmt1(' bgn_group {} ', pn, nn, ph, nh, shrt=1)
        self.txts['[']  = self._frmt2(' bgn_group {} ', pn, nn, ph, nh, shrt=1)
        self.mods[']']  = self._frmt1(' end_group {} ', pn, nn, ph, nh, shrt=1)
        self.txts[']']  = self._frmt2(' end_group {} ', pn, nn, ph, nh, shrt=1)
        self.mods['|']  = self._frmt1(' bar ', pn, nn, ph, nh, shrt=1)
        self.txts['|']  = self._frmt2(' bar ', pn, nn, ph, nh, shrt=1)
        self.mods['%']  = self._frmt1(' repeat ', pn, nn, ph, nh, shrt=1)
        self.txts['%']  = self._frmt2(' repeat ', pn, nn, ph, nh, shrt=1)
    
    def _frmt1(self, modText, pn, nn, ph, nh, shrt=0):
        '''Internal method to format the tab modifiers dictionary string values.'''
        CSI, pnt, nnt = self.tabsObj.CSI, '', ''
        stStyle, ntStyle, fStyle, pnStyle, nnStyle = CSI + '30;47m', CSI + '33;47m', CSI + '32;47m', CSI + '32;47m', CSI + '32;47m'
        if ph: pnt = ' Harmonic'
        if nh: nnt = ' Harmonic'
        pfs, pnn, pno, nfs, nnn, nno = '', '', '', '', '', ''
        if isinstance(self.prevFN, int) and pn:
            pfs, pnn, pno = self.tabsObj.getOrdSfx(self.prevFN), ' ' + pn.name, pn.getOctaveNum()
            if len(pn.name) > 1:
                if pn.name[1] == '#': pnStyle = CSI + '31;47m'
                else:                 pnStyle = CSI + '36;47m'
        if isinstance(self.nextFN, int) and nn:
            nfs, nnn, nno = self.tabsObj.getOrdSfx(self.nextFN), ' ' + nn.name, nn.getOctaveNum()
            if len(nn.name) > 1:
                if nn.name[1] == '#': nnStyle = CSI + '31;47m'
                else:                 nnStyle = CSI + '36;47m'
        if self.prevFN != 0: pfn = '{}{}'.format(self.prevFN, pfs)
        else:                pfn = 'open'
        if self.nextFN != 0: nfn = '{}{}'.format(self.nextFN, nfs)
        else:                nfn = 'open'
        if shrt:
            val = fStyle + pfn + stStyle + ' fret' + ntStyle + '{}'.format(pnt) + pnStyle + '{}{}'.format(pnn, pno) + stStyle + modText
        else:
            val = fStyle + pfn + stStyle + ' fret' + ntStyle + '{}'.format(pnt) + pnStyle + '{}{}'.format(pnn, pno) + stStyle + modText + \
                  fStyle + nfn + stStyle + ' fret' + ntStyle + '{}'.format(nnt) + nnStyle + '{}{}'.format(nnn, nno)
        return val
    
    def _frmt2(self, modText, pn, nn, ph, nh, shrt=0):
        pnt, nnt = '', ''
        if ph: pnt = ' Harmonic'
        if nh: nnt = ' Harmonic'
        pfs, pnn, pno, nfs, nnn, nno = '', '', '', '', '', ''
        if isinstance(self.prevFN, int) and pn:
            pfs, pnn, pno = self.tabsObj.getOrdSfx(self.prevFN), ' ' + pn.name, pn.getOctaveNum()
        if isinstance(self.nextFN, int) and nn:
            nfs, nnn, nno = self.tabsObj.getOrdSfx(self.nextFN), ' ' + nn.name, nn.getOctaveNum()
        if self.prevFN != 0: pfn = '{}{}'.format(self.prevFN, pfs)
        else:                pfn = 'open'
        if self.nextFN != 0: nfn = '{}{}'.format(self.nextFN, nfs)
        else:                nfn = 'open'
        if shrt:
            val = pfn + ' fret' + '{}'.format(pnt) + '{}{}'.format(pnn, pno) + modText
        else:
            val = pfn + ' fret' + '{}'.format(pnt) + '{}{}'.format(pnn, pno) + modText + \
                  nfn + ' fret' + '{}'.format(nnt) + '{}{}'.format(nnn, nno)
        return val
    
    def setMods(self, dir1=None, dir2=None, prevFN=None, prevNote=None, nextNote=None, nextFN=None, ph=0, nh=0):
        '''Specify the contextual data for tab modifiers'''
        if dir1 is not None: self.dir1 = dir1
        else:                self.dir1 = '(up or down)'
        if dir2 is not None: self.dir2 = dir2
        else:                self.dir2 = '(off or on)'
        if prevFN is not None: self.prevFN = prevFN
        else:                  self.prevFN = 'prev'
        if nextFN is not None: self.nextFN = nextFN
        else:                  self.nextFN = 'next'
        self._setMods(pn=prevNote, nn=nextNote, ph=ph, nh=nh)
    
    def getMods(self):
        return self.mods
    
    def getTxts(self):
        return self.txts
    
