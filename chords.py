'''chords.py module.  class list: [Chords].  Users are encouraged to modify this module to customize chord discovery and naming'''

class Chords(object):
    '''Model chords for stringed instruments.  Discover and name chords'''
    
    def __init__(self, tabsObj):
        self.INTERVAL_RANK = { 'R':0, 'b2':1, '2':2, 'm3':3, 'M3':4, '4':5, 'b5':6, '5':7, 'a5':8, '6':9, 'b7':10, '7':11, 'b9':12, '9':13, '11':14, '13':15 }
        self.tabsObj = tabsObj
        self.chords = {}                                       # dict of chord spelling -> chord name; cache of discovered chords to avoid calculation
        print('Chords() tabsObj={}'.format(tabsObj), file=tabsObj.dbgFile)

    def imapKeyFunc(self, inKey):
        return self.INTERVAL_RANK[inKey]
        
    def getChordKey(self, keys):
        return ' '.join(keys)

    def eraseChord(self, cc):
        row, col = self.tabsObj.indices2RowCol(self.tabsObj.numStrings + self.tabsObj.NOTES_LEN, cc)
#        print('eraseChord({}) (row,col)=({},{}) bgn: '.format(cc, row, col), file=self.tabsObj.dbgFile)
        for r in range(self.tabsObj.CHORDS_LEN):
            self.tabsObj.prints(' ', r + row, col, self.tabsObj.styles['NAT_CHORD'])
            
    def printChords(self):
        print('printChords({}, {}) bgn {} =?= {} * {}'.format(self.tabsObj.row, self.tabsObj.col, self.tabsObj.numTabsPerString, self.tabsObj.numLines, self.tabsObj.numTabsPerStringPerLine), file=self.tabsObj.dbgFile)
        for c in range(self.tabsObj.numTabsPerString):
            noteCount = 0
            self.eraseChord(c)
            for r in range(self.tabsObj.numStrings):
                if self.tabsObj.isFret(chr(self.tabsObj.tabs[r][c])):
                    if noteCount > 0:
                        self.printChord(c=c)
                        break
                    noteCount += 1
            print(file=self.tabsObj.outFile)
        print('printChords({}, {}) end {} =?= {} * {}'.format(self.tabsObj.row, self.tabsObj.col, self.tabsObj.numTabsPerString, self.tabsObj.numLines, self.tabsObj.numTabsPerStringPerLine), file=self.tabsObj.dbgFile)
        
    def printChord(self, c=None, dbg=1):
        '''Analyse notes in given column index and if a valid chord is discovered then print it in the appropriate chords section.'''
        if c is None:
            c = self.tabsObj.col - self.tabsObj.COL_OFF
        self.eraseChord(c)
        row, col = self.tabsObj.indices2RowCol(self.tabsObj.numStrings + self.tabsObj.NOTES_LEN, c)
        indent = '    '
        if dbg:
            print('printChord({}) ({},{}) bgn: '.format(c, row, col), file=self.tabsObj.dbgFile)
            print('{}Strings     ['.format(indent), end='', file=self.tabsObj.dbgFile)
            for r in range(self.tabsObj.numStrings - 1, -1, -1):
                if self.tabsObj.isFret(chr(self.tabsObj.tabs[r][c])):
                    note = self.tabsObj.getNote(r + 1, 0)
                    print('{:>3}/{:<1}'.format(r+1, note.name[0]), end=' ', file=self.tabsObj.dbgFile)
        tbs = []
        for r in range(self.tabsObj.numStrings):
            if self.tabsObj.isFret(chr(self.tabsObj.tabs[r][c])):
                tbs.append(chr(self.tabsObj.tabs[r][c]))
        tbs.reverse()
        if dbg:
            print(']\n{}tabs        ['.format(indent), end='', file=self.tabsObj.dbgFile)
            for t in range(len(tbs)):
                print('{:>5}'.format(tbs[t]), end=' ', file=self.tabsObj.dbgFile)
        tbs = []
        for r in range(self.tabsObj.numStrings):
            if self.tabsObj.isFret(chr(self.tabsObj.tabs[r][c])):
                tbs.append(chr(self.tabsObj.getFretByte(self.tabsObj.getFretNum(self.tabsObj.tabs[r][c]) + self.tabsObj.getFretNum(self.tabsObj.capo))))
        tbs.reverse()
        if dbg:
            print(']\n{}capoed tabs ['.format(indent), end='', file=self.tabsObj.dbgFile)
            for t in range(len(tbs)):
                print('{:>5}'.format(tbs[t]), end=' ', file=self.tabsObj.dbgFile)
        
        notes = []
        for r in range(self.tabsObj.numStrings):
            tab = self.tabsObj.getFretByte(self.tabsObj.getFretNum(self.tabsObj.tabs[r][c]) + self.tabsObj.getFretNum(self.tabsObj.capo))
            if self.tabsObj.isFret(chr(tab)):
                note = self.tabsObj.getNote(r + 1, tab)
                if len(note.name) > 1 and note.name[1] == '#' and self.tabsObj.enharmonic == self.tabsObj.ENHARMONIC['FLAT']:
                    note.name = self.tabsObj.SHARPS_2_FLATS[note.name]
                elif len(note.name) > 1 and note.name[1] == 'b' and self.tabsObj.enharmonic == self.tabsObj.ENHARMONIC['SHARP']:
                    note.name = self.tabsObj.FLATS_2_SHARPS[note.name]
                notes.append(note.name)
        notes.reverse()
        if dbg:
            print(']\n{}notes       ['.format(indent), end='', file=self.tabsObj.dbgFile)
            for t in range(len(notes)):
                print('{:>5}'.format(notes[t]), end=' ', file=self.tabsObj.dbgFile)
                
        indices = []
        for r in range(self.tabsObj.numStrings):
            tab = self.tabsObj.getFretByte(self.tabsObj.getFretNum(self.tabsObj.tabs[r][c]) + self.tabsObj.getFretNum(self.tabsObj.capo))
            if self.tabsObj.isFret(chr(tab)):
                note = self.tabsObj.getNote(r + 1, tab)
                indices.append(note.index)
        indices.reverse()
        if dbg:
            print(']\n{}indices     ['.format(indent), end='', file=self.tabsObj.dbgFile)
            for t in range(len(indices)):
                print('{:>5}'.format(indices[t]), end=' ', file=self.tabsObj.dbgFile)
            print(']', file=self.tabsObj.dbgFile)
        
        for j in range(len(indices)):
            if dbg: print('{}printChord({}) index={}'.format(indent, c, j), file=self.tabsObj.dbgFile)
            deltas = []
            for i in range(len(indices)):
                if indices[i] - indices[j] >= 0:
                    deltas.append(indices[i] - indices[j])
                elif 0 > indices[i] - indices[j] >= -12:
                    deltas.append(indices[i] - indices[j] + 12)
                elif -12 > indices[i] - indices[j] >= -24:
                    deltas.append(indices[i] - indices[j] + 24)
                elif -24 > indices[i] - indices[j] >= -36:
                    deltas.append(indices[i] - indices[j] + 36)
                elif -36 > indices[i] - indices[j] >= -48:
                    deltas.append(indices[i] - indices[j] + 48)
            if dbg:
                print('{}deltas      ['.format(indent), end='', file=self.tabsObj.dbgFile)
                for t in range(len(deltas)):
                    print('{:>5}'.format(deltas[t]), end=' ', file=self.tabsObj.dbgFile)
            intervals = []
            for i in range(len(deltas)):
                intervals.append(self.tabsObj.INTERVALS[deltas[i]])
            if dbg:
                print(']\n{}intervals   ['.format(indent), end='', file=self.tabsObj.dbgFile)
                for t in range(len(deltas)):
                    print('{:>5}'.format(intervals[t]), end=' ', file=self.tabsObj.dbgFile)
            
            imap = dict(zip(intervals, notes))
            imapKeys = sorted(imap, key=self.imapKeyFunc, reverse=False)
            chordKeys = [ imap[k] for k in imapKeys ]
            chordKey = self.getChordKey(chordKeys)
            if dbg:
                print(']\n{}iMap        ['.format(indent), end='', file=self.tabsObj.dbgFile)
                for k in imap:
                    print('{:>2}:{:<2}'.format(k, imap[k]), end=' ', file=self.tabsObj.dbgFile)
                print(']\n{}imapKeys    ['.format(indent), end='', file=self.tabsObj.dbgFile)
                for k in imapKeys:
                    print('{:>5}'.format(k), end=' ', file=self.tabsObj.dbgFile)
                print(']\n{}chordKeys   ['.format(indent), end='', file=self.tabsObj.dbgFile)
                for k in chordKeys:
                    print('{:>5}'.format(k), end=' ', file=self.tabsObj.dbgFile)
                print(']\n{}chords      ['.format(indent), end=' ', file=self.tabsObj.dbgFile)
                for k in self.chords:
                    print('\'{}\':{}'.format(k, self.chords[k]), end=', ', file=self.tabsObj.dbgFile)
                print(']', file=self.tabsObj.dbgFile)
            
            chordName = ''
            if chordKey not in self.chords:
                if dbg: print('{}printChord({}) index={}, Key=\'{}\' not in chords - calculating value'.format(indent, c, j, chordKey), file=self.tabsObj.dbgFile)
                chordName = self.getChordName(imap)
                if len(chordName) > 0:
                    self.chords[chordKey] = chordName
                    if dbg:
                        print('{}printChord({}) index={}, Adding Key=\'{}\', value=\'{}\' to chords'.format(indent, c, j, chordKey, self.chords[chordKey]), file=self.tabsObj.dbgFile)
                        print('chords      [', end=' ', file=self.tabsObj.dbgFile)
                        for k in self.chords:
                            print('\'{}\':{}'.format(k, self.chords[k]), end=', ', file=self.tabsObj.dbgFile)
                        print(']', file=self.tabsObj.dbgFile)
                elif dbg: print('{}printChord({}) index={}, Key=\'{}\' not a chord'.format(indent, c, j, chordKey), file=self.tabsObj.dbgFile)
            else: 
                if dbg: print('{}printChord({}) index={}, Found key=\'{}\', value=\'{}\' in chords'.format(indent, c, j, chordKey, self.chords[chordKey]), file=self.tabsObj.dbgFile)
                chordName = self.chords[chordKey]
            if len(chordName) > 0:
                if len(chordName) > 1 and ( chordName[1] == '#' or chordName[1] == 'b' ):
                    chordName = chordName[0] + chordName[2:]
#                print('printChord() colorize name={}, len={}'.format(chordName, len(chordName)), file=self.tabsObj.dbgFile)
                for i in range(len(chordName)):
#                i = 0
#                while i < len(chordName):
#                    print('printChord() colorizing name={}, len={}, i={}'.format(chordName, len(chordName), i), file=self.tabsObj.dbgFile)
                    style = self.tabsObj.styles['NAT_CHORD']
                    if i == 0:
                        if len(imap['R']) > 1:
                            if imap['R'][1] == '#':
                                if self.tabsObj.enharmonic == self.tabsObj.ENHARMONIC['FLAT']:
                                    style = self.tabsObj.styles['FLT_CHORD']
                                else:
                                    style = self.tabsObj.styles['SHP_CHORD']
                            elif imap['R'][1] == 'b':
                                if self.tabsObj.enharmonic == self.tabsObj.ENHARMONIC['SHARP']:
                                    style = self.tabsObj.styles['SHP_CHORD']
                                else:
                                    style = self.tabsObj.styles['FLT_CHORD']
                    elif chordName[i] == 'm' or 'dim' in chordName and chordName[i] == 'd' or chordName[i] == 'i':
                        style = self.tabsObj.styles['FLT_CHORD']
#                    elif chordName[i] == '+':
#                        chordName = chordName[0:i] + chordName[i+1:]
#                        style = self.tabsObj.styles['SHP_CHORD']
#                        print('printChord() colorized name={}, len={}, i={}'.format(chordName, len(chordName), i), file=self.tabsObj.dbgFile)
                    self.tabsObj.prints(chordName[i], i + row, col, style)
#                    i += 1
#                    self.moveTo()
                break

    def getChordName_ORIG(self, imap):
        '''Calculate chord name.'''
        r = imap['R']
        if 'R' in imap:
            if '5' in imap: 
                if len(imap) == 2:                            return '{}5'.format(r)
                elif 'M3' in imap:
                    if len(imap) == 3:                        return '{}'.format(r)
                    elif len(imap) == 4:
                        if   'b7' in imap:                    return '{}7'.format(r)
                        elif  '7' in imap:                    return '{}M7'.format(r)
                        elif  '6' in imap or '13' in imap:    return '{}6'.format(r)
                        elif  '4' in imap or '11' in imap:    return '{}4'.format(r)
                        elif  '2' in imap or  '9' in imap:    return '{}2'.format(r)
                    elif len(imap) == 5:
                        if 'b7' in imap:
                            if   '2' in imap or  '9' in imap: return '{}9'.format(r)
                            elif '4' in imap or '11' in imap: return '{}11'.format(r)
                            elif '6' in imap or '13' in imap: return '{}13'.format(r)
                        elif '7' in imap:
                            if   '2' in imap or  '9' in imap: return '{}M9'.format(r)
                            elif '4' in imap or '11' in imap: return '{}M11'.format(r)
                            elif '6' in imap or '13' in imap: return '{}M13'.format(r)
                elif 'm3' in imap:
                    if len(imap) == 3:                        return '{}m'.format(r)
                    elif len(imap) == 4:
                        if   'b7' in imap:                    return '{}m7'.format(r)
                        elif  '7' in imap:                    return '{}mM7'.format(r)
                        elif  '6' in imap or '13' in imap:    return '{}m6'.format(r)
                        elif  '4' in imap or '11' in imap:    return '{}m4'.format(r)
                        elif  '2' in imap or  '9' in imap:    return '{}m2'.format(r)
                    elif len(imap) == 5:
                        if 'b7' in imap:
                            if   '2' in imap or  '9' in imap: return '{}m9'.format(r)
                            elif '4' in imap or '11' in imap: return '{}m11'.format(r)
                            elif '6' in imap or '13' in imap: return '{}m13'.format(r)
                elif len(imap) == 3:
                    if    '2' in imap or  '9' in imap:        return '{}s2'.format(r)
                    elif  '4' in imap or '11' in imap:        return '{}s4'.format(r)
                elif len(imap) == 4:
                    if   'b7' in imap:
                        if    '2' in imap or  '9' in imap:    return '{}7s2'.format(r)
                        elif  '4' in imap or '11' in imap:    return '{}7s4'.format(r)
            elif 'b5' in imap:
                if 'm3' in imap:
                    if len(imap) == 3:                        return '{}dim'.format(r)
            elif 'a5' in imap:
                if 'M3' in imap:
                    if len(imap) == 3:                        return '{}aug'.format(r)
            # Maybe omit all the n5 (no 5th) chords for simplicity
            elif 'M3' in imap:
                if len(imap) == 3:
                    if   'b7' in imap:                        return '{}7n5'.format(r)
                    elif  '7' in imap:                        return '{}M7n5'.format(r)
                elif len(imap) == 4:
                    if   'b7' in imap:
                        if '9' in imap:                       return '{}9n5'.format(r)
            elif 'm3' in imap:
                if len(imap) == 3:
                    if   'b7' in imap:                        return '{}m7n5'.format(r)
                    elif  '7' in imap:                        return '{}mM7n5'.format(r)
        return ''

    def getChordName(self, imap):
        '''Calculate chord name.'''
        r = imap['R']
        if '5' in imap: 
            if len(imap) == 2:                            return '{}5'.format(r)    # Power5
            elif 'M3' in imap:
                if len(imap) == 3:                        return '{}'.format(r)     # Maj
                elif len(imap) == 4:
                    if   'b7' in imap:                    return '{}7'.format(r)    # Dom7
                    elif  '7' in imap:                    return '{}M7'.format(r)   # Maj7
                    elif  '2' in imap or  '9' in imap:    return '{}2'.format(r)    # Add2
                    elif  '4' in imap or '11' in imap:    return '{}4'.format(r)    # Add4
                    elif  '6' in imap or '13' in imap:    return '{}6'.format(r)    # Add6
                elif len(imap) == 5:
                    if 'b7' in imap:
                        if   '2' in imap or  '9' in imap: return '{}9'.format(r)    # 9
                        elif '4' in imap or '11' in imap: return '{}11n9'.format(r) # 11no9
                        elif '6' in imap or '13' in imap: return '{}13n9'.format(r) # 13no9
                    elif '7' in imap:
                        if   '2' in imap or  '9' in imap: return '{}M9'.format(r)   # Maj9
                        elif '4' in imap or '11' in imap: return '{}M11n9'.format(r)  # Maj11no9
                        elif '6' in imap or '13' in imap: return '{}M13n9'.format(r)  # Maj13no9
                elif len(imap) == 6:
                    if 'b7' in imap and ('2' in imap or '9' in imap):
                        if   '4' in imap or '11' in imap: return '{}11'.format(r)   # 11
                        elif '6' in imap or '13' in imap: return '{}13'.format(r)   # 13
                    elif '7' in imap:
            elif 'm3' in imap:
                if len(imap) == 3:                        return '{}m'.format(r)    # Min
                elif len(imap) == 4:
                    if   'b7' in imap:                    return '{}m7'.format(r)   # MinDom7
                    elif  '7' in imap:                    return '{}mM7'.format(r)  # MinMaj7
                    elif  '6' in imap or '13' in imap:    return '{}m6'.format(r)   # Min6
                    elif  '4' in imap or '11' in imap:    return '{}m4'.format(r)   # Min4
                    elif  '2' in imap or  '9' in imap:    return '{}m2'.format(r)   # Min2
                elif len(imap) == 5:
                    if 'b7' in imap:
                        if   '2' in imap or  '9' in imap: return '{}m9'.format(r)   # Min9
                        elif '4' in imap or '11' in imap: return '{}m11'.format(r)  # Min11
                        elif '6' in imap or '13' in imap: return '{}m13'.format(r)  # Min13
            elif len(imap) == 3:
                if    '2' in imap or  '9' in imap:        return '{}s2'.format(r)   # sus2
                elif  '4' in imap or '11' in imap:        return '{}s4'.format(r)   # sus4
            elif len(imap) == 4:
                if   'b7' in imap:
                    if    '2' in imap or  '9' in imap:    return '{}7s2'.format(r)  # Dom7sus2
                    elif  '4' in imap or '11' in imap:    return '{}7s4'.format(r)  # Dom7sus4
        elif 'b5' in imap:
            if 'm3' in imap:
                if len(imap) == 3:                        return '{}o'.format(r)    # Dim
                elif len(imap) == 4:
                    if   'b7' in imap:                    return '{}07'.format(r)   # HalfDim7
                    elif  '6' in imap:                    return '{}o7'.format(r)   # Dim7
            elif 'M3' in imap:
                if len(imap) == 4:
                    if 'b7' in imap:                      return '{}7b5'.format(r)  # Dom7Dim5
        elif 'a5' in imap:
            if 'M3' in imap:
                if len(imap) == 3:                        return '{}+'.format(r)    # Aug
                elif len(imap) == 4:
                    if   'b7' in imap:                    return '{}+7'.format(r)   # Aug7
                    elif  '7' in imap:                    return '{}+M7'.format(r)  # AugMaj7
        # Maybe omit all the n5 (no 5th) chords for simplicity
        elif 'M3' in imap:
            if len(imap) == 3:
                if   'b7' in imap:                        return '{}7n5'.format(r)
                elif  '7' in imap:                        return '{}M7n5'.format(r)
            elif len(imap) == 4:
                if   'b7' in imap:
                    if '9' in imap:                       return '{}9n5'.format(r)
        elif 'm3' in imap:
            if len(imap) == 3:
                if   'b7' in imap:                        return '{}m7n5'.format(r)
                elif  '7' in imap:                        return '{}mM7n5'.format(r)
        return ''
        
'''
Chord Naming Conventions:
| ----------------------------------------------------------|
| Long      | Short | Intervals          | Notes            | NoR | No3 | No5 |
| ----------------------------------------------------------|
| CMaj      | C     | R 3 5              | C E G            |
| CMin      | Cm    | R m3 5             | C Eb G           |
| CAug      | C+    | R 3 a5             | C E G#           |
| CDim      | Co    | R m3 b5            | C Eb Gb          |
| ----------------------------------------------------------|
| CMaj7     | CM7   | R 3 5 7            | C E G B          |
| CDom7     | C7    | R 3 5 b7           | C E G Bb         |
| CMin7     | Cm7   | R m3 5 b7          | C Eb G Bb        |
| CMinMaj7  | CmM7  | R m3 5 7           | C Eb G B         |
| CAugMaj7  | C+M7  | R 3 a5 7           | C E G# B         |
| CAug7     | C+7   | R 3 a5 b7          | C E G# Bb        |
| CHDim7    | C07   | R m3 b5 b7         | C Eb Gb Bb       |
| CDim7     | Co7   | R m3 b5 bb7        | C Eb Gb Bbb      |
| C7Dim5    | C7b5  | R 3 b5 b7          | C E Gb Bb        |
| ----------------------------------------------------------|
| CMaj9     | CM9   | R 3 5 7 9          | C E G B D        |
| CDom9     | C9    | R 3 5 b7 9         | C E G Bb D       |
| CMinMaj9  | CmM9  | R m3 5 7 9         | C Eb G B D       |
| CMinDom9  | Cm9   | R m3 5 b7 9        | C Eb G Bb D      |
| CAugMaj9  | C+M9  | R 3 a5 7 9         | C E G# B D       |
| CAugDom9  | C+9   | R 3 a5 b7 9        | C E G# Bb D      |
| CHDim9    | C09   | R m3 b5 b7 9       | C Eb Gb Bb D     |
| CHDimMin9 | C0b9  | R m3 b5 b7 9b      | C Eb Gb Bb Db    |
| CDim9     | Co9   | R m3 b5 bb7 9      | C Eb Gb Bbb D    |
| CDimMin9  | Cob9  | R m3 b5 bb7 b9     | C Eb Gb Bbb Db   |
| ----------------------------------------------------------|
| CMaj11    | CM11  | R 3 5 7 9 11       | C E G B D F      |
| CDom11    | C11   | R 3 5 b7 9 11      | C E G Bb D F     |
| CMinMaj11 | CmM11 | R m3 5 7 9 11      | C Eb G B D F     |
| CMin11    | Cm11  | R m3 5 b7 9 11     | C Eb G Bb D F    |
| CAugMaj11 | C+M11 | R 3 a5 7 9 11      | C E G# B D F     |
| CAug11    | C+11  | R 3 a5 b7 9 11     | C E G# Bb D F    |
| CHDim11   | C011  | R m3 b5 b7 b9 11   | C Eb Gb Bb Db F  |
| CDim11    | Co11  | R m3 b5 bb7 b9 b11 | C Eb Gb Bbb Db F |
| ----------------------------------------------------------|
| CMaj13    | CM13  | R 3 5 7 9 11 13    | C E G B D F A    |
| CDom13    | C13   | R 3 5 b7 9 11 13   | C E G Bb D F A   |
| CMinMaj13 | CmM13 | R m3 5 7 9 11 13   | C Eb G B D F A   |
| CMinDom13 | Cm13  | R m3 5 b7 9 11 13  | C Eb G Bb D F A  |
| CAugMaj13 | C+M13 | R 3 a5 7 9 11 13   | C E G# B D F A   |
| CAugDom13 | C+13  | R 3 a5 b7 9 11 13  | C E G# Bb D F A  |
| CHDim13   | C013  | R m3 b5 b7 9 11 13 | C Eb Gb Bb D F A |
| ----------------------------------------------------------|
| CPower5   | C5    | R 5                | C G              |
| C7no3     | C7no3 | R 5 7b             | C G Bb           |
| ----------------------------------------------------------|
| Csus2     | Cs2   | R 2 5              | C D G            |
| C7sus2    | C7s2  | R 2 5 b7           | C D G Bb         |
| C9sus2    | C9s2  | R 2 5 b7 9         | C D G Bb D       |
| Csus4     | Cs4   | R 4 5              | C F G            |
| C7sus4    | C7s4  | R 4 5 b7           | C F G Bb         |
| C9sus4    | C9s4  | R 4 5 b7 9         | C F G Bb D       |
| ----------------------------------------------------------|
| Cadd9     | C2    | R 2 3 5            | C D E G          |
| Cadd11    | C4    | R 3 4 5            | C E F G          |
| Cadd13    | C6    | R 3 5 6            | C E G A          |
| CAdd6Add9 | C6/9  | R 3 5 6 9          | C E G A D        |


C5   : R 5            : C G            : 5
C    : R M3 5         : C E G          : Maj
Cm   : R m3 5         : C Eb G         : Min
C+   : R M3 a5        : C E G#         : Aug
Co   : R m3 b5        : C Eb Gb        : Dim
Co5  : R M3 b5        : C E Gb         : Dim5

C7   : R M3 5 b7      : C E G Bb       : Dom7
CM7  : R M3 5 7       : C E G B        : Maj7
Cm7  : R m3 5 b7      : C Eb G Bb      : Min7
CmM7 : R m3 5 7       : C Eb G B       : MinMaj7
Co7  : R m3 b5 6      : C Eb Gb Bbb    : Dim7
C07  : R m3 b5 b7     : C Eb Gb Bb     : HDim7
C+7  : R M3 a5 b7     : C E G# Bb      : Aug7
C+M7 : R M3 a5 7      : C E G# B       : AugMaj7

C9   : C E G Bb D     : Dom9
C11  : C E G Bb D F   : Dom11
C13  : C E G Bb D F A : Dom13
CM9  : C E G B D      : Maj9
CM11 : C E G B D F    : Maj11
CM13 : C E G B D F A  : Maj13
Cm9  : C Eb G B D     : Min9
Cm11 : C Eb G B D F   : Maj11
Cm13 : C Eb G B D F A : Maj13

C7+5 : C E G# Bb      : 7Aug5
C7-5 : C E Gb Bb      : 7Dim5
C7+9 : C E G Bb D#    : 7#9
C7-9 : C E G Bb Db    : 7b9
'''