'''mods.py module.  class list: [Mods].  Users are encouraged to modify this module to customize the tabs mods as desired'''

'''Note, tab mods are essentially opaque to the tabs application.  However, their values are displayed at the bottom of the tabs console 
when the cursor is under any of the keys that are displayed in the tabs and notes sections.  Thus they are essentially self documenting.  
The tab mod characters are assumed to apply to the previous tab or between the previous and the next tab.  Note the lower case letters 
[a-o] are used to denote tabs [10-24] and some upper case letters are reserved for user interactive commands, thus tab mods should avoid 
overriding defined alphabetic characters as keys.'''

class Mods(object):
    '''Model playing techniques and expression using a dictionary of tab modifier keys with contextually descriptive values.'''
    def __init__(self, tabsObj):
        self.tabsObj = tabsObj
        self.mods = {}
        self.setMods()
  
    def _setMods(self, pn, nn, ph, nh):
        '''Internal method to specify tab modifiers that use contextual data.'''
        CSI, pnt, nnt = self.tabsObj.CSI, '', ''
        stStyle, pfStyle, pnStyle, nfStyle, nnStyle = CSI + '32;40m', CSI + '32;40m', CSI + '32;40m', CSI + '32;40m', CSI + '32;40m'
        if ph: pfStyle, pnStyle, pnt = CSI + '33;40m', CSI + '33;40m', ' Harmonic '
        if nh: nfStyle, nnStyle, nnt = CSI + '33;40m', CSI + '33;40m', ' Harmonic '
        pfs, pnn, pno, nfs, nnn, nno = '', '', '', '', '', ''
        if isinstance(self.prevFN, int) and pn:
            pfs, pnn, pno = self.tabsObj.getOrdSfx(self.prevFN), ' ' + pn.name, pn.getOctaveNum()
            if ph and len(pn.name) > 1:
                if pn.name[1] == '#': pnStyle = CSI + '31;43m'
                else:                 pnStyle = CSI + '34;43m'
            elif len(pn.name) > 1:
                if pn.name[1] == '#': pnStyle = CSI + '31;40m'
                else:                 pnStyle = CSI + '36;40m'
        if isinstance(self.nextFN, int) and nn:
            nfs, nnn, nno = self.tabsObj.getOrdSfx(self.nextFN), ' ' + nn.name, nn.getOctaveNum()
            if nh and len(nn.name) > 1:
                if nn.name[1] == '#': nnStyle = CSI + '31;43m'
                else:                 nnStyle = CSI + '34;43m'
            elif len(nn.name) > 1:
                if nn.name[1] == '#': nnStyle = CSI + '31;40m'
                else:                 nnStyle = CSI + '36;40m'
        self.mods['#']  = pfStyle + '{}{}'.format(self.prevFN, pfs) + stStyle + ' fret' + pnStyle + '{}{}{}'.format(pnt, pnn, pno) + stStyle + ' mute'
        self.mods['~']  = '{}{} fret{}{} vibrato'.format(self.prevFN, pfs, pnn, pno)
        self.mods['=']  = '{}{} fret{}{} vibrato'.format(self.prevFN, pfs, pnn, pno)
        self.mods['.']  = '{}{} fret{}{} staccato'.format(self.prevFN, pfs, pnn, pno)
        self.mods['_']  = '{}{} fret{}{} legato'.format(self.prevFN, pfs, pnn, pno)
        self.mods['\\'] = pfStyle + '{}{}'.format(self.prevFN, pfs) + stStyle + ' fret' + pnStyle + '{}{}{}'.format(pnt, pnn, pno) + stStyle + ' bend {} to '.format(self.dir1) + \
                          nfStyle + '{}{}'.format(self.nextFN, nfs) + stStyle + ' fret' + nnStyle + '{}{}{}'.format(nnt, nnn, nno)
        self.mods['/']  = '{}{} fret{}{} slide {} to {}{} fret{}{}'.format(self.prevFN, pfs, pnn, pno, self.dir1, self.nextFN, nfs, nnn, nno)
        self.mods['+']  = '{}{} fret{}{} hammer {} to {}{} fret{}{}'.format(self.prevFN, pfs, pnn, pno, self.dir2, self.nextFN, nfs, nnn, nno)

    def setMods(self, dir1=None, dir2=None, prevFN=None, prevNote=None, nextNote=None, nextFN=None, ph=0, nh=0):
        '''Specify the contextual data for tab modifiers'''
        if dir1: self.dir1 = dir1
        else:    self.dir1 = '(up or down)'
        if dir2: self.dir2 = dir2
        else:    self.dir2 = '(off or on)'
        if prevFN is not None: self.prevFN = prevFN
        else:    self.prevFN = 'prev'
        if nextFN: self.nextFN = nextFN
        else:    self.nextFN = 'next'
        self._setMods(pn=prevNote, nn=nextNote, ph=ph, nh=nh)
    
    def getMods(self):
        return self.mods
