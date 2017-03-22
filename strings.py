import notes

class Strings(object):
    '''Represent the musical instrument strings and how they are tuned in ascending order.'''
    
    def __init__(self, dbgFile, spelling=None, alias=None):
        '''The alias argument overrides the spelling argument.  e.g. alias='GUITAR' -> strings=['E2A2D3G3B3E4'] represents a standard 6 string guitar tuning.'''
        self.dbgFile = dbgFile
        self._map = {}
        self._keys = []
        alias = alias[0].upper()
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

    def _initAliases(self):
        self.ALIASES = {}
        self.ALIASES['GUITAR']              = ['E2A2D3G3B3E4']
        self.ALIASES['GUITAR_OPEN_GMIN_OT'] = ['G2G2D3G3Bb3D4']
    
    @property
    def map(self):
        return self._map
    
    @property
    def keys(self):
        return self._keys
        
    @map.setter
    def map(self):
        '''Return map of string note names -> note indices e.g. a standard 6 string guitar tuning { E2:28 A2:33 D3:38 G3:43 B3:47 E4:52 }.'''
        return self._map
        
    @keys.setter
    def keys(self):
        '''Return the keys sorted in ascending order.'''
        return self._keys
        
    def _parseSpelling(self, spelling):
        '''Parse string spelling into map of note names -> note indices.'''
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
                if key not in notes.INDICES:
                    errorMsg = 'Strings.parseSpelling({}) invalid key={}, extracted from spelling={}'.format(i, key, spelling)
                    print(errorMsg, file=self.dbgFile)
                    print(errorMsg)
                    raise Exception(errorMsg)
                self.map[key] = notes.INDICES[key]
                print('Strings.parseSpelling({}) appending {}:{} to map={}'.format(i, key, self.map[key], self.map), file=self.dbgFile)
        self._keys = sorted(self.map, key=self._mapKeyFunc, reverse=False)
        print('Strings.parseSpelling() map={}'.format(self.map), file=self.dbgFile)
        print('Strings.parseSpelling() keys={}'.format(self.keys), file=self.dbgFile)
        print('Strings.parseSpelling() sorted map: {', end='', file=self.dbgFile)
        for k in self.keys:
            print(' {}:{}'.format(k, self.map[k]), end='', file=self.dbgFile)
        print(' }', file=self.dbgFile)
        
    def _mapKeyFunc(self, inKey):
        '''Internal method for sorting the map keys in ascending order.'''
        return self.map[inKey]

