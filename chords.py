'''chords.py module.  class list: [Chords].  Users are encouraged to modify this module to customize chord discovery and naming'''

import notes
import collections

class Chords(object):
    '''Model chords for stringed instruments.  Discover and name chords.'''
    # Consider: Chords without a root note (E G Bb D -> C9)?  Multiple chord names for same imap (C+7 = C7b13)?  Use red m for mM chords?
    def __init__(self, tabsObj):
        self.CHORD_LABEL = 'CHORD'
        self.c = None
        self.chordNames = {}
        self.indent = '    '
        self.INTERVALS =     { 0:'R', 1:'b2', 2:'2', 3:'m3', 4:'M3', 5:'4', 6:'b5', 7:'5', 8:'a5', 9:'6', 10:'b7', 11:'7' }
        self.INTERVAL_RANK = { 'R':0, 'b2':1, '2':2, 'm3':3, 'M3':4, '4':5, 'b5':6, '5':7, 'a5':8, '6':9, 'b7':10, '7':11, }
        self.tobj = tabsObj
        self.chords = collections.OrderedDict()                 # dict of chord spelling -> chord name; cache of discovered chords to avoid calculation
        print('Chords() tobj={}, chords={}'.format(self.tobj, self.chords), file=self.tobj.DBG_FILE)
    
    def imapKeyFunc(self, inKey):
        return self.INTERVAL_RANK[inKey]
    
    def getChordKey(self, keys):
        return ' '.join(keys)
    
    def eraseChord(self, c, rmv=1, dbg=1):
        row, col = self.tobj.indices2RowCol(self.tobj.numStrings + self.tobj.NOTES_LEN + self.tobj.INTERVALS_LEN, c)
        if dbg and c == 0: print('eraseChord(rmv={} c={}) row={} col={} bgn'.format(rmv, c, row, col), file=self.tobj.DBG_FILE)
        if c in self.tobj.chordInfo:
            print('eraseChord(rmv={} c={}) deleting chordInfo'.format(rmv, c), file=self.tobj.DBG_FILE)
            self.tobj.dumpChordInfoCol(self.tobj.chordInfo[c])
            del self.tobj.chordInfo[c]
            self.tobj.dumpChordInfo(self.tobj.chordInfo)
        if rmv == 1:
            if c in self.tobj.chordAliases:
                print('eraseChord(rmv={}) deleting chordAliases[{}]={}'.format(rmv, c, self.tobj.chordAliases[c]), file=self.tobj.DBG_FILE)
                del self.tobj.chordAliases[c]
            if c in self.tobj.analyzeIndices:
                print('eraseChord(rmv={}) deleting analyzeIndices[{}]={}'.format(rmv, c, self.tobj.analyzeIndices[c]), file=self.tobj.DBG_FILE)
                del self.tobj.analyzeIndices[c]
        for r in range(self.tobj.CHORDS_LEN):
            self.tobj.prints(' ', r + row, col, self.tobj.styles['NAT_CHORD'])
    
    def printChords(self):
        self.tobj.printFileMark('<BGN_CHORDS_SECTION>')
        print('printChords({} {}) {} =?= {} * {}'.format(self.tobj.row, self.tobj.col, self.tobj.numTabsPerString, self.tobj.numLines, self.tobj.numTabsPerStringPerLine), file=self.tobj.DBG_FILE)
        for line in range(self.tobj.numLines):
            row = self.tobj.ROW_OFF + line * self.tobj.lineDelta() + self.tobj.numStrings + self.tobj.NOTES_LEN + self.tobj.INTERVALS_LEN
            for r in range(self.tobj.CHORDS_LEN):
                self.tobj.prints(self.CHORD_LABEL[r], r + row, 1, self.tobj.styles['NAT_CHORD'])
                self.tobj.prints(chr(self.tobj.capo), r + row, self.tobj.cursorModeCol, self.tobj.cursorDirStyle)
        for c in range(self.tobj.numTabsPerString):
            self.eraseChord(c, rmv=0)
            noteCount = 0
            for r in range(self.tobj.numStrings):
                if self.tobj.isFret(chr(self.tobj.tabs[r][c])):
                    noteCount += 1
                    if noteCount > 1:
                        self.printChord(c=c)
                        break
            print(file=self.tobj.outFile)
        self.tobj.printFileMark('<END_CHORDS_SECTION>')
        return self.chordNames
    
    def printChord(self, c, bStyle='', pc=1, dbg=0):
        '''Analyze notes in given column index and if a valid chord is discovered then print it in the appropriate chords section.'''
        self.c = c
        if self.c is None:
            self.c = self.tobj.col - self.tobj.COL_OFF
        self.eraseChord(self.c, rmv=0)
        row, col = self.tobj.indices2RowCol(self.tobj.numStrings + self.tobj.NOTES_LEN + self.tobj.INTERVALS_LEN, self.c)
        if dbg:
            print('printChord(pc={}, c={}) row={} col={} len(chords)={} dbg={} BGN'.format(pc, self.c, row, col, len(self.chords), dbg), file=self.tobj.DBG_FILE)
            self.printStrings()
            self.printTabs()
        if dbg >= 3: self.printTabs(capoed=1)
        (_notes, indices) = self.getNotesAndIndices(dbg=dbg)
        aliases, limap, lchords, count, selected, chordName = [], [], [], 0, 0, ''
        for i in range(len(indices)-1, -1, -1):
            if dbg: print('{}printChord({}) index={}'.format(self.indent, self.c, i), file=self.tobj.DBG_FILE)
            intervals = self.getIntervals(i, indices, dbg=dbg)
            (imap, imapKeys, imapNotes, chordKey) = self.getImapAndKeys(intervals, _notes, dbg=dbg)
            currentName = self.updateChords(i, chordKey, imap, count, dbg=dbg)
            lchords.insert(0, currentName)
            limap = self.add2Limap(imap, limap, currentName, dbg=dbg)
            if len(currentName) > 0:
                chordName = currentName
                if chordName in self.tobj.selectChords:
                    selected += 1
                    if selected == 1:
                        selectedChord = self.tobj.imap2String(self.tobj.selectChords[chordName])
                        print('printChord({}) FOUND SELECTED chordName={} in selectChords[{}]={}'.format(self.c, chordName, chordName, selectedChord), file=self.tobj.DBG_FILE)
                        self.tobj.chordInfo[self.c] = {'INDEX': i, 'CHORDS': lchords, 'LIMAP': limap}
                        if pc: self.printChordName(row, col, chordName, imap, bStyle)
                        self.chordNames[self.c] = chordName
                        print('printChord({}) ADDING chordName[{}]={} to chordNames={}'.format(self.c, self.c, self.chordNames[self.c], self.chordNames), file=self.tobj.DBG_FILE)
        if selected == 0 and len(limap):
            imap = limap[0]
            print('printChord({}) currentName={} chordName={} imap={}'.format(self.c, currentName, chordName, imap), file=self.tobj.DBG_FILE)
            if pc: self.printChordName(row, col, chordName, imap, bStyle)
            self.tobj.chordInfo[self.c] = {'INDEX': i, 'CHORDS': lchords, 'LIMAP': limap}
            if len(chordName) > 0:
                self.chordNames[self.c] = chordName
                print('printChord({}) ADDING chordName[{}]={} to chordNames={}'.format(self.c, self.c, self.chordNames[self.c], self.chordNames), file=self.tobj.DBG_FILE)
        if self.c in self.tobj.chordInfo:
            self.tobj.dumpChordInfoCol(self.tobj.chordInfo[self.c], reason='printChord({})'.format(self.c))
        return chordName
    
    def printStrings(self):
        print('{}Strings     ['.format(self.indent), end='', file=self.tobj.DBG_FILE)
        for r in range(self.tobj.numStrings - 1, -1, -1):
            if self.tobj.isFret(chr(self.tobj.tabs[r][self.c])):
                note = self.tobj.getNote(r + 1, 0)
                print('{:>2}/{:<2}'.format(r + 1, note.name), end=' ', file=self.tobj.DBG_FILE)
    
    def printTabs(self, capoed=0):
        tbs = []
        if capoed: label = ']\n{}capoed tabs ['.format(self.indent)
        else:      label = ']\n{}tabs        ['.format(self.indent)
        for r in range(self.tobj.numStrings):
            if self.tobj.isFret(chr(self.tobj.tabs[r][self.c])):
                if capoed: tab = chr(self.tobj.getFretByte(self.tobj.getFretNum(self.tobj.tabs[r][self.c]) + self.tobj.getFretNum(self.tobj.capo)))
                else:      tab = chr(self.tobj.tabs[r][self.c])
                tbs.insert(0, tab)
        print('{}'.format(label), end='', file=self.tobj.DBG_FILE)
        for t in range(len(tbs)):
            print('{:>5}'.format(tbs[t]), end=' ', file=self.tobj.DBG_FILE)
    
    def getNotesAndIndices(self, dbg=0):
        _notes = []
        for r in range(self.tobj.numStrings):
            if self.tobj.isFret(chr(self.tobj.tabs[r][self.c])):
                tab = self.tobj.getFretByte(self.tobj.getFretNum(self.tobj.tabs[r][self.c]) + self.tobj.getFretNum(self.tobj.capo))
                if self.tobj.isFret(chr(tab)):
                    note = self.tobj.getNote(r + 1, tab)
                    _notes.insert(0, note.name)
        if dbg:
            print(']\n{}notes       ['.format(self.indent), end='', file=self.tobj.DBG_FILE)
            for t in range(len(_notes)):
                print('{:>5}'.format(_notes[t]), end=' ', file=self.tobj.DBG_FILE)
        indices = []
        for r in range(self.tobj.numStrings):
            if self.tobj.isFret(chr(self.tobj.tabs[r][self.c])):
                tab = self.tobj.getFretByte(self.tobj.getFretNum(self.tobj.tabs[r][self.c]) + self.tobj.getFretNum(self.tobj.capo))
                if self.tobj.isFret(chr(tab)):
                    note = self.tobj.getNote(r + 1, tab)
                    indices.insert(0, note.index)
        if dbg:
            print(']\n{}indices     ['.format(self.indent), end='', file=self.tobj.DBG_FILE)
            for t in range(len(indices)):
                print('{:>5}'.format(indices[t]), end=' ', file=self.tobj.DBG_FILE)
            print(']', file=self.tobj.DBG_FILE)
        return (_notes, indices)
    
    def getIntervals(self, j, indices, dbg=0):
        deltas = []
        for i in range(len(indices)):
            if indices[i] - indices[j] >= 0:
                deltas.append((indices[i] - indices[j]) % notes.Note.NUM_SEMI_TONES)
            else:
                d = (indices[j] - indices[i]) % notes.Note.NUM_SEMI_TONES
                delta = notes.Note.NUM_SEMI_TONES - d
                if delta == notes.Note.NUM_SEMI_TONES: delta = 0
                deltas.append(delta)
        if dbg:
            print('{}deltas      ['.format(self.indent), end='', file=self.tobj.DBG_FILE)
            for t in range(len(deltas)):
                print('{:>5}'.format(deltas[t]), end=' ', file=self.tobj.DBG_FILE)
        intervals = []
        for i in range(len(deltas)):
            intervals.append(self.INTERVALS[deltas[i]])
        if dbg:
            print(']\n{}intervals   ['.format(self.indent), end='', file=self.tobj.DBG_FILE)
            for t in range(len(deltas)):
                print('{:>5}'.format(intervals[t]), end=' ', file=self.tobj.DBG_FILE)
        return intervals
    
    def getImapAndKeys(self, intervals, _notes, dbg=0):
        imap = collections.OrderedDict(sorted(dict(zip(intervals, _notes)).items(), key=lambda t: self.INTERVAL_RANK[t[0]]))
        imapKeys = imap.keys()
        imapNotes = imap.values()
        chordKey = self.getChordKey(imapNotes)
        sdeltas, rdeltas, relimapKeys = [], [], ['R']
        for k in imapKeys: sdeltas.append(self.INTERVAL_RANK[k])
        rdeltas.append(sdeltas[0])
        for i in range(1, len(sdeltas)): 
            rdeltas.append(sdeltas[i] - sdeltas[i-1])
            relimapKeys.append(self.INTERVALS[rdeltas[i]])
        if dbg >= 2:
            print(']\n{}sdeltas     ['.format(self.indent), end='', file=self.tobj.DBG_FILE)
            for sd in sdeltas:
                print('{:>5}'.format(sd), end=' ', file=self.tobj.DBG_FILE)
            print(']\n{}rdeltas     ['.format(self.indent), end='', file=self.tobj.DBG_FILE)
            for rd in rdeltas:
                print('{:>5}'.format(rd), end=' ', file=self.tobj.DBG_FILE)
            print(']\n{}relimapKeys ['.format(self.indent), end='', file=self.tobj.DBG_FILE)
            for rk in relimapKeys:
                print('{:>5}'.format(rk), end=' ', file=self.tobj.DBG_FILE)
            print(']\n{}imap        ['.format(self.indent), end='', file=self.tobj.DBG_FILE)
            for k in imap:
                print('{:>2}:{:<2}'.format(k, imap[k]), end=' ', file=self.tobj.DBG_FILE)
        if dbg:
            print(']\n{}imapKeys    ['.format(self.indent), end='', file=self.tobj.DBG_FILE)
            for k in imapKeys:
                print('{:>5}'.format(k), end=' ', file=self.tobj.DBG_FILE)
            print(']\n{}imapNotes   ['.format(self.indent), end='', file=self.tobj.DBG_FILE)
            for k in imapNotes:
                print('{:>5}'.format(k), end=' ', file=self.tobj.DBG_FILE)
            print(']\n{}chords      ['.format(self.indent), end=' ', file=self.tobj.DBG_FILE)
            for k in self.chords:
                print('({}):{}'.format(k, self.chords[k]), end=', ', file=self.tobj.DBG_FILE)
            print(']', file=self.tobj.DBG_FILE)
        return (imap, imapKeys, imapNotes, chordKey)
    
    def updateChords(self, j, chordKey, imap, count, dbg=0):
        chordName = ''
        if chordKey in self.chords:
            chordName = self.chords[chordKey]
            count += 1
            if dbg: print('{}updateChords({}) index={} count={} FOUND key={} value={} in chords'.format(self.indent, self.c, j, count, chordKey, self.chords[chordKey]), file=self.tobj.DBG_FILE)
        else:
            if dbg: print('{}updateChords({}) index={} Key={} not in chords - calculating value'.format(self.indent, self.c, j, chordKey), file=self.tobj.DBG_FILE)
            chordName = self.getChordName(imap)
            if len(chordName) > 0:
                self.chords[chordKey] = chordName
                count += 1
                if dbg:
                    print('{}updateChords({}) index={} count={} ADDING Key={} value={} to chords'.format(self.indent, self.c, j, count, chordKey, self.chords[chordKey]), file=self.tobj.DBG_FILE)
                    print('{}chords      ['.format(self.indent), end=' ', file=self.tobj.DBG_FILE)
                    for k in self.chords:
                        print('({}):{}'.format(k, self.chords[k]), end=', ', file=self.tobj.DBG_FILE)
                    print(']', file=self.tobj.DBG_FILE)
            elif dbg: print('{}updateChords({}) index={} Key={} not a chord'.format(self.indent, self.c, j, chordKey), file=self.tobj.DBG_FILE)
        return chordName
    
    def add2Limap(self, imap, limap, chordName, dbg=1):
        if imap not in limap:
            if len(chordName) > 0:
                if dbg: self.dumpLimaps(imap, limap, chordName, 'printChord(add2Limap({})) prepend '.format(self.c))
                limap.insert(0, imap)
            else:
                if dbg: self.dumpLimaps(imap, limap, chordName, 'printChord(add2Limap({})) append '.format(self.c))
                limap.append(imap)
        elif len(chordName) > 0 and imap != limap[0]:
            if dbg: self.dumpLimaps(imap, limap, chordName, 'printChord(add2Limap({})) remove and prepend '.format(self.c))
            limap.remove(imap)
            limap.insert(0, imap)
        else:
            if dbg: self.dumpLimaps(imap, limap, chordName, 'printChord(add2Limap({})) append '.format(self.c))
            limap.append(imap)
        if dbg: self.tobj.dumpLimap(limap, reason='add2Limap({})'.format(self.c))
        return limap
    
    def dumpLimaps(self, imap, limap, chordName, reason):
        if chordName: print('{} chordName={} imap=['.format(reason, chordName), end=' ', file=self.tobj.DBG_FILE)
        else: print('{} imap=['.format(reason), end=' ', file=self.tobj.DBG_FILE)
        for k in imap: print('{}:{}'.format(k, imap[k]), end=' ', file=self.tobj.DBG_FILE)
        print('] to', end=' ', file=self.tobj.DBG_FILE)
        self.tobj.dumpLimap(limap, reason='dumpLimaps()')
    
    def printChordName(self, row, col, chordName, imap, bStyle='', dbg=0):
        print('printChordName() {:<7}, imap={}'.format(chordName, self.tobj.imap2String(imap)), file=self.tobj.DBG_FILE)
        if len(chordName) > 1 and ( chordName[1] == '#' or chordName[1] == 'b' ):
            chordName = chordName[0] + chordName[2:]
            if dbg: print('printChordName() strip # or b, name={}'.format(chordName), file=self.tobj.DBG_FILE)
        i, ddn, ddf, dds = 0, 0, 0, 0
        while i < len(chordName):
            style = self.tobj.styles['NAT_CHORD']
            if i == 0:
                style = self.tobj.getEnharmonicStyle(imap['R'], style, self.tobj.styles['FLT_CHORD'], self.tobj.styles['SHP_CHORD'])
                if dbg: print('printChordName() style={}'.format(style), file=self.tobj.DBG_FILE)
            elif chordName[i] == 'm':
                if i + 1 < len(chordName) and chordName[i+1] == 'M':
                    chordName = chordName[:i+1] + chordName[i+2:]
                    style = self.tobj.styles['SHP_CHORD']
                else: style = self.tobj.styles['FLT_CHORD']
            elif chordName[i] == 'n':
                chordName = chordName[:i] + chordName[i+1:]
                style = self.tobj.styles['NO_IVAL']
                if chordName[i] == '1': ddn = 1
            elif chordName[i] == 'b':
                chordName = chordName[:i] + chordName[i+1:]
                style = self.tobj.styles['FLT_CHORD']
                if chordName[i] == '1': ddf = 1
            elif chordName[i] == 'a' or chordName[i] == '#':
                chordName = chordName[:i] + chordName[i+1:]
                style = self.tobj.styles['SHP_CHORD']
                if chordName[i] == '1': dds = 1
            elif ddn: style = self.tobj.styles['NO_IVAL']
            elif ddf: style = self.tobj.styles['FLT_CHORD']
            elif dds: style = self.tobj.styles['SHP_CHORD']
            self.tobj.prints(chordName[i], i + row, col, bStyle + style)
            i += 1
            if i == self.tobj.CHORDS_LEN: break
        for i in range(i, self.tobj.CHORDS_LEN):
            self.tobj.prints(' ', i + row, col, self.tobj.styles['NAT_CHORD'])
        if dbg: print('printChordName({}) name={}'.format(self.c, chordName), file=self.tobj.DBG_FILE)
    
    def getChordName(self, imap):
        '''Calculate chord name.'''
        r = imap['R']
        if '5' in imap: 
            if len(imap) == 2:                                 return '{}5'.format(r)       # (Power)5
            elif 'M3' in imap:
                if len(imap) == 3:                             return '{}'.format(r)        # (Maj)
                elif len(imap) == 4:
                    if   'b7' in imap:                         return '{}7'.format(r)       # 7
                    elif  '7' in imap:                         return '{}M7'.format(r)      # Maj7
                    elif  '2' in imap:                         return '{}2'.format(r)       # add2
                    elif  '4' in imap:                         return '{}4'.format(r)       # add4
                    elif  '6' in imap:                         return '{}6'.format(r)       # add6
                elif len(imap) == 5:
                    if 'b7' in imap:
                        if    '2' in imap:                     return '{}9'.format(r)       # 9
                        elif 'b2' in imap:                     return '{}7b9'.format(r)     # 7b9
                        elif 'm3' in imap:                     return '{}7#9'.format(r)     # 7#9
                        elif  '4' in imap:                     return '{}11n9'.format(r)    # 11(no9)
                        elif  '6' in imap:                     return '{}13n9'.format(r)    # 13(no9)
                    elif '7' in imap:
                        if   '2' in imap:                      return '{}M9'.format(r)      # Maj9
                        elif '4' in imap:                      return '{}M11n9'.format(r)   # Maj11(no9)
                        elif '6' in imap:                      return '{}M13n9'.format(r)   # Maj13(no9)
                    elif '2' in imap and '6' in imap:          return '{}6/9'.format(r)     # 6add9
                elif len(imap) == 6:
                    if '2' in imap:
                        if 'b7' in imap:
                            if   '4' in imap:                  return '{}11'.format(r)      # 11
                            elif '6' in imap:                  return '{}13n11'.format(r)   # 13(no11)
                        elif '7' in imap:
                            if   '4' in imap:                  return '{}M11'.format(r)     # Maj11
                            elif '6' in imap:                  return '{}M13n11'.format(r)  # Maj13(no11)
            elif 'm3' in imap:
                if len(imap) == 3:                             return '{}m'.format(r)       # min
                elif len(imap) == 4:
                    if   'b7' in imap:                         return '{}m7'.format(r)      # min7
                    elif  '7' in imap:                         return '{}mM7'.format(r)     # minMaj7
                    elif  '2' in imap:                         return '{}m2'.format(r)      # minadd2
                    elif  '4' in imap:                         return '{}m4'.format(r)      # minadd4
                    elif  '6' in imap:                         return '{}m6'.format(r)      # minadd6
                elif len(imap) == 5:
                    if 'b7' in imap:
                        if  'b2' in imap:                      return '{}m7b9'.format(r)    # min7b9
                        elif '2' in imap:                      return '{}m9'.format(r)      # min9
                        elif '4' in imap:                      return '{}m11n9'.format(r)   # min11(no9)
                        elif '6' in imap:                      return '{}m13n9'.format(r)   # min13(no9)
                    elif '7' in imap:
                        if   '2' in imap:                      return '{}mM9'.format(r)     # minMaj9
                        elif '4' in imap:                      return '{}mM11n9'.format(r)  # minMaj11(no9)
                        elif '6' in imap:                      return '{}mM13n9'.format(r)  # minMaj13(no9)
                    elif '2' in imap:                          return '{}m6/9'.format(r)    # min6add9
                elif len(imap) == 6:
                    if '2' in imap:
                        if 'b7' in imap:
                            if   '4' in imap:                  return '{}m11'.format(r)     # min11
                            elif '6' in imap:                  return '{}m13n11'.format(r)  # min13(no11)
                        elif '7' in imap:
                            if   '4' in imap:                  return '{}mM11'.format(r)    # minMaj11
                            elif '6' in imap:                  return '{}mM13n11'.format(r) # minMaj13(no11)
            elif len(imap) == 3:
                if    '2' in imap:                             return '{}s2'.format(r)      # sus2
                elif  '4' in imap:                             return '{}s4'.format(r)      # sus4
            elif len(imap) == 4:
                if   'b7' in imap:
                    if    '2' in imap:                         return '{}7s2'.format(r)     # 7sus2
                    elif  '4' in imap:                         return '{}7s4'.format(r)     # 7sus4
                elif '7' in imap:
                    if    '2' in imap:                         return '{}M7s2'.format(r)    # Maj7sus2
                    elif  '4' in imap:                         return '{}M7s4'.format(r)    # Maj7sus4
                elif '2' in imap and '6' in imap:              return '{}6/9n3'.format(r)   # 6add9no3
            elif len(imap) == 5:
                if   'b7' in imap:
                    if 'b2' in imap and 'b5' in imap:          return '{}7b9#11n3'.format(r) # 7b9#11(no3)
        elif 'b5' in imap:
            if 'm3' in imap:
                if len(imap) == 3:                             return '{}o'.format(r)       # dim
                elif len(imap) == 4:
                    if   'b7' in imap:                         return '{}07'.format(r)      # halfdim7
                    elif  '6' in imap:                         return '{}o7'.format(r)      # dim7
                    elif  '2' in imap:                         return '{}o2'.format(r)      # dimadd2
                    elif  '4' in imap:                         return '{}o4'.format(r)      # dimadd4
                elif len(imap) == 5:
                    if   'b7' in imap:
                        if   '2' in imap:                      return '{}09'.format(r)      # halfdim9
                        elif '4' in imap:                      return '{}011n9'.format(r)   # halfdim11(no9)
                        elif '6' in imap:                      return '{}013n9'.format(r)   # halfdim13(no9)
                    elif '6' in imap:
                        if   '2' in imap:                      return '{}o9'.format(r)      # dim9
                        elif '4' in imap:                      return '{}o11n9'.format(r)   # dim11(no9)
                elif len(imap) == 6:
                    if '2' in imap:
                        if 'b7' in imap:
                            if   '4' in imap:                  return '{}011'.format(r)     # halfdim11
                            elif '6' in imap:                  return '{}013n11'.format(r)  # halfdim13(no11)
                        elif '6' in imap:
                            if   '4' in imap:                  return '{}o11'.format(r)     # dim11
            elif 'M3' in imap:
                if len(imap) == 4:
                    if 'b7' in imap:                           return '{}7b5'.format(r)     # 7dim5
            elif len(imap) == 4:
                if 'b7' in imap:
                    if '2' in imap:                            return '{}9#11n3n5'.format(r)  # 9#11(no5no3)
            elif len(imap) == 5:
                if 'b7' in imap:
                    if 'b2' in imap and '6' in imap:           return '{}13b9#11n5'.format(r) # 13b9#11(no5)
        elif 'a5' in imap:
            if 'M3' in imap:
                if len(imap) == 3:                             return '{}+'.format(r)       # aug
                elif len(imap) == 4:
                    if   'b7' in imap:                         return '{}+7'.format(r)      # aug7          7b13(no5)
                    elif  '7' in imap:                         return '{}+M7'.format(r)     # augMaj7       M7b13(no5)
                    elif  '2' in imap:                         return '{}+2'.format(r)      # augadd2
                    elif  '4' in imap:                         return '{}+4'.format(r)      # augadd4
                    elif  '6' in imap:                         return '{}+6'.format(r)      # augadd6
                elif len(imap) == 5:
                    if    'b7' in imap:
                        if   '2' in imap:                      return '{}+9'.format(r)      # aug9          9b13(no5)
                        elif 'b2' in imap:                     return '{}+7b9'.format(r)    # aug7b9        7b9b13(no5)
                        elif 'm3' in imap:                     return '{}+7#9'.format(r)    # aug7#9        7#9b13(no5)
                        elif '4' in imap:                      return '{}+11n9'.format(r)   # aug11(no9)
                        elif '6' in imap:                      return '{}+13n9'.format(r)   # aug13(no9)
                    elif  '7' in imap:
                        if   '2' in imap:                      return '{}+M9'.format(r)     # augMaj9
                        elif '4' in imap:                      return '{}+M11n9'.format(r)  # augMaj11(no9)
                        elif '6' in imap:                      return '{}+M13n9'.format(r)  # augMaj13(no9)
                elif len(imap) == 6:
                    if '2' in imap:
                        if 'b7' in imap:
                            if   '4' in imap:                  return '{}+11'.format(r)     # aug11
                            elif '6' in imap:                  return '{}+13n11'.format(r)  # aug13(no11)
                        elif '7' in imap:
                            if   '4' in imap:                  return '{}+M11'.format(r)    # augMaj11
                            elif '6' in imap:                  return '{}+M13n11'.format(r) # augMaj13(no11)
        # Maybe omit all the n5 (no 5th) chords for simplicity?
        elif 'M3' in imap:
            if len(imap) == 3:
                if   'b7' in imap:                             return '{}7n5'.format(r)     # 7(no5)
                elif  '7' in imap:                             return '{}M7n5'.format(r)    # Maj7(no5)
                elif  '2' in imap:                             return '{}2n5'.format(r)     # Maj2(no5)
                elif  '4' in imap:                             return '{}4n5'.format(r)     # Maj4(no5)
                elif  '6' in imap:                             return '{}6n5'.format(r)     # Maj6(no5)
            elif len(imap) == 4:
                if   'b7' in imap:
                    if   '2' in imap:                          return '{}9n5'.format(r)     # 9(no5)
                    elif 'b2' in imap:                         return '{}7b9n5'.format(r)   # 7b9(no5)
                    elif 'm3' in imap:                         return '{}7#9n5'.format(r)   # 7#9(no5)
                    elif '4' in imap:                          return '{}11n5'.format(r)    # 11(no5)
                    elif '6' in imap:                          return '{}13n5'.format(r)    # 13(no5)
                elif '7' in imap:
                    if   '2' in imap:                          return '{}M9n5'.format(r)    # Maj9(no5)
                    elif 'b2' in imap:                         return '{}M7b9n5'.format(r)  # Maj7b9(no5)
                    elif 'm3' in imap:                         return '{}M7#9n5'.format(r)  # Maj7#9(no5)
                    elif '4' in imap:                          return '{}M11n5'.format(r)   # Maj11(no5)
                    elif '6' in imap:                          return '{}M13n5'.format(r)   # Maj13(no5)
                elif '2' in imap and '6' in imap:              return '{}6/9n5'.format(r)   # Maj6add9(no5)
            elif len(imap) == 5:
                if   'b7' in imap:
                    if    '2' in imap and '6' in imap:         return '{}13n5'.format(r)    # 13(no5)
                    elif 'b2' in imap and '6' in imap:         return '{}13b9n5'.format(r)  # 13b9(no5)
        elif 'm3' in imap:
            if len(imap) == 3:
                if   'b7' in imap:                             return '{}m7n5'.format(r)    # min7(no5)
                elif  '7' in imap:                             return '{}mM7n5'.format(r)   # minMaj7(no5)
                elif  '2' in imap:                             return '{}m2n5'.format(r)    # min2(no5)
                elif  '4' in imap:                             return '{}m4n5'.format(r)    # min4(no5)
                elif  '6' in imap:                             return '{}m6n5'.format(r)    # min6(no5)
            elif len(imap) == 4:
                if   'b7' in imap:
                    if   '2' in imap:                          return '{}m9n5'.format(r)    # min9(no5)
                    elif '4' in imap:                          return '{}m11n5'.format(r)   # min11(no5)
                    elif '6' in imap:                          return '{}m13n5'.format(r)   # min13(no5)
                elif '7' in imap:
                    if   '2' in imap:                          return '{}mM9n5'.format(r)   # minMaj9(no5)
                    elif '4' in imap:                          return '{}mM11n5'.format(r)  # minMaj11(no5)
                    elif '6' in imap:                          return '{}mM13n5'.format(r)  # minMaj13(no5)
                elif '2' in imap and '6' in imap:              return '{}m6/9n5'.format(r)  # min6add9(no5)
            elif len(imap) == 5:
                if   'b7' in imap:
                    if   '2' in imap and '4' in imap:          return '{}m11n5'.format(r)   # m11(no5)
        else:
            if len(imap) == 3:
                if   'b7' in imap:
                    if   '2' in imap:                          return '{}7s2n5'.format(r)   # 7sus2(no5)
                    elif '4' in imap:                          return '{}7s4n5'.format(r)   # 7sus4(no5)
                elif '7' in imap:
                    if   '2' in imap:                          return '{}M7s2n5'.format(r)  # Maj7sus2(no5)
                    elif '4' in imap:                          return '{}M7s4n5'.format(r)  # Maj7sus4(no5)
        return ''
    
'''
Chord Naming Conventions:
| -----------------------------------------------------------------------------|
| Long      | Short | Intervals          | Indices          | Notes            |
| ----------|-------|--------------------|------------------|------------------|
| CMaj      | C     | R 3 5              | 0 4 7            | C E G            |
| CMin      | Cm    | R m3 5             | 0 3 7            | C Eb G           |
| CAug      | C+    | R 3 a5             | 0 4 8            | C E G#           |
| CDim      | Co    | R m3 b5            | 0 3 6            | C Eb Gb          |
| ----------|-------|--------------------|------------------|------------------|
| CMaj7     | CM7   | R 3 5 7            | 0 4 7 11         | C E G B          |
| CDom7     | C7    | R 3 5 b7           | 0 4 7 10         | C E G Bb         |
| CMin7     | Cm7   | R m3 5 b7          | 0 3 7 10         | C Eb G Bb        |
| CMinMaj7  | CmM7  | R m3 5 7           | 0 3 7 11         | C Eb G B         |
| CAugMaj7  | C+M7  | R 3 a5 7           | 0 4 8 11         | C E G# B         |
| CAug7     | C+7   | R 3 a5 b7          | 0 4 8 10         | C E G# Bb        |
| CHDim7    | C07   | R m3 b5 b7         | 0 3 6 10         | C Eb Gb Bb       |
| CDim7     | Co7   | R m3 b5 bb7        | 0 3 6 9          | C Eb Gb Bbb      |
| C7Dim5    | C7b5  | R 3 b5 b7          | 0 4 6 10         | C E Gb Bb        |
| ----------|-------|--------------------|------------------|------------------|
| CMaj9     | CM9   | R 3 5 7 9          | 0 4 7 11 14      | C E G B D        |
| CDom9     | C9    | R 3 5 b7 9         | 0 4 7 10 14      | C E G Bb D       |
| CMinMaj9  | CmM9  | R m3 5 7 9         | 0 3 7 11 14      | C Eb G B D       |
| CMinDom9  | Cm9   | R m3 5 b7 9        | 0 3 7 10 14      | C Eb G Bb D      |
| CAugMaj9  | C+M9  | R 3 a5 7 9         | 0 4 8 11 14      | C E G# B D       |
| CAugDom9  | C+9   | R 3 a5 b7 9        | 0 4 8 10 14      | C E G# Bb D      |
| CHDim9    | C09   | R m3 b5 b7 9       | 0 3 6 10 14      | C Eb Gb Bb D     |
| CHDimMin9 | C0b9  | R m3 b5 b7 9b      | 0 3 6 10 13      | C Eb Gb Bb Db    |
| CDim9     | Co9   | R m3 b5 bb7 9      | 0 3 6 9 14       | C Eb Gb Bbb D    |
| CDimMin9  | Cob9  | R m3 b5 bb7 b9     | 0 3 6 9 13       | C Eb Gb Bbb Db   |
| ----------|-------|--------------------|------------------|------------------|
| CMaj11    | CM11  | R 3 5 7 9 11       | 0 4 7 11 14 17   | C E G B D F      |
| CDom11    | C11   | R 3 5 b7 9 11      | 0 4 7 10 14 17   | C E G Bb D F     |
| CMinMaj11 | CmM11 | R m3 5 7 9 11      | 0 3 7 11 14 17   | C Eb G B D F     |
| CMin11    | Cm11  | R m3 5 b7 9 11     | 0 3 7 10 14 17   | C Eb G Bb D F    |
| CAugMaj11 | C+M11 | R 3 a5 7 9 11      | 0 4 8 11 14 17   | C E G# B D F     |
| CAug11    | C+11  | R 3 a5 b7 9 11     | 0 4 8 10 14 17   | C E G# Bb D F    |
| CHDim11   | C011  | R m3 b5 b7 b9 11   | 0 3 6 10 13 17   | C Eb Gb Bb Db F  |
| CDim11    | Co11  | R m3 b5 bb7 b9 b11 | 0 3 6 9 13 17    | C Eb Gb Bbb Db F |
| ----------|-------|--------------------|------------------|------------------|
| CMaj13    | CM13  | R 3 5 7 9 11 13    | 0 4 7 11 14 17 21| C E G B D F A    |
| CDom13    | C13   | R 3 5 b7 9 11 13   | 0 4 7 10 14 17 21| C E G Bb D F A   |
| CMinMaj13 | CmM13 | R m3 5 7 9 11 13   | 0 3 7 11 14 17 21| C Eb G B D F A   |
| CMinDom13 | Cm13  | R m3 5 b7 9 11 13  | 0 3 7 10 14 17 21| C Eb G Bb D F A  |
| CAugMaj13 | C+M13 | R 3 a5 7 9 11 13   | 0 4 8 11 14 17 21| C E G# B D F A   |
| CAugDom13 | C+13  | R 3 a5 b7 9 11 13  | 0 4 8 10 14 17 21| C E G# Bb D F A  |
| CHDim13   | C013  | R m3 b5 b7 9 11 13 | 0 3 6 10 14 17 21| C Eb Gb Bb D F A |
| ----------|-------|--------------------|------------------|------------------|
| CPower5   | C5    | R 5                | 0 7              | C G              |
| C7no3     | C7n3  | R 5 7b             | 0 7 10           | C G Bb           |
| ----------|-------|--------------------|------------------|------------------|
| Csus2     | Cs2   | R 2 5              | 0 2 7            | C D G            |
| C7sus2    | C7s2  | R 2 5 b7           | 0 2 7 10         | C D G Bb         |
| C9sus2    | C9s2  | R 2 5 b7 9         | 0 2 7 10 14      | C D G Bb D       |
| Csus4     | Cs4   | R 4 5              | 0 5 7            | C F G            |
| C7sus4    | C7s4  | R 4 5 b7           | 0 5 7 10         | C F G Bb         |
| C9sus4    | C9s4  | R 4 5 b7 9         | 0 5 7 10 14      | C F G Bb D       |
| ----------|-------|--------------------|------------------|------------------|
| Cadd9     | C2    | R 2 3 5            | 0 2 4 7          | C D E G          |
| Cadd11    | C4    | R 3 4 5            | 0 4 5 7          | C E F G          |
| Cadd13    | C6    | R 3 5 6            | 0 4 7 9          | C E G A          |
| CAdd6Add9 | C6/9  | R 3 5 6 9          | 0 4 7 9 14       | C E G A D        |
| -----------------------------------------------------------------------------|
'''
