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
        # init the mods that do not use contextual data
        self.mods['~'] = 'vibrato'
        self.mods['.'] = 'staccato'
        self.mods['_'] = 'legato'
        self.setMods()
  
    def _setMods(self):
        '''Internal method to specify tab modifiers that use contextual data.'''
        pfs, nfs = '', ''
        if isinstance(self.prev, int): pfs = self.tabsObj.getOrdSfx(self.prev)
        if isinstance(self.next, int): nfs = self.tabsObj.getOrdSfx(self.next)
        self.mods['=']  =   'play {}{} fret with vibrato'.format(self.prev, pfs)
        self.mods['\\'] =   'bend {} from {}{} fret to {}{} fret'.format(self.dir1, self.prev, pfs, self.next, nfs)
        self.mods['/']  =  'slide {} from {}{} fret to {}{} fret'.format(self.dir1, self.prev, pfs, self.next, nfs)
        self.mods['+']  = 'hammer {} from {}{} fret to {}{} fret'.format(self.dir2, self.prev, pfs, self.next, nfs)
    
    def setMods(self, dir1=None, dir2=None, prev=None, next=None):
        '''Specify the contextual data for tab modifiers'''
        if dir1: self.dir1 = dir1
        else:    self.dir1 = '(up or down)'
        if dir2: self.dir2 = dir2
        else:    self.dir2 = '(off or on)'
        if prev: self.prev = prev
        else:    self.prev = 'prev'
        if next: self.next = next
        else:    self.next = 'next'
        self._setMods()
    
    def getMods(self):
        return self.mods
