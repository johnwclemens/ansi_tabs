'''strings.py module.  class list: [Strings].  Users are encouraged to modify this module to customize the aliases dictionary'''

import notes, collections

class Strings(object):
    '''Model the musical instrument strings and how they are tuned in ascending order.'''
    
    def _initAliases(self):  # how to model mandolin and 12 string guitar?
        '''Register aliases for specific string spellings.  Edit this method to add, remove, or modify aliases as desired.'''
        self.ALIASES = {}
        self.ALIASES['GUITAR']                    = ['E2A2D3G3B3E4']   # standard 6 string
        self.ALIASES['GUITAR_DADGAD']             = ['D2A2D3G3A3D4']
        self.ALIASES['GUITAR_OPEN_D_VESTAPOL']    = ['D2A2D3F#3A3D4']
        self.ALIASES['GUITAR_OPEN_G_OVERTONE']    = ['G2G2D3G3B3D4']
        self.ALIASES['GUITAR_OPEN_GMIN_OVERTONE'] = ['G2G2D3G3Bb3D4']
        self.ALIASES['TENOR_GUITAR']              = ['C3G3D4A4']
        self.ALIASES['UKULELE']                   = ['G4C4E4A4']       # 1 of many tunings, all notes in the same octave with the G note out of order
        self.ALIASES['BASS']                      = ['E1A1D2G2']       # electric bass not acoustic double bass
        self.ALIASES['BASS_5_STRING']             = ['B0E1A1D2G2']
        self.ALIASES['BASS_5_STRING_TENOR']       = ['E1A1D2G2C3']
        self.ALIASES['BASS_6_STRING']             = ['B0E1A1D2G2C3']
        self.ALIASES['DOUBLE_BASS']               = ['E1A1D2G2']       # acoustic double bass not electric bass
        self.ALIASES['CELLO']                     = ['C2G2D3A3']
        self.ALIASES['VIOLA']                     = ['C3G3D4A4']
        self.ALIASES['VIOLIN']                    = ['G3D4A4E5']
    
    def __init__(self, dbgFile, spelling=None, alias=None):
        '''The alias argument overrides the spelling argument.  e.g. alias=['GUITAR'] -> strings=['E2A2D3G3B3E4'] represents a standard 6 string guitar tuning.'''
        self.dbgFile = dbgFile
        self._map = collections.OrderedDict() #{}
        self._keys = []
        if alias: alias = alias[0].upper()
        self._initAliases()
        print('Strings() alias={}, spelling={}'.format(alias, spelling), file=self.dbgFile)
        if not spelling and not alias:
            alias = 'GUITAR'
            spelling = self.ALIASES[alias]
            print('Strings() no alias and no spelling, using defaluts: alias={}, spelling={}'.format(alias, spelling), file=self.dbgFile)
        elif alias and alias in self.ALIASES: 
            spelling = self.ALIASES[alias]
            print('Strings() using valid alias={}, and its looked up spelling={}'.format(alias, spelling), file=self.dbgFile)
        elif alias and spelling: 
            print('Strings() Ignoring invalid alias={}, using valid spelling={}'.format(alias, spelling), file=self.dbgFile)
        elif alias:
            print('Strings() ERROR! invalid alias={} and no spelling={}'.format(alias, spelling), file=self.dbgFile)
            raise Exception('Strings() ERROR! invalid alias={} and no spelling={}'.format(alias, spelling))
        if spelling:
            print('Strings() spelling={}'.format(spelling), file=self.dbgFile)
            self._parseSpelling(spelling)
    
    @property
    def map(self):
        return self._map
    
    @property
    def keys(self):
        return self._keys
    
    @map.setter
    def map(self):
        '''Return map of string note name -> note index e.g. a standard 6 string guitar tuning { E2:28 A2:33 D3:38 G3:43 B3:47 E4:52 }.'''
        return self._map
    
    @keys.setter
    def keys(self):
        '''Return the keys sorted in ascending order.'''
        return self._keys
    
    def _parseSpelling(self, spelling):
        '''Parse string spelling into map of note name -> note index.'''
        key = None
        if len(spelling) != 1:
            errorMsg = 'Strings.parseSpelling() invalid raw spelling len(spelling)={} expected len(spelling)=1, spelling={}'.format(len(spelling), spelling)
            print(errorMsg, file=self.dbgFile)
            print(errorMsg)
            raise Exception(errorMsg)
        print('Strings.parseSpelling(list) spelling={} len(spelling)={}'.format(spelling, len(spelling)), file=self.dbgFile)
        self.spelling = str(spelling[0]).upper()
        print('Strings.parseSpelling(strg) spelling={} len(spelling)={}'.format(self.spelling, len(self.spelling)), file=self.dbgFile)
        for i in range(0, len(self.spelling)):
            print('Strings.parseSpelling({}) {}'.format(i, self.spelling[i]), file=self.dbgFile)
            if ord(self.spelling[i]) in range(ord('A'), ord('G') + 1) and self.spelling[i+1].isdecimal():
                key = self.spelling[i:i+2]
            elif ord(self.spelling[i]) in range(ord('A'), ord('G') + 1) and self.spelling[i+1] in ('#', 'B') and self.spelling[i+2].isdecimal():
                if self.spelling[i+1] == 'B': 
                    self.spelling = self.spelling[:i+1] + self.spelling[i+1].lower() + self.spelling[i+2:]
                key = self.spelling[i:i+3]
                print('Strings.parseSpelling({}) enharmonic string key {}'.format(i, key), file=self.dbgFile)
            if key:
                print('Strings.parseSpelling({}) current key={}, current map={}'.format(i, key, self.map), file=self.dbgFile)
                if key not in notes.Note.INDICES:
                    errorMsg = 'Strings.parseSpelling({}) invalid key={}, extracted from spelling={}'.format(i, key, spelling)
                    print(errorMsg, file=self.dbgFile)
                    print(errorMsg)
                    raise Exception(errorMsg)
                self.map[key] = notes.Note.INDICES[key]
                print('Strings.parseSpelling({}) appending {}:{} to map={}'.format(i, key, self.map[key], self.map), file=self.dbgFile)
#        self._keys = sorted(self.map, key=self._mapKeyFunc, reverse=False)
        self._keys = list(self._map.keys())
        print('Strings.parseSpelling() map={}'.format(self.map), file=self.dbgFile)
        print('Strings.parseSpelling() keys={}'.format(self.keys), file=self.dbgFile)
        print('Strings.parseSpelling() sorted map: {', end='', file=self.dbgFile)
        for k in self.keys:
            print(' {}:{}'.format(k, self.map[k]), end='', file=self.dbgFile)
        print(' }', file=self.dbgFile)
    
    def _mapKeyFunc(self, inKey):
        '''Internal method for sorting the map keys in ascending order.'''
        return self.map[inKey]
    
