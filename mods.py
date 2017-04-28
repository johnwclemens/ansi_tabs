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
  
    def _setMods(self, prevNote, nextNote):
        '''Internal method to specify tab modifiers that use contextual data.'''
        pfs, pnn, pno, nfs, nnn, nno = '', '', '', '', '', ''
        if isinstance(self.prevFN, int) and prevNote:
            pfs, pnn, pno = self.tabsObj.getOrdSfx(self.prevFN), prevNote.name, prevNote.getOctaveNum()
        if isinstance(self.nextFN, int):
            nfs, nnn, nno = self.tabsObj.getOrdSfx(self.nextFN), nextNote.name, nextNote.getOctaveNum()
        self.mods['=']  = '{}{} fret {}{}, vibrato'.format(self.prevFN, pfs, pnn, pno)
        self.mods['.']  = '{}{} fret {}{}, staccato'.format(self.prevFN, pfs, pnn, pno)
        self.mods['_']  = '{}{} fret {}{}, legato'.format(self.prevFN, pfs, pnn, pno)
        self.mods['\\'] = '{}{} fret {}{}, bend {} to, {}{} fret {}{}'.format(self.prevFN, pfs, pnn, pno, self.dir1, self.nextFN, nfs, nnn, nno)
        self.mods['/']  = '{}{} fret {}{}, slide {} to, {}{} fret {}{}'.format(self.prevFN, pfs, pnn, pno, self.dir1, self.nextFN, nfs, nnn, nno)
        self.mods['+']  = '{}{} fret {}{}, hammer {} to, {}{} fret {}{}'.format(self.prevFN, pfs, pnn, pno, self.dir2, self.nextFN, nfs, nnn, nno)

    def setMods(self, dir1=None, dir2=None, prevFN=None, prevNote=None, nextNote=None, nextFN=None):
        '''Specify the contextual data for tab modifiers'''
        if dir1: self.dir1 = dir1
        else:    self.dir1 = '(up or down)'
        if dir2: self.dir2 = dir2
        else:    self.dir2 = '(off or on)'
        if prevFN: self.prevFN = prevFN
        else:    self.prevFN = 'prevFN'
        if next: self.nextFN = nextFN
        else:    self.nexFNt = 'nextFN'
        self._setMods(prevNote=prevNote, nextNote=nextNote)
    
    def getMods(self):
        return self.mods
