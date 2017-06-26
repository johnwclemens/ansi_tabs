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
                for i in range(len(chordName)):
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
                    self.tabsObj.prints(chordName[i], i + row, col, style)
#                    self.moveTo()
                break

    def getChordName(self, imap):
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
                        elif  '2' in imap or  '9' in imap:    return '{}+9'.format(r)
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
                        elif  '2' in imap or  '9' in imap:     return '{}m+9'.format(r)
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
