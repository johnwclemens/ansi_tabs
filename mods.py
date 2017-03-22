class Mods(object):
    '''Represent playing techniques and expression using a dictionary of tab modifier keys and contextually descriptive values.'''
    def __init__(self, file=None):
        self.dbgFile = file
        self.dir = '(up or down)'
        self.dir2 = '(off or on)'
        self.prev = 'prev'
        self.next = 'next'
        self.mods = {}
        self._setMods()
        self.mods['='] = 'vibrato'
        self.mods['.'] = 'staccato'
        self.mods['_'] = 'legato'
#        self.mods['*'] = 'harmonic'  # Note harmonic notes are specified by using 'Ctrl Down Arrow' and are printed in bright color.
  
    def _setMods(self):
        '''Internal method to specify tab modifiers with contextual data.'''
        self.mods['\\'] =   'bend {} from {} to {}'.format(self.dir, self.prev, self.next)
        self.mods['/']  =  'slide {} from {} to {}'.format(self.dir, self.prev, self.next)
        self.mods['+']  = 'hammer {} from {} to {}'.format(self.dir2, self.prev, self.next)
    
    def setMods(self, dir=None, prev=None, next=None, dir2=None):
        '''Specifies the contextual data for tab modifiers'''
        if dir: self.dir = dir
        if dir2: self.dir2 = dir2
        if prev: self.prev = prev
        if next: self.next = next
        self._setMods()
    
    def getMods(self):
        return self.mods
