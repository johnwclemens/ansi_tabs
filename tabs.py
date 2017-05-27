'''tabs.py module.  Main entry point, class list: [Tabs].  Note the user simply instantiates this object and this object handles the entire tabs session.'''

'''Thus all methods are essentially private.  Note some functionality is deemed customizable by the user and is thus factored out into a separate module.  
e.g. The tab modifications are in mods.py, the string tunings and aliases are in strings.py, and the chord discovery and name calculations are in chords.py.'''

import os, inspect, sys

impFile = open('tabs_imp.log', 'w')

'''Lame attempt at portability.  Should work on Windows, might work on Linux.'''
try:
    print('try: import tty, termios', file=impFile)
    impFile.flush()
    import tty, termios
except ImportError as e:
    print('ERROR! e={}, import tty, termios failed'.format(e), file=impFile)
    impFile.flush()
    try:
        print('try: import msvcrt', file=impFile)
        impFile.flush()
        import msvcrt
    except ImportError as e:
        print('ERROR! e={}, import msvcrt failed, getch not available'.format(), file=impFile)
        impFile.flush()
        raise ImportError('ERROR! e={}, import msvcrt failed, getch not available'.format(e))
    else:
        getch   = msvcrt.getch
        getche  = msvcrt.getche
        kbhit   = msvcrt.kbhit
        getwch  = msvcrt.getwch
        getwche = msvcrt.getwche
        print('getwch={}'.format(getwch), file=impFile)
        impFile.flush()
else:
    print('import tty, termios OK, define getch()', file=impFile)
    impFile.flush()
    def getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch
    print('getch={}'.format(getch), file=impFile)
    impFile.flush()

import colorama
import cmdArgs
import chords
import mods
import notes
import strings

class Tabs(object):
    '''Model musical tab notation and tab editor functionality.'''
    ESC = '\033'
    CSI = '\033\133'
    QUIT_STR = 'Received Quit Cmd: Exiting'
    
    def __init__(self, inName='tabs.tab', outName='tabs.tab', dbgName='dbg.tab'):
        '''Initialize the Tabs object and start the interactive loop method.  The inName and outName can be the same or different.'''
        self.init(inName, outName, dbgName)
        self.loop()

    def init(self, inName='tabs.tab', outName='tabs.tab', dbgName='dbg.tab'):
        '''Initialize class instance, enable automatic reset of console after each call via implicit print(colorama.Style.RESET_ALL).'''
        colorama.init(autoreset=True)
        self.clearScreen()

        self.initFiles(inName, outName, dbgName)
        self.initConsts()
        self.registerUiCmds()                                  # register the dictionary for all the user interactive commands
        self.mods = {}                                         # dict of tab modification characters -> contextual descriptions 
        self.dbgMove = True                                    # used for finding bugs in basic movement functionality
        self.capo = ord('0')                                   # essentially added to every tab that is a fret, written to the outFile and read from the inFile
        self.maxFret = ord('0')                                # update in setTab() and readTabs()
        self.chordsObj = None                                  # the chords.Chords instance
        
        self.htabs = []                                        # list of bytearrays, one for each string; for harmonic tabs
        self.tabCount = 0                                      # used by appendTabs() 
        self.tabs = []                                         # list of bytearrays, one for each string; for all the tabs
        
        self.selectFlag = 0                                    # used to un-hilite selected rows
        self.selectTabs = []                                   # list of bytearrays, one for each string; for selected tabs
        self.selectHTabs = []                                  # list of bytearrays, one for each string; for selected tabs
        self.selectRows = []                                   # list of row    indices, one for each selected row;    for selected rows
        self.selectCols = []                                   # list of column indices, one for each selected column; for selected columns
        self.stringMap = {}                                    # dict of string note name -> note index
        self.stringKeys = []                                   # list of keys; stringMap keys sorted by note index
        self.numStrings = 1                                    # number of strings on the musical instrument, set here in case initStrings() fails

        self.numLines = 1                                      # number of music lines to display
        self.numTabsPerStringPerLine = 10                      # number of tabs to display on each line (for each string)
        self.numTabsPerString = self.numLines * self.numTabsPerStringPerLine  # total number of tabs per string
        
        self.ROW_OFF = 1                                       # offset between cursor row    number and tabs row    index
        self.COL_OFF = 3                                       # offset between cursor column number and tabs column index
        self.CHORDS_LEN = 0                                    # number of rows used to display chords
        self.NOTES_LEN = 0                                     # number of rows used to display notes
        self.NUM_FRETS = 24                                    # number of frets, (might make this a list for all the strings)?
      
        self.hiliteCount = 0                                   # statistic for measuring efficiency
        self.hiliteColNum = 0                                  # used to hilite the current cursor column and unhilite the previous cursor column
        self.hiliteRowNum = 0                                  # used to hilite the current cursor row    and unhilite the previous cursor row
        self.hilitePrevRowPos = 0
        self.row = self.ROW_OFF                                # current cursor row    number
        self.col = self.COL_OFF                                # current cursor column number
        self.editModeCol = 1                                   # column to display edit mode
        self.cursorModeCol = 2                                 # column to display cursor mode
        self.lastRow = self.ROW_OFF + self.numLines * self.lineDelta() - 1  # the row used to display status, set here in case initStrings() fails e.g. tab mod info or error info etc...
        
        self.displayLabels = self.DISPLAY_LABELS['DISABLED']   # enable or disable the display of the modes and labels section before each line
        self.displayNotes = self.DISPLAY_NOTES['DISABLED']     # enable or disable the display of the notes section for each line
        self.displayChords = self.DISPLAY_CHORDS['DISABLED']   # enable or disable the display of the chords section for each line
        self.cursorDir = self.CURSOR_DIRS['DOWN']              # affects the automatic cursor movement (up/down) when entering a tab in chord or arpeggio mode
        self.enharmonic = self.ENHARMONIC['SHARP']             # toggle to display enharmonic notes using flats or sharps
        self.editMode = self.EDIT_MODES['REPLACE']             # toggle between modifying the current character or inserting a new character
        self.cursorMode = self.CURSOR_MODES['MELODY']          # toggle between different cursor modes; melody, chord, and arpeggio
        
        argMap = {}
        cmdArgs.parseCmdLine(argMap)
        print('tabs.py args={}'.format(argMap), file=self.dbgFile)
        if 'f' in argMap and len(argMap['f']) > 0:
            self.inName = argMap['f'][0]                       # file to read from
            self.outName = argMap['f'][0]                      # file to write to, only written to with the saveTabs command
        if 't' in argMap and len(argMap['t']) > 0:
            self.initTabLen(argMap['t'])                       # set number of tabs/columns per line (and per string)
        if 'S' in argMap and len(argMap['S']) > 0:
            self.initStrings(alias=argMap['S'])                # set string tuning with alias 
        elif 's' in argMap and len(argMap['s']) > 0:
            self.initStrings(spelling=argMap['s'])             # set string tuning with string spelling
        else:
            self.initStrings()                                 # set default string tuning
        self.setLastRow()                                      # calculate last row, depends on numStrings which is supposed to be set in initStrings()
        self.numTabs = self.numStrings * self.numTabsPerString # total number of tab characters

        try:
            with open(self.inName, 'rb') as self.inFile:
                self.readTabs(readSize=500)
        except Exception as e: # FileNotFoundError as e:
            print('init() Exception: {}'.format(e), file=self.dbgFile)
            mult = 1
            tabs = '0123456789abcdefghijklmno'
            print('init() seeding tabs with \'{}\', len(tabs):{}, numTabsPerString:{} = numLines:{} * numTabsPerStringPerLine:{}'.format(tabs, len(tabs), self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine), file=self.dbgFile)
            if len(tabs) > self.numTabsPerStringPerLine: 
                tabs = tabs[:self.numTabsPerStringPerLine]
                print('init() truncated tabs to \'{}\', setting tabs = tabs[:self.numTabsPerStringPerLine], len(tabs):{} * mult:{} = {}'.format(tabs, len(tabs), mult, len(tabs) * mult), file=self.dbgFile)
            else: 
                print('init() setting tabs len'.format(), file=self.dbgFile)
                for i in range(len(tabs) - 1, -1, -1):
                    print('init() i={}'.format(i), file=self.dbgFile)
                    if not (self.numTabsPerStringPerLine % i):
                        tabs = tabs[:i]
                        mult = int(self.numTabsPerStringPerLine / i)
                        break
                print('init() truncated tabs to \'{}\', setting tabs = tabs[:mult], len(tabs):{} * mult:{} = {}'.format(tabs, len(tabs), mult, len(tabs) * mult), file=self.dbgFile)
            for r in range(0, self.numStrings):
                self.tabs.append(bytearray([ord(t) for t in tabs] * mult))
                self.htabs.append(bytearray([ord('0') for t in tabs] * mult))
        finally:
            self.modsObj = mods.Mods(self)
            self.mods = self.modsObj.getMods()
            print('init() mods=\{ ', file=self.dbgFile)
            for k in self.mods:
                print('{}:{}, '.format(k, self.mods[k]), file=self.dbgFile)
            if 'F' in argMap and len(argMap['F']) == 0:
                self.toggleEnharmonic()                        # toggle enharmonic note display from sharp to flat
            if 'i' in argMap and len(argMap['i']) == 0:
                self.toggleCursorDir(dbg=1)                    # toggle automatic cursor movement direction from down to up
            if 'k' in argMap and len(argMap['k']) > 0:
                self.setCapo(c=argMap['k'][0])                 # set capo at desired fret
            if 'a' in argMap and len(argMap['a']) == 0:
                self.toggleDisplayLabels(printTabs=False)      # toggle the display of the edit mode, cursor mode, and column number labels in first row for each line
            if 'b' in argMap and len(argMap['b']) == 0:
                self.toggleDisplayChords(printTabs=False)      # enable the chords section display
            if 'n' in argMap and len(argMap['n']) == 0:
                self.toggleDisplayNotes(printTabs=False)       # enable the notes section display
            if 'l' in argMap and len(argMap['l']) == 0:
                self.goToLastTab(cs=1)                         # go to last tab on current line of current string
            if 'L' in argMap and len(argMap['L']) == 0:
                self.goToLastTab()                             # go to last tab on current line of all strings
            if 'z' in argMap and len(argMap['z']) == 0:
                self.goToLastTab(cs=1, ll=1)                   # go to last tab on last line of current string
            if 'Z' in argMap and len(argMap['Z']) == 0:
                self.goToLastTab(ll=1)                         # go to last tab on last line of all strings
            if 'h' in argMap and len(argMap['h']) == 0:
                self.printHelpInfo()                           # display the help info
            self.printTabs()                                   # display all the tabs in the tabs section, optionally display the notes and chords sections and the modes/labels row
            self.moveTo(hi=1)                                  # display the status and hilite the first tab character
 
    def testAnsi(self):
        file = open('testAnsi.tab', 'w')
        self.clearScreen(file=file)
        print(self.CSI + self.styles['TABS']       + self.CSI + '{};{}H{}'.format(1, 1, 'TABS'), file=file)
        print(self.CSI + self.styles['H_TABS']     + self.CSI + '{};{}H{}'.format(1, 20, 'H_TABS!'), file=file)
        print(self.CSI + self.styles['NAT_NOTE']   + self.CSI + '{};{}H{}'.format(2, 1, 'NAT_NOTE'), file=file)
        print(self.CSI + self.styles['NAT_H_NOTE'] + self.CSI + '{};{}H{}'.format(2, 20, 'NAT_H_NOTE'), file=file)
        print(self.CSI + self.styles['FLT_NOTE']   + self.CSI + '{};{}H{}'.format(3, 1, 'FLT_NOTE'), file=file)
        print(self.CSI + self.styles['FLT_H_NOTE'] + self.CSI + '{};{}H{}'.format(3, 20, 'FLT_H_NOTE'), file=file)
        print(self.CSI + self.styles['SHP_NOTE']   + self.CSI + '{};{}H{}'.format(4, 1, 'SHP_NOTE'), file=file)
        print(self.CSI + self.styles['SHP_H_NOTE'] + self.CSI + '{};{}H{}'.format(4, 20, 'SHP_H_NOTE'), file=file)
        self.quit('testAnsi()')
     
    def initFiles(self, inName, outName, dbgName):
        self.dbgFile = open(dbgName, "w")
        self.inName = inName
        self.inFile = None
        self.outName = outName
        self.outFile = None
        
    def initConsts(self): # foreground 30-37, background 40-47, 0=black, 1=red, 2=green, 3=yellow, 4= blue, 5=magenta, 6=cyan, 7=white
        self.styles = { 'NAT_NOTE':'32;47m', 'NAT_H_NOTE':'37;43m', 'NAT_CHORD':'37;46m', 'MIN_COL_NUM':'32;40m',   'TABS':'32;40m', 'NUT_UP':'31;43m', 'NORMAL':'22;',
                        'FLT_NOTE':'34;47m', 'FLT_H_NOTE':'34;43m', 'FLT_CHORD':'34;46m', 'MAJ_COL_NUM':'33;40m', 'H_TABS':'33;40m', 'NUT_DN':'34;43m', 'BRIGHT':'1;',
                        'SHP_NOTE':'31;47m', 'SHP_H_NOTE':'31;43m', 'SHP_CHORD':'31;46m',      'STATUS':'37;40m',  'MODES':'34;47m',  'ERROR':'31;43m',   'CONS':'37;40m' }
        self.INTERVALS = { 0:'R',  1:'b2',  2:'2',  3:'m3',  4:'M3',  5:'4',   6:'b5',  7:'5',  8:'a5',  9:'6',  10:'b7', 11:'7', 
                          12:'R', 13:'b9', 14:'9', 15:'m3', 16:'M3', 17:'11', 18:'b5', 19:'5', 20:'a5', 21:'13', 22:'b7', 23:'7',
                          24:'R', 25:'b9', 26:'9', 27:'m3', 28:'M3', 29:'11', 30:'b5', 31:'5', 32:'a5', 33:'13', 34:'b7', 35:'7', 
                          36:'R', 37:'b9', 38:'9', 39:'m3', 40:'M3', 41:'11', 42:'b5', 43:'5', 44:'a5', 45:'13', 46:'b7', 47:'7', 48:'R' }
        self.HARMONIC_FRETS = { 12:12, 7:19, 19:19, 5:24, 24:24, 4:28, 9:28, 16:28, 28:28 }
#        self.FRET_INDICES = { 0:0, 1:1, 2:2, 3:3, 4:4, 5:5, 6:6, 7:7, 8:8, 9:9, 10:'a' }  # for moving along the fretboard?
#        self.MAJ_INDICES = [ 0, 2, 4, 5, 7, 9, 11, 12 ]                                   # for key signatures and or scales?
#        self.MIN_INDICES = [ 0, 2, 3, 5, 7, 8, 10, 12 ]                                   # for key signatures and or scales?
        self.CURSOR_DIRS = { 'DOWN':0, 'UP':1 }
        self.CURSOR_MODES = { 'MELODY':0, 'CHORD':1, 'ARPEGGIO':2 }
        self.EDIT_MODES = { 'REPLACE':0, 'INSERT':1 }
        self.ENHARMONIC = { 'SHARP':0, 'FLAT':1 }
        self.DISPLAY_LABELS = { 'DISABLED':0, 'ENABLED':1 }
        self.DISPLAY_NOTES = { 'DISABLED':0, 'ENABLED':1 }
        self.DISPLAY_CHORDS = { 'DISABLED':0, 'ENABLED':1 }
    
    def initStrings(self, alias=None, spelling=None):
        print('initStrings(alias={}, spelling={})'.format(alias, spelling), file=self.dbgFile)
        try:
            self.strings = strings.Strings(self.dbgFile, alias=alias, spelling=spelling)
        except Exception as ex:
            e = sys.exc_info()[0]
            info = 'initStrings() Exception: \'{}\', e={}'.format(ex, str(e))
            self.quit(info, code=1)
        self.stringMap = self.strings.map
        self.stringKeys = self.strings.keys
        self.numStrings = len(self.stringKeys)
        if len(self.strings.map) < 1:
            print('initStrings() ERROR! invalid stringMap, numStrings={}'.format(self.numStrings), file=self.dbgFile)
            self.quit('initStrings() ERROR! Empty stringMap!', code=1)
        print('initStrings() map = {', end='', file=self.dbgFile)
        for k in self.stringKeys:
            print(' {}:{}'.format(k, self.stringMap[k]), end='', file=self.dbgFile)
        print(' }', file=self.dbgFile)
    
    def initTabLen(self, numTabs):
        self.numTabsPerStringPerLine = int(numTabs[0])
        self.numTabsPerString = self.numLines * self.numTabsPerStringPerLine
        print('initTabLen() numTabsPerString:{} = numLines:{} * numTabsPerStringPerLine:{}'.format(self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine), file=self.dbgFile)
        
    def initInFile(self):
        self.inFile.seek(0, 2)
        fileSize = self.inFile.tell()
        self.inFile.seek(0, 0)
        return fileSize
    
    '''
                                                                                                   1         1         1         1         1         1         1         1         1         1         2         2         2
         1         2         3         4         5         6         7         8         9         0         1         2         3         4         5         6         7         8         9         0         1         2
1234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890
[40m[32m[2;1H1[40m[32m[2;2H|[40m[32m[2;3H0[40m[32m[2;4H1[40m[32m[2;5H2[40m[32m[2;6H3[40m[32m[2;7H4[40m[32m[2;8H5[40m[32m[2;9H6
    '''

    def readTabs(self, readSize=600):
        dbg = 1
        fileSize = self.initInFile()
        tmp, htmp = [], []
        cnt, bytesRead, bgnTabs, endTabs, hasFrag, rowStr = 0, 0, None, None, False, '{}'.format(self.ROW_OFF)
        data = self.inFile.read(readSize)
        if not len(data) or not fileSize:
            info = 'readTabs({}) ERROR! Invalid input file: file={} fileSize {:,} bytes, readSize {:,}, len(data)={}, data={}'.format(rowStr, self.inFile, fileSize, readSize, len(data), data) 
            print(info, file=self.dbgFile)
            raise Exception(info)
        print('readTabs({}) fileSize {:,} bytes, reading first {:,} bytes:\'\n{}\''.format(rowStr, fileSize, readSize, ''.join([chr(data[p]) for p in range(0, readSize)])), file=self.dbgFile)
        while len(data) != 0:
            bytesRead += len(data)
            i, bgn, fragment, end = 0, 0, b'', len(data)
            while i != -1:
                ii = i
                cnt += 1
                i = data.find(ord('H'), bgn, end)
                if i == -1 or i + 1 >= len(data):
                    fragment += data[ii+2:end]
                    hasFrag = True
                    if dbg: print('readTabs({}) detected fragment, len={} \'{}\' ii={}, p1={}, p2={}, i={}, bgn={}'.format(rowStr, len(fragment), ''.join([chr(fragment[p]) for p in range(0, len(fragment))]), ii, p1, p2, i, bgn), file=self.dbgFile)
                else:
                    p2 = data.rfind(ord(';'), i-4, i)
                    p1 = data.rfind(ord('['), i-7, p2) + 1
                    row = ''.join([chr(data[p]) for p in range(p1, p2)])
                    col = ''.join([chr(data[p]) for p in range(p2+1, i)])
                    if data[p1-3] == ord('m') and data[p1-6] == ord(';'):
                        s2 = ''.join([chr(data[p]) for p in range(p1-5, p1-3)])
                        if data[p1-9] == ord('['):
                            s1 = ''.join([chr(data[p]) for p in range(p1-8, p1-6)])
                            if s1 == self.styles['H_TABS'][0:2] and s2 == self.styles['H_TABS'][3:5]:
                                print('readTabs() s1={} & s2={} matched harmonic tab style r={}, c={}, {}'.format(s1, s2, (int(rowStr) - self.ROW_OFF) % self.numStrings, int(col) - self.COL_OFF, len(self.htabs)), file=self.dbgFile)
                                htmp.append(ord('1'))
                            else:
                                htmp.append(ord('0'))
                    z1 = data.find(ord('<'), bgn, p1)
                    z2 = data.find(ord('>'), z1, p1)
                    if z1 != -1 and z2 != -1 and data[z1+1:z2] == b'BGN_TABS_SECTION':
                        bgnTabs = data[z1+1:z2]
                        print('readTabs() found {} mark at z1,z2={},{}'.format(bgnTabs, z1, z2), file=self.dbgFile)
                        z = data.find(ord('c'), bgn, z1)
                        if z != -1:
                            zName = ''.join([chr(data[p]) for p in range(z, z+len('capo'))])
                            zLen = len(zName)
                            print('readTabs() found name={} at z={} with len={}!'.format(zName, z, zLen), file=self.dbgFile)
                            if zName == 'capo' and chr(data[z+zLen]) == '=':
                                z += zLen + 1
                                self.capo = ord(data[z:z+1])
                                print('readTabs() parsing capo, raw value={}, setting capo={}'.format(data[z:z+1], self.capo), file=self.dbgFile)
                    if bgnTabs:
                        tab = chr(data[i+1])
                        tmp.append(data[i+1])
                        if self.isFret(tab):
                            tabFN = self.getFretNum(ord(tab))
                            maxFN = self.getFretNum(self.maxFret)
                            if tabFN > maxFN: 
                                self.maxFret = ord(tab)
                                print('readTabs() updating chr(mf)={}, maxFret={}, maxFN={}'.format(chr(self.maxFret), self.maxFret, self.getFretNum(self.maxFret)), file=self.dbgFile)
                        if hasFrag:
                            print('readTabs({}) {} {} [{},{}], ii={}, p1={}, p2={}, i={}, bgn={} {} \'{}\' data=\'{}\' tmp=\'{}\''.format(rowStr, cnt, len(fragment), row, col, ii, p1, p2, i, bgn, hasFrag, tab, ''.join([chr(data[p]) for p in range(ii, i+2)]), ''.join([chr(tmp[p]) for p in range(0, len(tmp))])), file=self.dbgFile)
                            hasFrag = False
                        elif dbg:
                            print('readTabs({}) {} {} [{},{}], ii={}, p1={}, p2={}, i={}, bgn={} {} \'{}\' data=\'{}\' tmp=\'{}\''.format(rowStr, cnt, len(fragment), row, col, ii, p1, p2, i, bgn, hasFrag, tab, ''.join([chr(data[p]) for p in range(ii+2, i+2)]), ''.join([chr(tmp[p]) for p in range(0, len(tmp))])), file=self.dbgFile)
                        z1 = data.find(ord('<'), bgn, p1)
                        z2 = data.find(ord('>'), z1, p1)
                        if z1 != -1 and z2 != -1 and data[z1+1:z2] == b'END_TABS_SECTION':
                            endTabs = data[z1+1:z2]
                            print('readTabs() found {} mark at z1,z2={},{}'.format(endTabs, z1, z2), file=self.dbgFile)
                            break
                        elif self.numTabsPerStringPerLine == 0 and int(row) == self.ROW_OFF + 1:
                            self.numTabsPerStringPerLine = cnt - self.COL_OFF
                            self.numTabsPerString = self.numLines * self.numTabsPerStringPerLine
                            tmp, htmp, rowStr = self.appendTabs(tmp, htmp, rowStr)
                            tmp.append(data[i + 1])
                            if dbg: print('readTabs({}) {} [{},{}] \'{}\' setting numTabsPerStringPerLine={} tmp=\'{}\''.format(rowStr, cnt, row, col, tab, self.numTabsPerStringPerLine, ''.join([chr(tmp[p]) for p in range(0, len(tmp))])), file=self.dbgFile)
                        elif self.isTab(tab) and self.numTabsPerStringPerLine != 0 and int(col) == self.COL_OFF - 1 + self.numTabsPerStringPerLine:# and len(tmp) > 1 and tmp[1] == '|':
                            tmp, htmp, rowStr = self.appendTabs(tmp, htmp, rowStr)
                    else:
                        info = 'readTabs() prior to bgnTabs!'
                        quit(info)
                bgn = i + 2
            if endTabs: break
            data = self.inFile.read(readSize)
            dataLen = len(data)
            if dataLen == 0:
                print('readTabs() No more data to read from inFile, fragment: \'{}\''.format(''.join([chr(fragment[p]) for p in range(0, len(fragment))])), file=self.dbgFile)
                break
            data = fragment + data
            if dbg: print('readTabs() bytes read {:,}, reading next {:,} bytes and appending to fragment of len {} bytes ({:,} bytes):\n{}'.format(bytesRead, dataLen, len(fragment), dataLen + len(fragment), ''.join([chr(data[p]) for p in range(0, len(data))])), file=self.dbgFile)
        print('readTabs() numStrings:{} =?= len(tabs):{}, numTabsPerString:{} =?= numLines:{} * numTabsPerStringPerLine:{}, totTabs:{}'.format(
            self.numStrings, len(self.tabs), self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, len(self.tabs) * len(self.tabs[0])), file=self.dbgFile)
        self.dumpTabs('readTabs()')
        self.dumpTabs('readTabs(h)', h=1)

    def appendTabs(self, tmp, htmp, rowStr):
        rowStr = '{}'.format(int(rowStr) + 1)
        tabDataRow = tmp[self.COL_OFF-1 : self.COL_OFF-1 + self.numTabsPerStringPerLine]
        htabDataRow = htmp[self.COL_OFF-1 : self.COL_OFF-1 + self.numTabsPerStringPerLine]
        self.tabCount += len(tabDataRow)
        print('appendTabs({}) checking  \'{}\' , numTabsPerString={}, numLines={}, numTabsPerStringPerLine={}, tabCount={}'.format(rowStr, ''.join([chr(t) for t in tabDataRow]), self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.tabCount), file=self.dbgFile)
        if self.tabCount > self.numStrings * self.numTabsPerStringPerLine:
            if self.tabCount == (self.numStrings + 1) * self.numTabsPerStringPerLine or self.tabCount == (2 * self.numStrings + 1) * self.numTabsPerStringPerLine:
                self.appendLine(printTabs=False)
            if int(rowStr) - (self.numLines - 1) * self.numStrings - self.ROW_OFF <= self.numStrings:
                r = (int(rowStr) - self.ROW_OFF - 1) % self.numStrings
                for c in range(0, len(tabDataRow)):
                    self.tabs[r][c + (self.numLines - 1) * self.numTabsPerStringPerLine] = tabDataRow[c]
                    self.htabs[r][c + (self.numLines - 1) * self.numTabsPerStringPerLine] = ord('0')
                print('appendTabs({},{}) appending \'{}\' to tabs[line={}, string={}], numTabsPerString={}, numLines={}, numTabsPerStringPerLine={}, tabCount={}'.format(rowStr, r, ''.join([chr(t) for t in tabDataRow]), self.numLines, '{}'.format(int(rowStr) - (self.numLines-1)*self.numStrings - self.ROW_OFF), self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.tabCount), file=self.dbgFile)
        else:
            self.tabs.append(tabDataRow)
            self.htabs.append(htabDataRow)
            print('appendTabs({}) appending \'{}\' to tabs[line={}, string={}], numTabsPerString={}, numLines={}, numTabsPerStringPerLine={}, tabCount={}'.format(rowStr, ''.join([chr(t) for t in tabDataRow]), self.numLines, '{}'.format(int(rowStr) - self.ROW_OFF), self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.tabCount), file=self.dbgFile)
        tmp, htmp = [], []
        return [tmp, htmp, rowStr]
        
    def appendLine(self, printTabs=True):
        '''Append another line of tabs to the display.'''
        tabs, htabs = [], []
        print('appendLine(old) numTabsPerString:{} = numLines:{} * numTabsPerStringPerLine:{}, numTabs:{} = numStrings:{} * len(tabs[0]):{}'.format(self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.numTabs, self.numStrings, len(self.tabs[0])), file=self.dbgFile)
        self.numLines += 1
        self.numTabsPerString = self.numLines * self.numTabsPerStringPerLine
        for r in range(0, self.numStrings):
            tabs.append(bytearray([ord('-')] * self.numTabsPerString))
            htabs.append(bytearray([0] * self.numTabsPerString))
            for c in range(0, len(self.tabs[r])):
                tabs[r][c] = self.tabs[r][c]
                htabs[r][c] = self.htabs[r][c]
        self.htabs = htabs
        self.tabs = tabs
        self.setLastRow()
        count = 0
        for r in range(0, self.numStrings):
            count += len(self.tabs[r])
        self.numTabs = count
        print('appendLine(new) numTabsPerString:{} = numLines:{} * numTabsPerStringPerLine:{}, numTabs:{} = numStrings:{} * len(tabs[0]):{}'.format(self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.numTabs, self.numStrings, len(self.tabs[0])), file=self.dbgFile)
        if printTabs:
            self.printTabs()

    def removeLine(self):
        '''Remove last line of tabs from the display.'''
        tabs, htabs = [], []
        print('removeLine(old) numTabsPerString:{} = numLines:{} * numTabsPerStringPerLine:{}, numTabs:{} = numStrings:{} * len(tabs[0]):{}'.format(self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.numTabs, self.numStrings, len(self.tabs[0])), file=self.dbgFile)
        self.numLines -= 1
        self.numTabsPerString = self.numLines * self.numTabsPerStringPerLine
        for r in range(0, self.numStrings):
            tabs.append(bytearray([ord('-')] * self.numTabsPerString))
            htabs.append(bytearray([ord('0')] * self.numTabsPerString))
            for c in range(0, self.numTabsPerString):
                tabs[r][c] = self.tabs[r][c]
                htabs[r][c] = self.htabs[r][c]
        self.tabs = tabs
        self.htabs = htabs
        self.setLastRow()
        count = 0
        for r in range(0, self.numStrings):
            count += len(self.tabs[r])
        self.numTabs = count
        print('removeLine(new) numTabsPerString:{} = numLines:{} * numTabsPerStringPerLine:{}, numTabs:{} = numStrings:{} * len(tabs[0]):{}'.format(self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.numTabs, self.numStrings, len(self.tabs[0])), file=self.dbgFile)
        self.printTabs()
    
    def quit(self, reason, code=0):
        '''Quit with reason and exit code.'''
        self.printLineInfo('quit(ExitCode={}, reason=\'{}\')'.format(code, reason))
        print(self.CSI + self.styles['CONS'] + self.CSI + '{};{}HExitCode={}, reason=\'{}\''.format(self.lastRow, 1, code, reason))
        self.dbgFile.close()
        exit(code)
     
    def printHelpInfo(self, ui=None):
        '''Print help info.  If ui: explicitly call printTabs(), else: assume printTabs() will be called by the invoker.  [cmd line opt -h]'''
        self.clearScreen()
        self.printHelpSummary()
        self.printHelpUiCmds()
        print('{}'.format('Press any key to continue... (Note some of the help text may have scrolled off the screen, you should be able to scroll back to view it.)'))
        b = ord(getwch())
        if ui:
            self.printTabs()

    def printHelpUiCmds(self):
        print('{:>20} : {}'.format('User Interactive Cmd', 'Description'))
        print('{:>20} : {}'.format('User Interactive Cmd', 'Description'), file=self.dbgFile)
        print('--------------------------------------------------------------------------------')
        print('--------------------------------------------------------------------------------', file=self.dbgFile)
        for k in self.uiKeys:
            print('{:>20} : {}'.format(k, self.uiCmds[k].__doc__))
            print('{:>20} : {}'.format(k, self.uiCmds[k].__doc__), file=self.dbgFile)
    
    def registerUiCmds(self):
        self.uiCmds = {}
        self.uiKeys = []
        self.registerUiCmd('Tablature',           self.setTab)
        self.registerUiCmd('Ctrl A',              self.toggleDisplayLabels)
        self.registerUiCmd('Ctrl B',              self.toggleDisplayChords)
        self.registerUiCmd('Ctrl C',              self.copySelectTabs)
        self.registerUiCmd('Shift C',             self.copySelectTabs)
        self.registerUiCmd('Ctrl D',              self.deleteSelectTabs)
        self.registerUiCmd('Ctrl E',              self.eraseTabs)
        self.registerUiCmd('Ctrl F',              self.toggleEnharmonic)
        self.registerUiCmd('Ctrl G',              self.goTo)
        self.registerUiCmd('Ctrl H or Backspace', self.deletePrevTab)
        self.registerUiCmd('Ctrl I or Tab',       self.toggleCursorDir)
        self.registerUiCmd('Ctrl J',              self.shiftSelectTabs)
        self.registerUiCmd('Ctrl K',              self.printChord)
        self.registerUiCmd('Ctrl L',              self.goToLastTab)
        self.registerUiCmd('Ctrl M or Enter',     self.toggleCursorMode)
        self.registerUiCmd('Ctrl N',              self.toggleDisplayNotes)
        self.registerUiCmd('Ctrl P',              self.printTabs)
        self.registerUiCmd('Ctrl Q',              self.quit)
        self.registerUiCmd('Ctrl R',              self.resetTabs)
        self.registerUiCmd('Ctrl S',              self.saveTabs)
        self.registerUiCmd('Ctrl T',              self.appendLine)
        self.registerUiCmd('Ctrl U',              self.unselectAll)
        self.registerUiCmd('Ctrl V',              self.pasteSelectTabs)
        self.registerUiCmd('Shift V',             self.pasteSelectTabs)
        self.registerUiCmd('Ctrl X',              self.cutSelectTabs)
        self.registerUiCmd('Ctrl Z',              self.goToLastTab)
        self.registerUiCmd('Shift Z',             self.goToLastTab)
        self.registerUiCmd('Shift T',             self.removeLine)
        self.registerUiCmd('Shift L',             self.goToLastTab)
        self.registerUiCmd('Shift K',             self.setCapo)
        self.registerUiCmd('Shift H',             self.printHelpInfo)
        self.registerUiCmd('Space',               self.moveCursor)
        self.registerUiCmd('Home',                self.moveHome)
        self.registerUiCmd('End',                 self.moveEnd)
        self.registerUiCmd('Page Up',             self.movePageUp)
        self.registerUiCmd('Page Down',           self.movePageDown)
        self.registerUiCmd('Insert',              self.toggleEditMode)
        self.registerUiCmd('Delete',              self.deleteTab)
        self.registerUiCmd('Arrow Up',            self.moveUp)
        self.registerUiCmd('Arrow Down',          self.moveDown)
        self.registerUiCmd('Arrow Left',          self.moveLeft)
        self.registerUiCmd('Arrow Right',         self.moveRight)
        self.registerUiCmd('Ctrl Arrow Left',     self.selectCol)
        self.registerUiCmd('Ctrl Arrow Right',    self.selectCol)
        self.registerUiCmd('Ctrl Arrow Up',       self.selectRow)
        self.registerUiCmd('Ctrl Arrow Down',     self.selectRow)
        self.registerUiCmd('Alt Arrow Left',      self.unselectCol)
        self.registerUiCmd('Alt Arrow Right',     self.unselectCol)
        self.registerUiCmd('Alt Arrow Up',        self.unselectRow)
        self.registerUiCmd('Alt Arrow Down',      self.unselectRow)
        self.registerUiCmd('ESC',                 self.toggleHarmonicNote)
        
    def registerUiCmd(self, key, method):
        if key not in self.uiKeys:
            self.uiCmds[key] = method
        self.uiKeys = sorted(self.uiCmds)
            
    def loop(self):
        '''Run the user interactive loop, executing user interactive commands as they are entered via the keyboard.'''
        while True:
            b = ord(getwch())
            if self.isTab(chr(b)): self.uiCmds['Tablature'](b)    # setTab()               # N/A
            elif b == 1:   self.uiCmds['Ctrl A']()                # toggleDisplayLabels()  # cmd line opt  -a
            elif b == 2:   self.uiCmds['Ctrl B']()                # toggleDisplayChords()  # cmd line opt  -b
            elif b == 3:   self.uiCmds['Ctrl C']()                # copySelectTabs()       # N/A
            elif b == 67:  self.uiCmds['Shift C'](arpg=1)         # copySelectTabs()       # N/A
            elif b == 4:   self.uiCmds['Ctrl D']()                # deleteSelectTabs()     # N/A
            elif b == 5:   self.uiCmds['Ctrl E']()                # eraseTabs()            #?cmd line opt?
            elif b == 6:   self.uiCmds['Ctrl F']()                # toggleEnharmonic()     # cmd line opt  -F?
            elif b == 7:   self.uiCmds['Ctrl G']()                # goTo()                 #?cmd line opt? -g
            elif b == 8:   self.uiCmds['Ctrl H or Backspace']()   # deletePrevTab()        # N/A
            elif b == 72:  self.uiCmds['Shift H'](ui=1)           # printHelpInfo()        # cmd line opt -h
            elif b == 9:   self.uiCmds['Ctrl I or Tab']()         # toggleCursorDir()      # cmd line opt  -i
            elif b == 10:  self.uiCmds['Ctrl J']()                # shiftSelectTabs()      # N/A
            elif b == 11:  self.uiCmds['Ctrl K'](dbg=1)           # printChord()           # N/A
            elif b == 75:  self.uiCmds['Shift K']()               # setCapo()              # cmd line opt -k?
            elif b == 12:  self.uiCmds['Ctrl L'](cs=1)            # goToLastTab()          # cmd line opt -l
            elif b == 76:  self.uiCmds['Shift L']()               # goToLastTab()          # cmd line opt -L
            elif b == 13:  self.uiCmds['Ctrl M or Enter']()       # toggleCursorMode()     # cmd line opt  -m
            elif b == 14:  self.uiCmds['Ctrl N']()                # toggleDisplayNotes()   # cmd line opt  -n
            elif b == 16:  self.uiCmds['Ctrl P']()                # printTabs()            # DBG?
            elif b == 17:  self.uiCmds['Ctrl Q'](self.QUIT_STR)   # quit()                 # DBG?
            elif b == 18:  self.uiCmds['Ctrl R']()                # resetTabs()            # DBG?
            elif b == 19:  self.uiCmds['Ctrl S']()                # saveTabs()             # DBG?
            elif b == 20:  self.uiCmds['Ctrl T']()                # appendLine()           # DBG?
            elif b == 84:  self.uiCmds['Shift T']()               # removeLine()           # DBG?
            elif b == 21:  self.uiCmds['Ctrl U']()                # unselectAll()          # N/A
            elif b == 22:  self.uiCmds['Ctrl V']()                # pasteSelectTabs()      # N/A
            elif b == 86:  self.uiCmds['Shift V']()               # pasteSelectTabs()      # N/A
            elif b == 24:  self.uiCmds['Ctrl X']()                # cutSelectTabs()        # N/A
            elif b == 26:  self.uiCmds['Ctrl Z'](ll=1, cs=1)      # goToLastTab()          # cmd line opt -z
            elif b == 90:  self.uiCmds['Shift Z'](ll=1)           # goToLastTab()          # cmd line opt -Z
            elif b == 27:  self.uiCmds['ESC']()                   # toggleHarmonicNote()   # N/A
            elif b == 32:  self.uiCmds['Space']()                 # moveCursor()           # N/A
            elif b == 155: self.uiCmds['Alt Arrow Left'](left=1)  # unselectCol()          # N/A
            elif b == 157: self.uiCmds['Alt Arrow Right']()       # unselectCol()          # N/A
            elif b == 152: self.uiCmds['Alt Arrow Up'](up=1)      # unselectRow()          # N/A
            elif b == 160: self.uiCmds['Alt Arrow Down']()        # unselectRow()          # N/A
            elif b == 224:                                        # Escape Sequence        # N/A
                b = ord(getwch())                                      # Read the escaped character
                if   b == 75:  self.uiCmds['Arrow Left']()             # moveLeft()             # N/A
                elif b == 77:  self.uiCmds['Arrow Right']()            # moveRight()            # N/A
                elif b == 72:  self.uiCmds['Arrow Up']()               # moveUp()               # N/A
                elif b == 80:  self.uiCmds['Arrow Down']()             # moveDown()             # N/A
                elif b == 71:  self.uiCmds['Home']()                   # moveHome()             #?cmd line opt?
                elif b == 79:  self.uiCmds['End']()                    # moveEnd()              #?cmd line opt?
                elif b == 73:  self.uiCmds['Page Up']()                # movePageUp()           #?cmd line opt?
                elif b == 81:  self.uiCmds['Page Down']()              # movePageDown()         #?cmd line opt?
                elif b == 82:  self.uiCmds['Insert']()                 # toggleEditMode()       # cmd line opt
                elif b == 83:  self.uiCmds['Delete']()                 # deleteTab()            # N/A
                elif b == 115: self.uiCmds['Ctrl Arrow Left'](left=1)  # selectCol()            # N/A
                elif b == 116: self.uiCmds['Ctrl Arrow Right']()       # selectCol()            # N/A
                elif b == 141: self.uiCmds['Ctrl Arrow Up'](up=1)      # selectRow()            # N/A
                elif b == 145: self.uiCmds['Ctrl Arrow Down']()        # selectRow()            # N/A
                else:          self.unknown(b, 'Unknown Escape')
            else:              self.unknown(b, 'Unknown Key')
        
    def unknown(self, b, reason):
        if b == 0:            return
        elif b < 128:         self.printe('{:<17}:{}:{}'.format(reason, chr(b), b))
        else:                 self.printe('{:<17}: :{}'.format(reason, b))

    def resetPos(self):
        print(self.CSI + '{};{}H'.format(self.row, self.col), end='')
    
    def moveTo(self, row=None, col=None, hi=0):
        '''Move to given row and col (optionally hilite row and col num).'''
        if row is not None: self.row = row
        if col is not None: self.col = col
        print('moveTo({}, {}, {}) row={}, col={}, line={}'.format(row, col, hi, self.row, self.col, self.row2Line(self.row)), file=self.dbgFile)
        print(self.CSI + '{};{}H'.format(self.row, self.col), end='')
        self.printStatus()
        if self.displayLabels == self.DISPLAY_LABELS['ENABLED'] and hi == 1:
            self.hiliteRowColNum()
   
    def moveLeft(self, dbg=None):
        '''Move cursor left one column on current line, wrapping to end of row on previous line or last line.'''
        if dbg or self.dbgMove: print('moveLeft({}, {})'.format(self.row, self.col), file=self.dbgFile)
        if self.col == self.bgnCol():
            line = self.row2Line(self.row)
            if line == 0: self.moveTo(row=self.row + self.lineDelta() * (self.numLines - 1), col=self.endCol(), hi=1)
            else:         self.moveTo(row=self.row - self.lineDelta(), col=self.endCol(), hi=1)
        else:             self.moveTo(col=self.col - 1, hi=1)

    def moveRight(self, dbg=None):
        '''Move cursor right one column on current line, wrapping to beginning of row on next line or first line.'''
        if dbg or self.dbgMove: print('moveRight({}, {})'.format(self.row, self.col), file=self.dbgFile)
        if self.col == self.endCol():
            line = self.row2Line(self.row)
            if line == self.numLines - 1: self.moveTo(row=self.row - self.lineDelta() * (self.numLines - 1), col=self.bgnCol(), hi=1)
            else:                         self.moveTo(row=self.row + self.lineDelta(), col=self.bgnCol(), hi=1)
        else:                             self.moveTo(col=self.col + 1, hi=1)
        
    def moveUp(self, dbg=None):
        '''Move cursor up one row on current line, wrapping to last row on previous line or last line.'''
        if dbg or self.dbgMove: print('moveUp({}, {})'.format(self.row, self.col), file=self.dbgFile)
        line = self.row2Line(self.row)
        if self.row == self.bgnRow(line):
            if line == 0: self.moveTo(row=self.endRow(self.numLines - 1), hi=1)
            else:         self.moveTo(row=self.endRow(line - 1), hi=1)
        else:             self.moveTo(row=self.row - 1, hi=1)
    
    def moveDown(self, dbg=None):
        '''Move cursor down one row on current line, wrapping to first row on next line or first line.'''
        if dbg or self.dbgMove: print('moveDown({}, {})'.format(self.row, self.col), file=self.dbgFile)
        line = self.row2Line(self.row)
        if self.row == self.endRow(line):
            if line == self.numLines - 1: self.moveTo(row=self.bgnRow(0), hi=1)
            else:                         self.moveTo(row=self.bgnRow(line + 1), hi=1)
        else:                             self.moveTo(row=self.row + 1, hi=1)
    
    def moveHome(self, dbg=None):
        '''Move cursor to beginning of row on current line, wrapping to end of row on previous line or last line.'''
        if dbg or self.dbgMove: print('moveHome({}, {})'.format(self.row, self.col), file=self.dbgFile)
        if self.col == self.bgnCol():
            line = self.row2Line(self.row)
            if line == 0: self.moveTo(row=self.row + self.lineDelta() * (self.numLines - 1), col=self.endCol(), hi=1)
            else:         self.moveTo(row=self.row - self.lineDelta(), col=self.endCol(), hi=1)
        else:             self.moveTo(col=self.bgnCol(), hi=1)
            
    def moveEnd(self, dbg=None):
        '''Move cursor to end of row on current line, wrapping to beginning of row on next line or first line.'''
        if dbg or self.dbgMove: print('moveEnd({}, {})'.format(self.row, self.col), file=self.dbgFile)
        if self.col == self.endCol():
            line = self.row2Line(self.row)
            if line == self.numLines - 1: self.moveTo(row=self.row - self.lineDelta() * (self.numLines - 1), col=self.bgnCol(), hi=1)
            else:                         self.moveTo(row=self.row + self.lineDelta(), col=self.bgnCol(), hi=1)
        else:                             self.moveTo(col=self.endCol(), hi=1)

    def movePageUp(self, dbg=None):
        '''Move cursor to first row on current line, wrapping to last row on previous line or last line.'''
        if dbg or self.dbgMove: self.printLineInfo('movePageUp({}, {})'.format(self.row, self.col))
        line = self.row2Line(self.row)
        if self.row == self.bgnRow(line):
            if line == 0: self.moveTo(row=self.endRow(self.numLines - 1), hi=1)
            else:         self.moveTo(row=self.endRow(line - 1), hi=1)
        else:             self.moveTo(row=self.bgnRow(line), hi=1)

    def movePageDown(self, dbg=None):
        '''Move cursor to last row on current line, wrapping to first row on next line or first line.'''
        if dbg or self.dbgMove: self.printLineInfo('movePageDown({}, {})'.format(self.row, self.col))
        line = self.row2Line(self.row)
        if self.row == self.endRow(line):
            if line == self.numLines - 1: self.moveTo(row=self.bgnRow(0), hi=1)
            else:                         self.moveTo(row=self.bgnRow(line + 1), hi=1)
        else:                             self.moveTo(row=self.endRow(line), hi=1)

    def row2Line(self, row):
        for line in range(0, self.numLines):
            if self.bgnRow(line) <= row <= self.endRow(line):
                return line
        return -1

    def colIndex2Line(self, c):
        return int(c / self.numTabsPerStringPerLine)
        
    def rowCol2Indices(self, row, col):
        r = self.row2Index(row)
        c = self.col2Index(col)
        return r, c
    
    def row2Index(self, row):
        r = row - self.ROW_OFF
        r -= self.row2Line(row) * self.lineDelta()
        return r
    
    def col2Index(self, col):
        c = col - self.COL_OFF
        c += self.row2Line(self.row) * self.numTabsPerStringPerLine
        return c
    
    def indices2Row(self, r, c):
        return r + self.ROW_OFF + self.colIndex2Line(c) * self.lineDelta()
    
    def index2Col(self, c):
        return c + self.COL_OFF - self.colIndex2Line(c) * self.numTabsPerStringPerLine
    
    def indices2RowCol(self, r, c):
        return self.indices2Row(r, c), self.index2Col(c)
    
    def bgnCol(self):
        return self.COL_OFF
        
    def endCol(self):
        return self.COL_OFF + self.numTabsPerStringPerLine - 1
        
    def lineDelta(self):
        return self.numStrings + self.NOTES_LEN + self.CHORDS_LEN + 1
        
    def bgnRow(self, line):
        return self.ROW_OFF + line * self.lineDelta()
            
    def endRow(self, line):
        return self.ROW_OFF + line * self.lineDelta() + self.numStrings - 1
        
    def setLastRow(self):
        self.lastRow = self.ROW_OFF + self.numLines * self.lineDelta() - 1
    
    def toggleEditMode(self, dbg=None):
        '''Toggle cursor movement modes (insert or replace).'''
        self.editMode = (self.editMode + 1) % len(self.EDIT_MODES)
        if self.displayLabels == self.DISPLAY_LABELS['ENABLED']:
            for line in range(0, self.numLines):
                r = line * self.lineDelta() + 1
                if self.editMode == self.EDIT_MODES['INSERT']:
                    self.prints('I', r, self.editModeCol, self.styles['MODES'])
                elif self.editMode == self.EDIT_MODES['REPLACE']:
                    self.prints('R', r, self.editModeCol, self.styles['MODES'])
            if dbg: self.printLineInfo('toggleEditMode({}, {})'.format(self.row, self.col))
            self.resetPos()
    
    def toggleCursorMode(self, dbg=None):
        '''Toggle cursor movement modes (melody, chord, or arpeggio).'''
        self.cursorMode = (self.cursorMode + 1) % len(self.CURSOR_MODES)
        if self.displayLabels == self.DISPLAY_LABELS['ENABLED']:
            for line in range(0, self.numLines):
                r = line * self.lineDelta() + 1
                if self.cursorMode == self.CURSOR_MODES['MELODY']:
                    self.prints('M', r, self.cursorModeCol, self.styles['MODES'])
                elif self.cursorMode == self.CURSOR_MODES['CHORD']:
                    self.prints('C', r, self.cursorModeCol, self.styles['MODES'])
                elif self.cursorMode == self.CURSOR_MODES['ARPEGGIO']:
                    self.prints('A', r, self.cursorModeCol, self.styles['MODES'])
            if dbg: self.printLineInfo('toggleCursorMode({}, {})'.format(self.row, self.col))
            self.resetPos()

    def toggleCursorDir(self, dbg=None):
        '''Toggle direction (up or down) of cursor vertical movement.  [cmd line opt -i]'''
        self.cursorDir = (self.cursorDir + 1) % len(self.CURSOR_DIRS)
        for line in range(0, self.numLines):
            for r in range(0, self.numStrings):
                if self.cursorDir == self.CURSOR_DIRS['DOWN']:
                    self.prints(chr(self.capo), r + self.bgnRow(line), self.cursorModeCol, self.styles['NUT_DN'])
                    self.prints(chr(self.capo), r + self.endRow(line), self.cursorModeCol, self.styles['NUT_DN'])
                elif self.cursorDir == self.CURSOR_DIRS['UP']:
                    self.prints(chr(self.capo), r + self.bgnRow(line), self.cursorModeCol, self.styles['NUT_UP'])
                    self.prints(chr(self.capo), r + self.endRow(line), self.cursorModeCol, self.styles['NUT_UP'])
        if dbg: self.printLineInfo('toggleCursorDir({}, {}, {}, {})'.format(self.row, self.col, self.cursorDir, self.CURSOR_DIRS[self.cursorDir]))
        self.resetPos()

    def toggleEnharmonic(self):
        '''Toggle display of enharmonic (sharp or flat) notes.  [cmd line opt -F]'''
        self.enharmonic = (self.enharmonic + 1) % len(self.ENHARMONIC)
        self.printTabs()

    def toggleDisplayLabels(self, printTabs=True):
        '''Toggle (enable or disable) display of modes and labels row.  [cmd line opt -a]'''
        self.displayLabels = (self.displayLabels + 1) % len(self.DISPLAY_LABELS)
        line = self.row2Line(self.row)
        if self.displayLabels == self.DISPLAY_LABELS['ENABLED']:
            self.ROW_OFF = 2
            self.row += 1
        elif self.displayLabels == self.DISPLAY_LABELS['DISABLED']:
            self.ROW_OFF = 1
            self.row -= 1
        self.setLastRow()
        self.printLineInfo('toggleDisplayLabels({}) row,col=({}, {}), line={},'.format(self.displayLabels, self.row, self.col, line))
        if printTabs: self.printTabs()
        
    def toggleDisplayNotes(self, printTabs=True):
        '''Toggle (enable or disable) display of notes section.  [cmd line opt -n]'''
        self.displayNotes = (self.displayNotes + 1) % len(self.DISPLAY_NOTES)
        line = self.row2Line(self.row)
        if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
            self.NOTES_LEN = self.numStrings
            self.row += line * self.NOTES_LEN
        elif self.displayNotes == self.DISPLAY_NOTES['DISABLED']:
            self.row -= line * self.NOTES_LEN
            self.NOTES_LEN = 0
        self.setLastRow()
        self.printLineInfo('toggleDisplayNotes({}) row,col=({}, {}), line={}'.format(self.displayNotes, self.row, self.col, line))
        if printTabs: self.printTabs()
    
    def toggleDisplayChords(self, printTabs=True):
        '''Toggle (enable or disable) display of chords section.  [cmd line opt -b]'''
        self.displayChords = (self.displayChords + 1) % len(self.DISPLAY_CHORDS)
        line = self.row2Line(self.row)
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            if self.chordsObj is None:
                self.chordsObj = chords.Chords(self)
                print('toggleDisplayChords() loaded chords module and Chords class, chordsObj={}, getChordName={}'.format(self.chordsObj, self.chordsObj.getChordName), file=self.dbgFile)
            self.CHORDS_LEN = 5
            self.row += line * self.CHORDS_LEN
        elif self.displayChords == self.DISPLAY_CHORDS['DISABLED']:
            self.row -= line * self.CHORDS_LEN
            self.CHORDS_LEN = 0
        self.setLastRow()
        self.printLineInfo('toggleDisplayChords({}) row,col=({}, {}), line={}'.format(self.displayChords, self.row, self.col, line))
        if printTabs: self.printTabs()

    def printCursorAndEditModes(self, r):
        print('printCursorAndEditModes()'.format(), file=self.dbgFile)
        if self.editMode == self.EDIT_MODES['INSERT']:
            self.prints('I', r, self.editModeCol, self.styles['MODES'])
        elif self.editMode == self.EDIT_MODES['REPLACE']:
            self.prints('R', r, self.editModeCol, self.styles['MODES'])
        if self.cursorMode == self.CURSOR_MODES['MELODY']:
            self.prints('M', r, self.cursorModeCol, self.styles['MODES'])
        elif self.cursorMode == self.CURSOR_MODES['CHORD']:
            self.prints('C', r, self.cursorModeCol, self.styles['MODES'])
        elif self.cursorMode == self.CURSOR_MODES['ARPEGGIO']:
            self.prints('A', r, self.cursorModeCol, self.styles['MODES'])

    def printPageAndLine(self, r, line):
        self.prints('1', r, self.editModeCol, self.styles['MODES'])
        self.prints('{}'.format(line + 1), r, self.cursorModeCol, self.styles['MODES'])
    
    def printColNums(self, row):
        print('printColNums({})'.format(row), file=self.dbgFile)
        for c in range(0, self.numTabsPerStringPerLine):
            self.printColNum(row, c + 1, self.styles['NORMAL'])

    def printColNum(self, row, c, style):
        '''Print 1 based tab col index, c, as a single decimal digit.'''
        '''123456789112345678921234567893123456789412345678951234567896123456789712345678981234567899123456789012345678911234567892123456789312345678941234567895'''
        if c % 10: style += self.styles['MIN_COL_NUM']
        else:      style += self.styles['MAJ_COL_NUM']
        self.prints('{}'.format(self.getColMod(c)), row, c + self.COL_OFF - 1, style)

    def getColMod(self, c):
        if c % 10:    return c % 10
        elif c < 100: return c // 10
        else:         return ((c - 100) // 10)
    
    def selectRow(self, up=0):
        '''Select row, append to selected rows list, hilite current tab, and advance (up or down) to next tab.'''
        r = self.row2Index(self.row)
        c = self.col2Index(self.col)
        print('selectRow({},{}) befor appending r={}, c={}, selectRows={}, selectCols={}'.format(self.row, self.col, r, c, self.selectRows, self.selectCols), file=self.dbgFile)
        self.selectRows.append(r)
        self.selectCols.append(c)
        print('selectRow({},{}) after appending r={}, c={}, selectRows={}, selectCols={}'.format(self.row, self.col, r, c, self.selectRows, self.selectCols), file=self.dbgFile)
        self.selectStyle(c, self.styles['BRIGHT'], rList=self.selectRows)
        if up: self.moveUp()
        else:  self.moveDown()

    def unselectRow(self, up=0):
        '''Unselect row, remove it from selected rows list, un-hilite the current tab, and advance (up or down) to the next tab.'''
        if len(self.selectRows):
            r = self.row2Index(self.row)
            print('unselectRow({},{}) checking if r={} in selectRows={}'.format(self.row, self.col, r, self.selectRows), file=self.dbgFile)
            if r in self.selectRows:
                print('unselectRow({},{}) before removing r={} from selectRows={}'.format(self.row, self.col, r, self.selectRows), file=self.dbgFile)
                self.selectRows.remove(r)
                print('unselectRow({},{}) after removing r={} from selectRows={}'.format(self.row, self.col, r, self.selectRows), file=self.dbgFile)
                c = self.col2Index(self.col)
                self.selectStyle(c, self.styles['NORMAL'], r=r)
                if up: self.moveUp()
                else:  self.moveDown()
            else: print('unselectRow({},{}) r={} not in selectRows={}, nothing to unselect'.format(self.row, self.col, r, self.selectRows), file=self.dbgFile)
        else: print('unselectRow({},{}) selectRows={}, empty list, nothing to unselect'.format(self.row, self.col, self.selectRows), file=self.dbgFile)
        
    def selectCol(self, left=0):
        '''Select column, append to selected columns list, hilite current tab, and advance (left or right) to next tab.'''
        if len(self.selectRows) == 0:
            self.selectFlag = 1
            print('selectCol({},{}) before appending all rows, selectCols={}, selectRows={}'.format(self.row, self.col, self.selectCols, self.selectRows), file=self.dbgFile)
            for r in range(0, self.numStrings):
                self.selectRows.append(r)
            print('selectCol({},{}) after appending all rows, selectCols={}, selectRows={}'.format(self.row, self.col, self.selectCols, self.selectRows), file=self.dbgFile)
        elif self.selectFlag == 0:
            self.selectFlag = 1
            print('selectCol({},{}) before removing all cols, selectCols={}, selectRows={}'.format(self.row, self.col, self.selectCols, self.selectRows), file=self.dbgFile)
            for c in range(0, len(self.selectCols)):
                self.selectStyle(c, self.styles['NORMAL'], rList=self.selectRows)
            self.selectCols = []
            print('selectCol({},{}) after removing all cols, selectCols={}, selectRows={}'.format(self.row, self.col, self.selectCols, self.selectRows), file=self.dbgFile)
        c = self.col2Index(self.col)
        print('selectCol({},{}) before appending c={}, selectCols={}, selectRows={}'.format(self.row, self.col, c, self.selectCols, self.selectRows), file=self.dbgFile)
        self.selectCols.append(c)
        print('selectCol({},{}) after appending c={}, selectCols={}, selectRows={}'.format(self.row, self.col, c, self.selectCols, self.selectRows), file=self.dbgFile)
        self.selectStyle(c, self.styles['BRIGHT'], rList=self.selectRows)
        if left: self.moveLeft()
        else:    self.moveRight()

    def unselectCol(self, left=0):
        '''Unselect column, remove it from selected columns list, un-hilite the current tab, and advance (left or right) to the next tab.'''
        if len(self.selectCols):
            c = self.col2Index(self.col)
            print('unselectCol({},{}) checking if c={} in selectCols={}'.format(self.row, self.col, c, self.selectCols), file=self.dbgFile)
            if c in self.selectCols:
                print('unselectCol({},{}) before removing c={} from selectCols={}'.format(self.row, self.col, c, self.selectCols), file=self.dbgFile)
                self.selectCols.remove(c)
                print('unselectCol({},{}) after removing c={} from selectCols={}'.format(self.row, self.col, c, self.selectCols), file=self.dbgFile)
                self.selectStyle(c, self.styles['NORMAL'], rList=self.selectRows)
                if left: self.moveLeft()
                else:    self.moveRight()
            else: print('unselectCol({},{}) c={} not in selectCols={}, nothing to unselect'.format(self.row, self.col, c, self.selectCols), file=self.dbgFile)
        else: print('unselectCol({},{}) selectCols={}, empty list, nothing to unselect'.format(self.row, self.col, self.selectCols), file=self.dbgFile)

    def unselectAll(self):
        '''Unselect all rows and columns.'''
        self.printLineInfo('unselectAll({}, {})'.format(self.row, self.col))
        for c in range(0, len(self.selectCols)):
            self.selectStyle(self.selectCols[c], self.styles['NORMAL'], rList=self.selectRows)
        self.selectRows, self.selectCols, self.selectTabs, self.selectHTabs = [], [], [], []
        self.resetPos()
            
    def selectStyle(self, c, style, rList=None, r=None):
        print('selectStyle({}) c={}, rList={}, r={}'.format(style, c, rList, r), file=self.dbgFile)
        if rList is not None and r is None:
            for rr in range(0, len(rList)):
                r = rList[rr]
                self.selectRowStyle(r, c, style)
        elif rList is None and r is not None:
            self.selectRowStyle(r, c, style)
            
    def selectRowStyle(self, r, c, style):
        tab = self.tabs[r][c]
        row, col = self.indices2RowCol(r, c)
        print('selectRowStyle({}) r={}, c={}, row={}, col={}, tab={}'.format(style, r, c, row, col, chr(tab)), file=self.dbgFile)
        if self.htabs[r][c] == ord('1'):
            self.prints(chr(tab), row, col, style + self.styles['H_TABS'])
        else:
            self.prints(chr(tab), row, col, style + self.styles['TABS'])
        if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
            if self.isFret(chr(tab)):
                if self.htabs[r][c] == ord('1'):
                    n = self.getHarmonicNote(r + 1, tab)
                    self.printNote(row + self.numStrings, col, n, style, hn=1)
                else:
                    n = self.getNote(r + 1, tab)
                    self.printNote(row + self.numStrings, col, n, style)
            else:
                self.prints(chr(tab), row + self.numStrings, col, style + self.styles['NAT_NOTE'])
    
    def toggleHarmonicNote(self):
        '''Toggle between normal and harmonic note.  Modify note modelling the closest natural harmonic note in the tab fret number.'''
        line = self.row2Line(self.row)
        r, c = self.rowCol2Indices(self.row, self.col)
        tab = self.tabs[r][c]
        if self.htabs[r][c] == ord('0'):
            if self.isFret(chr(tab)) and self.getFretNum(tab) in self.HARMONIC_FRETS:
                self.htabs[r][c] = ord('1')
                n = self.getHarmonicNote(r + 1, tab)
                self.prints(chr(tab), self.row, self.col, self.styles['H_TABS'])
                if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                    self.printNote(r + line * self.lineDelta() + self.endRow(0) + 1 , self.col, n, hn=1)
                    self.resetPos()
                pn = self.getNote(r + 1, tab)
                print('toggleHarmonicNote({},{}) r,c={},{}, tab={}, pn.n={}, pn.i={} norm->harm n.n={}, n.i={}'.format(self.row, self.col, r, c, chr(tab), pn.name, pn.index, n.name, n.index), file=self.dbgFile)
        else:
            self.htabs[r][c] = ord('0')
            n = self.getNote(r + 1, tab)
            self.prints(chr(tab), self.row, self.col, self.styles['TABS'])
            if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                self.printNote(r + line * self.lineDelta() + self.endRow(0) + 1 , self.col, n)
                self.resetPos()
            pn = self.getHarmonicNote(r + 1, tab)
            print('toggleHarmonicNote({},{}) r,c={},{}, tab={}, pn.n={}, pn.i={} harm->norm n.n={}, n.i={}'.format(self.row, self.col, r, c, chr(tab), pn.name, pn.index, n.name, n.index), file=self.dbgFile)
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.chordsObj.eraseChord(c)
            self.chordsObj.printChord(c=c)
        self.printStatus()

    def setCapo(self, c=None):
        '''Model a capo placed at fret position specified by user input of a single character, [0-9] [a-o].  [cmd line opt -k]'''
        if c is None: c = getwch()
        print('setCapo({}, {}) c={}, ord(c)={}, prevCapo={} bgn: check isFret(c)'.format(self.row, self.col, c, ord(c), self.capo), file=self.dbgFile)
        if self.isFret(c):
            capFN = self.getFretNum(ord(c))
            maxFN = self.getFretNum(self.maxFret)
            print('setCapo() c={}, ord(c)={}, chr(mf)={}, maxFret={}, check capFN:{} + maxFN:{} <= {}?'.format(c, ord(c), chr(self.maxFret), self.maxFret, capFN, maxFN, self.NUM_FRETS), file=self.dbgFile)
            if capFN + maxFN > self.NUM_FRETS:
                info = 'setCapo() ERROR! capFN:{} + maxFN:{} > {}!  c={}, ord(c)={}, capo={}, chr(mf)={}, maxFret={}'.format(capFN, maxFN, self.NUM_FRETS, c, ord(c), self.capo, chr(self.maxFret), self.maxFret)
                self.printe(info)
            else:
                self.capo = ord(c)            
                print('setCapo() c={}, ord(c)={}, capo={}, capFN={}, chr(mf)={}, maxFret={}, maxFN={} setting capo'.format(c, ord(c), self.capo, capFN, chr(self.maxFret), self.maxFret, maxFN), file=self.dbgFile)
                self.printTabs()

    def findMaxFret(self):
        maxFN = 0
        for r in range(0, len(self.tabs)):
            for c in range(0, len(self.tabs[r])):
                tab = self.tabs[r][c]
                if self.isFret(chr(tab)):
                    currFN = self.getFretNum(tab)
                    if currFN > maxFN:
                        maxFN = currFN
        return self.getFretByte(maxFN)
        
    def setTab(self, tab):
        '''Set given tab byte at the current row and col, print the corresponding tab character and then move cursor according to the cursor mode.'''
        print('setTab({}, {}) chr(tab)={}, tab, bgn: check row/col'.format(self.row, self.col, chr(tab), tab), file=self.dbgFile)
        if self.bgnCol() <= self.col <= self.endCol() and self.ROW_OFF <= self.row < self.ROW_OFF + self.numLines * self.lineDelta():
            row, col = self.row, self.col
            rr, cc = self.rowCol2Indices(row, col)
            if self.editMode == self.EDIT_MODES['INSERT']:
                for c in range(len(self.tabs[rr]) - 1, cc, - 1):
                    self.tabs[rr][c] = self.tabs[rr][c - 1]
            if self.htabs[rr][cc] == ord('1'):
                self.htabs[rr][cc] = ord('0')
                print('setTab() cleared htab={}, rr={}, cc={}'.format(chr(self.htabs[rr][cc]), rr, cc), file=self.dbgFile)
            prevTab = self.tabs[rr][cc]
            capTab = self.tabs[rr][cc] = tab
            if self.isFret(chr(prevTab)) and self.getFretNum(prevTab) == self.getFretNum(self.maxFret):
                self.maxFret = self.findMaxFret()
                print('setTab() setting maxFret=({},{},{}) prevMF=({},{},{})'.format(self.maxFret, chr(self.maxFret), self.getFretNum(self.maxFret), prevTab, chr(prevTab), self.getFretNum(prevTab)), file=self.dbgFile)
            print('setTab({}, {}) chr(tab)={}, tab={}, check isFret(chr(tab)), htab={}'.format(rr, cc, chr(tab), tab, self.htabs[rr][cc]), file=self.dbgFile)
            if self.isFret(chr(tab)):
                tabFN = self.getFretNum(tab)
                maxFN = self.getFretNum(self.maxFret)
                capFN = self.getFretNum(self.capo)
                print('setTab() chr(tab)={}, tab={}, chr(capo)={}, capo={}, check tabFN:{} + capFN:{} > {}?'.format(chr(tab), tab, chr(self.capo), self.capo, tabFN, capFN, self.NUM_FRETS), file=self.dbgFile)
                if tabFN + capFN > self.NUM_FRETS:
                    info = 'setTab() ERROR! capFN:{} + tabFN:{} > {}! chr(tab)={}, tab={}, chr(capo)={}, capo={}'.format(capFN, tabFN, self.NUM_FRETS, chr(tab), tab, chr(self.capo), self.capo)
                    self.printe(info)
                    return
                print('setTab() check tabFn:{} > maxFn:{}? chr(tab)={}, tab={}, chr(mf)={}, maxFret={}'.format(tabFN, maxFN, chr(tab), tab, chr(self.maxFret), self.maxFret), file=self.dbgFile)
                if tabFN > maxFN: 
                    self.maxFret = tab
                    print('setTab() updating maxFret: chr(mf)={}, maxFret={}, maxFN={}'.format(chr(self.maxFret), self.maxFret, self.getFretNum(self.maxFret)), file=self.dbgFile)
                capTab = self.getFretByte(tabFN + capFN)
                print('setTab() setting capTab:{} = self.getFretByte(tabFN:{} + capFN:{})'.format(capTab, tabFN, capFN), file=self.dbgFile)
            if self.editMode == self.EDIT_MODES['INSERT']:
                self.printTabs()
            elif self.editMode == self.EDIT_MODES['REPLACE']:
                if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                    if self.isFret(chr(capTab)):
                        note = self.getNote(rr + 1, tab)
                        self.printNote(row + self.numStrings, col, note)
                        print('setTab() chr(capTab)={} note={}'.format(chr(capTab), note.name), file=self.dbgFile)
                    else:
                        self.prints(chr(capTab), row + self.numStrings, col, self.styles['NAT_NOTE'])
                self.prints(chr(tab), row, col, self.styles['TABS'])
                if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
                    noteCount = 0
                    for r in range(0, self.numStrings):
                        if self.isTab(chr(self.tabs[r][cc])):
                            noteCount += 1
                            if noteCount > 1:
                                print('setTab() noteCount={}'.format(noteCount), file=self.dbgFile)
                                self.chordsObj.printChord(c=cc)
                                break
            self.moveCursor()
        else:
            info = 'row/col ERROR in setTab({},{},{})'.format(self.row, self.col, tab)
            self.printe(info)

    def goTo(self):
        '''Go to tab location specified by user numeric input of up to 3 characters terminated by space char.'''
        cc, tmp = '', []
        while len(tmp) < 3:
            cc = getwch()
            if cc != ' ' and '0' <= cc <= '9' : tmp.append(cc)
            else: break
        if len(tmp):
            c = int(''.join(tmp))
            self.moveTo(col=c + self.COL_OFF - 1, hi=1)
        
    def goToLastTab(self, cs=0, ll=0):
        '''Go to last tab position on the current line, ll=0, or the last line, ll=1, of all strings, cs=0, or the current string, cs=1.'''
        rr, cc = 0, 0
        if ll: lineBgn, lineEnd = self.numLines,               0
        else:  lineBgn, lineEnd = self.row2Line(self.row) + 1, self.row2Line(self.row)      # lineBgn - 1
        if cs: rowBgn,  rowEnd = self.row2Index(self.row),     self.row2Index(self.row) + 1 # rowBgn + 1
        else:  rowBgn,  rowEnd = 0,                            self.numStrings
        print('goToLastTab({}, {}) cs={}, ll={}, rowBng={}, rowEnd={}, lineBgn={}, lineEnd={}'.format(self.row, self.col, cs, ll, rowBgn, rowEnd, lineBgn, lineEnd), file=self.dbgFile)
        for line in range(lineBgn, lineEnd, -1):
            for r in range(rowBgn, rowEnd):
                for c in range(line * self.numTabsPerStringPerLine - 1, (line - 1) * self.numTabsPerStringPerLine - 1, -1):
                    t = chr(self.tabs[r][c])
                    if t != '-' and self.isTab(t):
                        if c > cc:
                            rr, cc, ll = r, c, line
                            print('goToLastTab(updating col) t={}, line={}, r={}, c={}'.format(t, line, r, c), file=self.dbgFile)
                        break
        if cc > 0:
            row, col = self.indices2RowCol(rr, cc)
            print('goToLastTab() row,col=({},{})'.format(row, col), file=self.dbgFile)
            self.moveTo(row=row, col=col, hi=1)

    def moveCursor(self, row=None, col=None):
        '''Move cursor to the next row and or col using cursor mode (optionally hilite new row and col nums).'''
        print('moveCursor({}, {}) old: row={}, col={}'.format(row, col, self.row, self.col), file=self.dbgFile)
        if row != None: self.row = row
        if col != None: self.col = col
        elif self.cursorMode == self.CURSOR_MODES['MELODY']:
            self.moveRight()
        elif self.cursorMode == self.CURSOR_MODES['CHORD'] or self.cursorMode == self.CURSOR_MODES['ARPEGGIO']:
            if self.cursorMode == self.CURSOR_MODES['ARPEGGIO']:
                self.moveRight()
            line = self.row2Line(self.row)
            if self.cursorDir == self.CURSOR_DIRS['DOWN']:
                if self.row < self.endRow(line):
                    self.moveDown()
                else:
                    self.row = self.bgnRow(line)
                    self.moveRight()
            elif self.cursorDir == self.CURSOR_DIRS['UP']:
                if self.row > self.bgnRow(line):
                    self.moveUp()
                else:
                    self.row = self.endRow(line)
                    self.moveRight()
        print('moveCursor({}, {}) new: row={}, col={}'.format(row, col, self.row, self.col), file=self.dbgFile)

    def hiliteRowColNum(self):
        self.hiliteCount += 1
        print('hiliteRowColNum({}, {}) hilitePrevRowPos={}, hiliteRowNum={}, hiliteColNum={}, hiliteCount={}'.format(self.row, self.col, self.hilitePrevRowPos, self.hiliteRowNum, self.hiliteColNum, self.hiliteCount), file=self.dbgFile)
        for line in range(0, self.numLines):
            row = line * self.lineDelta() + 1
            if self.hiliteColNum != 0:
                self.printColNum(row, self.hiliteColNum, self.styles['NORMAL'])
        self.hiliteColNum = self.col - self.COL_OFF + 1
        for line in range(0, self.numLines):
            row = line * self.lineDelta() + 1
            if self.hiliteColNum != 0:
                self.printColNum(row, self.hiliteColNum, self.styles['BRIGHT'])
                
        if self.hiliteRowNum != 0:
            self.prints(self.hiliteRowNum, self.hilitePrevRowPos, self.editModeCol, self.styles['NORMAL'] + self.styles['TABS'])
        self.hiliteRowNum = self.row - self.row2Line(self.row) *  self.lineDelta() - 1
        self.hilitePrevRowPos = self.row
        print('hiliteRowColNum({}, {}) hilitePrevRowPos={}, hiliteRowNum={}, hiliteColNum={}, hiliteCount={}'.format(self.row, self.col, self.hilitePrevRowPos, self.hiliteRowNum, self.hiliteColNum, self.hiliteCount), file=self.dbgFile)
        self.prints(self.hiliteRowNum, self.row, self.editModeCol, self.styles['BRIGHT'] + self.styles['TABS'])
        self.resetPos()

    def deleteTab(self, row=None, col=None):
        '''Delete current tab.'''
        if row is None: row = self.row
        if col is None: col = self.col
        r, c = self.rowCol2Indices(row, col)
        tab = self.tabs[r][c]
        tabFN = self.getFretNum(tab)
        maxFN = self.getFretNum(self.maxFret)
        print('deleteTab({},{},{},{}) tab={}, chr(tab)={}, tabFN={}'.format(row, col, r, c, tab, chr(tab), tabFN, maxFN), file=self.dbgFile)
        if self.editMode == self.EDIT_MODES['INSERT']:
            for cc in range(c, len(self.tabs[r])):
                if len(self.tabs[r]) > cc + 1:
                    self.tabs[r][cc]  = self.tabs[r][cc + 1]
                    self.htabs[r][cc] = self.htabs[r][cc + 1]
            self.printTabs()
        elif self.editMode == self.EDIT_MODES['REPLACE']:
            self.tabs[r][c] = ord('-')
            self.htabs[r][c] = ord('0')
            self.prints(chr(self.tabs[r][c]), row, col, self.styles['TABS'])
            if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                self.prints(chr(self.tabs[r][c]), row + self.numStrings, col, self.styles['NAT_NOTE'])
            if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
                self.chordsObj.eraseChord(c)
                self.chordsObj.printChord(c=c)
            self.moveTo(row=row, col=col)
        if self.isFret(chr(tab)) and tabFN == maxFN:
            self.maxFret = self.findMaxFret()
            print('deleteTab() reset maxFret={}, chr(maxFret)={}, maxFN={}, tab={}, chr(tab)={}, tabFN={}'.format(self.maxFret, chr(self.maxFret), self.getFretNum(self.maxFret), tab, chr(tab), tabFN), file=self.dbgFile)

    def deletePrevTab(self):
        '''Delete previous tab (backspace).'''
        self.moveTo(col=self.col - 1)
        self.deleteTab()
    
    def eraseTabs(self):
        '''Erase all tabs (resets all tabs to '-').'''
        for r in range(0, len(self.tabs)):
            for c in range(0, len(self.tabs[r])):
                self.tabs[r][c] = ord('-')
                self.htabs[r][c] = ord('0')
        self.maxFret = ord('0')
        self.printTabs()

    def resetTabs(self):
        '''Reset all tabs to their initial state at start up.'''
        self.init()

    def saveTabs(self):
        '''Save all tabs (with ANSI codes) to the configured output file.  Use cat to display the file'''
        with open(self.outName, 'w') as self.outFile:
            self.printLineInfo('saveTabs({}, {}) bgn writing tabs to file'.format(self.row, self.col))
            self.clearScreen(2, file=self.outFile)
            print('capo={}'.format(chr(self.capo)), file=self.outFile)
            self.printTabs()
            self.moveTo(hi=1)
            print(self.CSI + self.styles['NORMAL'] + self.styles['CONS'] + self.CSI + '{};{}H'.format(self.lastRow, 1), end='', file=self.outFile) # set the file cursor to the front of the next row (NUM_STR+r+1, 0) and set the foreground and background color
            self.dumpTabs('saveTabs(h)', h=1)
            self.printLineInfo('saveTabs({}, {}) end writing tabs to file'.format(self.row, self.col))
        self.outFile = None

    def shiftSelectTabs(self):
        '''Shift selected tabs (left or right) specified by user numeric input of up to 3 characters terminated by space char.'''
        c, tmp = '', []
        while len(tmp) <= 3:
            c = getwch()
            if c != ' ': tmp.append(c)
            else: break
        shift = int(''.join(tmp))
        shifted = False
        print('shiftSelectTabs({}, {})'.format(shift, len(self.selectCols)), file=self.dbgFile)
        for cc in range(0, len(self.selectCols)):
            for r in range(0, self.numStrings):
                c = self.selectCols[cc]
                if self.isFret(chr(self.tabs[r][c])):
                    if self.tabs[r][c] + shift >= ord('0') - 1:
                        self.tabs[r][c] = self.tabs[r][c] + shift
                        shifted = True
                        print('shiftSelectTabs() r,c,tab=({},{},{})'.format(r, c, chr(self.tabs[r][c])), file=self.dbgFile)
                    else: self.printe('Error! shiftSelectTabs() Lower than open string! r,c,tab=({},{},{})'.format(self.row, self.col, chr(self.tabs[r][c])))
        if shifted:
            self.printTabs()

    def copySelectTabs(self, arpg=0):
        '''Copy selected tabs.  If arpg, transform selected tabs from a chord to an arpeggio.'''
        if arpg: self.arpeggiate, size = 1, len(self.selectRows) * len(self.selectCols)
        else:    size = len(self.selectCols)
        print('copySelectTabs({}) row={}, col={}, cursorDir={}'.format(arpg, self.row, self.col, self.cursorDir), file=self.dbgFile)
        self.printSelectTabs(cols=1)
        for r in range(0, len(self.selectRows)):
            self.selectTabs.append(bytearray([ord(' ')] * size))
            self.selectHTabs.append(bytearray([ord('0')] * size))
        lsr = len(self.selectRows)
        for c in range(0, len(self.selectCols)):
            cc = self.selectCols[c]
            for r in range(0, lsr):
                rr = self.selectRows[r]
                if arpg:
                    if   self.cursorDir == self.CURSOR_DIRS['DOWN']: ccc = c * lsr + r
                    elif self.cursorDir == self.CURSOR_DIRS['UP']:   ccc = (c + 1) * lsr - r - 1
                else: ccc = c
                self.selectTabs[r][ccc]  = self.tabs[rr][cc]
                self.selectHTabs[r][ccc] = self.htabs[rr][cc]
                print('arpeggiateSelectTabs() c={}, lsr={}, selectTabs[{}][{}]={}, tabs[{}][{}]={}'.format(c, lsr, r, ccc, chr(self.selectTabs[r][ccc]), rr, cc, chr(self.tabs[rr][cc])), file=self.dbgFile)
            print('arpeggiateSelect() row={}, col={}, len(selectTabs)={}, len(selectTabs[0])={}'.format(self.row, self.col, len(self.selectTabs), len(self.selectTabs[0])), file=self.dbgFile)
            self.printSelectTabs()
            
    def deleteSelectTabs(self, delSel=True):
        '''Delete selected tabs.'''
#        print('deleteSelectTabs(): {', end='', file=self.dbgFile)
#        for c in range(0, len(self.selectCols)):
#            print('{}'.format(self.selectCols[c]), end=',', file=self.dbgFile)
#        print('}', file=self.dbgFile)
        self.printLineInfo('deleteSelectTabs({}, {})'.format(self.row, self.col))
        self.selectCols.sort(key = int, reverse = True)
        for c in range(0, len(self.selectCols)):
            self.deleteTabs(self.selectCols[c])
        if delSel:
            self.selectCols = []
        if self.displayChords == self.DISPLAY_NOTES['ENABLED']:
            self.chordsObj.printChords()
        self.maxFret = self.findMaxFret()
        self.resetPos()

    def cutSelectTabs(self):
        '''Cut selected tabs.'''
        self.copySelectTabs()
        self.deleteSelectTabs(delSel=False)
    
    def printSelectTabs(self, cols=0):
        print('printSelectTabs() len(selectCols)={}, len(selectTabs)={}'.format(len(self.selectCols), len(self.selectTabs)), file=self.dbgFile)
        if cols:
            for d in range(0, len(self.selectCols)):
                print('    selectCols[{}]={}'.format(d, self.selectCols[d]), file=self.dbgFile)
        for d in range(0, len(self.selectTabs)):
            print('    selectTabs[{}]={}'.format(d, self.selectTabs[d]), file=self.dbgFile)

    def deleteTabs(self, cc):
        row, col = self.indices2RowCol(0, cc)
#        self.dumpTabs('deleteTabs({}, {}) (row,col)=({},{}), cc={} bgn: '.format(self.row, self.col, row, col, cc))
        if self.editMode == self.EDIT_MODES['INSERT']:
            for r in range(0, self.numStrings):
                for c in range(cc, len(self.tabs[r]) - 1):
                    self.tabs[r][c] = self.tabs[r][c + 1]
                    self.htabs[r][c] = self.htabs[r][c + 1]
            self.printTabs()
        elif self.editMode == self.EDIT_MODES['REPLACE']:
            for r in range(0, self.numStrings):
                tab = ord('-')
                self.tabs[r][cc] = tab
                self.htabs[r][cc] = ord('0')
                if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                    if self.isFret(chr(tab)):
                        self.printNote(r + row + self.numStrings, col, self.getNote(r + 1, tab))
                    else:
                        self.prints(chr(tab), r + row + self.numStrings, col, self.styles['NAT_NOTE'])
                self.prints(chr(tab), r + row, col, self.styles['TABS'])
#        self.dumpTabs('deleteTabs({}, {}) col={} end: '.format(self.row, self.col, col))
    
    def pasteSelectTabs(self):
        '''Paste selected tabs as arpeggio.'''
        col, row = self.col, self.row
        lsr, lsc, lst = len(self.selectRows), len(self.selectCols), len(self.selectTabs[0])
        print('pasteSelectTabs(bgn) arpeggiate={}, row={}, col={}, lsr={}, endRow={}'.format(self.arpeggiate, row, col, lsr, self.endRow(self.row2Line(row))), file=self.dbgFile)
        while lsr > self.endRow(self.row2Line(row)) - row + 1:
            row -= 1
            print('pasteSelectTabs(--row) lsr={}, endRow={}, row={}'.format(lsr, self.endRow(self.row2Line(row)), row), file=self.dbgFile)
        rr, cc = self.rowCol2Indices(row, col)
        if self.arpeggiate: ls = lst
        else:               ls = lsc
        print('pasteSelectTabs() row={}, col={}, rr={}, cc={}'.format(row, col, rr, cc), file=self.dbgFile)
        if self.editMode == self.EDIT_MODES['INSERT']:
            for c in range(len(self.tabs[0]) - 1, cc - 1, -1):
                for r in range(0, lsr):
                    if c >= ls + cc:
                        self.tabs[r][c] = self.tabs[r][c - ls]
                        self.htabs[r][c] = self.htabs[r][c - ls]
                        print('pasteSelectTabs(INSERT) c={} >= cc={} + ls={}, tabs[{}][{}]={}'.format(c, cc, ls, r, c, chr(self.tabs[r][c])), file=self.dbgFile)
                    elif self.arpeggiate:
                        self.tabs[r][c] = ord('-')
                        self.htabs[r][c] = ord('-')
                        print('pasteSelectTabs(INSERT) c={} < cc={} + lst={}, tabs[{}][{}]={}'.format(c, cc, lst, r, c, chr(self.tabs[r][c])), file=self.dbgFile)
        elif self.arpeggiate and self.editMode == self.EDIT_MODES['REPLACE']:
            for c in range(cc, cc + lst):
                if c < len(self.tabs[0]):
                    for r in range(0, lsr):
                        self.tabs[r][c] = ord('-')
                        self.htabs[r][c] = ord('-')
                        print('pasteSelectTabs(REPLACE) tabs[{}][{}]={}'.format(r, c, chr(self.tabs[r][c])), file=self.dbgFile)
                else:
                    self.printe('ERROR pasteSelectTabs() c={} >= len(tabs[0])={} skip remaining columns'.format(c, len(self.tabs[0])))
                    break
        range_error = 0
        for c in range(0, lsc):
            if range_error: break
            for r in range(0, lsr):
                if self.arpeggiate:
                    if   self.cursorDir == self.CURSOR_DIRS['DOWN']: ccc = c * lsr + r
                    elif self.cursorDir == self.CURSOR_DIRS['UP']:   ccc = (c + 1) * lsr - r - 1
                else: ccc = c
                if ccc + cc < len(self.tabs[0]):
                    self.tabs[r + rr][ccc + cc] = self.selectTabs[r][ccc]
                    self.htabs[r + rr][ccc + cc] = self.selectHTabs[r][ccc]
                    print('    tabs[{}][{}]={}'.format(r + rr, ccc + cc, chr(self.tabs[r + rr][ccc + cc])), file=self.dbgFile)
                else:
                    self.printe('ERROR pasteSelectTabs() ccc={} + cc={} >= len(tabs[0])={} skip remaining rows and columns'.format(ccc, cc, len(self.tabs[0])))
                    range_error = 1
                    break
            print('pasteSelectTabs(loop1) c={}, sc={}'.format(c, self.selectCols[c]), file=self.dbgFile)
            self.selectStyle(self.selectCols[c], self.styles['NORMAL'], rList=self.selectRows)
        if self.editMode == self.EDIT_MODES['INSERT']:
            self.printTabs()
        elif self.editMode == self.EDIT_MODES['REPLACE']:
            for c in range(cc, cc + ls):
                if c >= len(self.tabs[0]):
                    self.printe('ERROR pasteSelectTabs() c={} + ls={} >= len(tabs[0])={} skip remaining columns'.format(c, ls, len(self.tabs[0])))
                    break
                col = self.index2Col(c)
                if c % self.numTabsPerStringPerLine == 0:
                    row += self.lineDelta()
                    print('pasteSelectTabs(wrap) row={}, col={}, c={}'.format(row, col, c), file=self.dbgFile)
                for r in range(rr, rr + lsr):
                    row = self.indices2Row(r, c)
                    tab = self.tabs[r][c]
                    print('pasteSelectTabs(loop2) row={}, col={}, r={}, c={}, tab[{}][{}]={}'.format(row, col, r, c, r, c, chr(tab)), file=self.dbgFile)
                    if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                        if self.isFret(chr(tab)):
                            if self.htabs[r][c] == ord('1'):
                                note = self.getHarmonicNote(r + 1, tab)
                                self.printNote(row + r + self.numStrings, col, note, hn=1)
                            else:
                                note = self.getNote(r + 1, tab)
                                self.printNote(row + self.numStrings, col, note)
                        else:
                            self.prints(chr(tab), row + self.numStrings, col, self.styles['NAT_NOTE'])
                    if self.htabs[r][c] == ord('1'):
                        self.prints(chr(tab), row, col, self.styles['H_TABS'])
                    else:
                        self.prints(chr(tab), row, col, self.styles['TABS'])
            self.resetPos()
        self.selectTabs, self.selectHTabs, self.selectCols, self.selectRows = [], [], [], []
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.chordsObj.printChords()
        self.resetPos()
        self.dumpTabs('pasteSelectTabs(end) row={}, col={}'.format(row, col))

    def dumpTabs(self, reason='', h=None):
        print('dumpTabs({})'.format(reason), file=self.dbgFile)
        for line in range(0, self.numLines):
            for r in range(0, self.numStrings): #len(self.tabs)):
                if r == 0:
                    print('L={}: '.format(line), end='', file=self.dbgFile)
                    for c in range(0, self.numTabsPerStringPerLine):
                        print('{}'.format(self.getColMod(c)), end='', file=self.dbgFile)
                    print(file=self.dbgFile)
                print('R={}: '.format(r), end='', file=self.dbgFile)
                for c in range(0, self.numTabsPerStringPerLine):
                    if h is None:
                        print(chr(self.tabs[r][c + line * self.numTabsPerStringPerLine]), end='', file=self.dbgFile)
                    else:
                        print(chr(self.htabs[r][c + line * self.numTabsPerStringPerLine]), end='', file=self.dbgFile)
                print('', file=self.dbgFile)
    
    def printLineInfo(self, reason):
        print('{} numStrings={}, numLines={}, lineDelta={},'.format(reason, self.numStrings, self.numLines, self.lineDelta()), end='', file=self.dbgFile)
        for line in range(0, self.numLines):
            print(' bgnRow{}={}, endRow{}={},'.format(line, self.bgnRow(line), line, self.endRow(line)), end='', file=self.dbgFile)
        print(' lastRow={}, bgnCol={}, endCol={}'.format(self.lastRow, self.bgnCol(), self.endCol()), file=self.dbgFile)
    
    def printTabs(self):
        '''Print tabs using ANSI escape sequences to control the cursor position, foreground and background colors, and brightness'''
        self.printLineInfo('printTabs({}, {}) bgn'.format(self.row, self.col))
        if self.outFile == None: self.clearScreen()
        self.printFileMark('<BGN_TABS_SECTION>')
        for line in range(0, self.numLines):
            for r in range(0, self.numStrings):
                row = r + line * self.lineDelta() + self.ROW_OFF
                for c in range(0, self.numTabsPerStringPerLine):
                    tab = self.tabs[r][c + line * self.numTabsPerStringPerLine]
                    style = self.styles['TABS']
                    if chr(self.htabs[r][c + line * self.numTabsPerStringPerLine]) == '1':
                        style = self.styles['H_TABS']
                    if c == 0:
                        self.prints('{}'.format(r + 1), row, self.editModeCol, style)
                        if self.cursorDir == self.CURSOR_DIRS['DOWN']:
                            self.prints(chr(self.capo), row, self.cursorModeCol, self.styles['NUT_DN'])
                        elif self.cursorDir == self.CURSOR_DIRS['UP']:
                            self.prints(chr(self.capo), row, self.cursorModeCol, self.styles['NUT_UP'])
                    self.prints(chr(tab), row, c + self.COL_OFF, style)
                print(file=self.outFile)
            print()
        self.printFileMark('<END_TABS_SECTION>')
        if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
            self.printFileMark('<BGN_NOTES_SECTION>')
            for line in range(0, self.numLines):
                for r in range(0, self.numStrings):
                    row = r + line * self.lineDelta() + self.endRow(0) + 1
                    for c in range (0, self.numTabsPerStringPerLine):
                        capTab = tab = self.tabs[r][c + line * self.numTabsPerStringPerLine]
                        if self.isFret(chr(tab)):
                            capTab = self.getFretByte(self.getFretNum(tab) + self.getFretNum(self.capo))
                        if c == 0:
                            n = self.getNote(r + 1, ord('0'))
                            self.printNote(row, self.editModeCol, n)
                            if self.cursorDir == self.CURSOR_DIRS['DOWN']:
                                self.prints(chr(self.capo), row, self.cursorModeCol, self.styles['NUT_DN'])
                            elif self.cursorDir == self.CURSOR_DIRS['UP']:
                                self.prints(chr(self.capo), row, self.cursorModeCol, self.styles['NUT_UP'])
                        if self.isFret(chr(capTab)):
                            if chr(self.htabs[r][c + line * self.numTabsPerStringPerLine]) == '1':
                                print('printTabs() tab={}, capTab={}, chr(tab)={}, chr(capTab)={}, tabFN={}, capoFN={}'.format(tab, capTab, chr(tab), chr(capTab), self.getFretNum(tab), self.getFretNum(capTab)), file=self.dbgFile)
                                n = self.getHarmonicNote(r + 1, tab)
                                self.printNote(row, c + self.COL_OFF, n, hn=1)
                            else:
                                n = self.getNote(r + 1, tab)
                                self.printNote(row, c + self.COL_OFF, n)
                        else: self.prints(chr(tab), row, c + self.COL_OFF, self.styles['NAT_NOTE'])
                    print(file=self.outFile)
                print()
            self.printFileMark('<END_NOTES_SECTION>')
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.printFileMark('<BGN_CHORDS_SECTION>')
            self.chordsObj.printChords()
            self.printFileMark('<END_CHORDS_SECTION>')
        if self.displayLabels == self.DISPLAY_LABELS['ENABLED']:
            self.printFileMark('<BGN_LABELS_SECTION>')
            for line in range(0, self.numLines):
                r = line * self.lineDelta() + 1
                if self.outFile == None:
                    self.printCursorAndEditModes(r)
                else: 
                    self.printPageAndLine(r, line)
                    if self.outFile != None: print(file=self.outFile)
                self.printColNums(r)
                if self.outFile != None: print(file=self.outFile)
#            self.printFileMark('<END_LABELS_SECTION>')
        if self.row > 0 and self.col > 0:
            print(self.CSI + self.styles['NORMAL'] + self.styles['CONS'] + self.CSI + '{};{}H'.format(self.row, self.col), end='') # restore the console cursor to the given position (row, col) and set the foreground and background color
        self.printLineInfo('printTabs({}, {}) end'.format(self.row, self.col))

    def printFileMark(self, mark):
        if self.outFile != None:
            if mark == '<BGN_TABS_SECTION>' or mark == '<END_TABS_SECTION>':
                print('{}'.format(mark), file=self.outFile)
            else:
                print(self.CSI + self.styles['NORMAL'] + self.styles['CONS'] + self.CSI + '{};{}H{}'.format(1, 1, mark), file=self.outFile)
    
    def getNoteStyle(self, note, style, hn=None):
        if hn is None:
            natStyle = style + self.styles['NAT_NOTE']
            fltStyle = style + self.styles['FLT_NOTE']
            shpStyle = style + self.styles['SHP_NOTE']
        else:
            natStyle = style + self.styles['NAT_H_NOTE']
            fltStyle = style + self.styles['FLT_H_NOTE']
            shpStyle = style + self.styles['SHP_H_NOTE']
        if len(note.name) > 1:
            if note.name[1] == '#':
                if self.enharmonic == self.ENHARMONIC['FLAT']:
                    return fltStyle
                else:
                    return shpStyle
            elif note.name[1] == 'b':
                if self.enharmonic == self.ENHARMONIC['SHARP']:
                    return shpStyle
                else:
                    return fltStyle
        else:
            return natStyle
    
    def printNote(self, row, col, note, style='', hn=None):
        style = self.getNoteStyle(note, style, hn)
        self.prints(note.name[0], row, col, style)

    def printStatus(self):
        r, c = self.rowCol2Indices(self.row, self.col)
        tab = chr(self.tabs[r][c])
        print('printStatus({}, {}) r={}, c={}, tab={}'.format(self.row, self.col, r, c, tab), file=self.dbgFile)
        if   self.isFret(tab): self.printTabFretInfo(tab, r, c)
        elif tab in self.mods: self.printTabModInfo(tab, r, c)
        else:                  self.printDefTabInfo(tab, r, c)
        self.clearRow(arg=0, file=self.outFile)
        self.resetPos()
        
    def printTabFretInfo(self, tab, r, c):
        s, ss = r + 1, self.getOrdSfx(r + 1)
        f, fs = self.getFretNum(ord(tab)), self.getOrdSfx(self.getFretNum(ord(tab)))
        statStyle, fretStyle, typeStyle, noteStyle = self.CSI + self.styles['STATUS'], self.CSI + '32;40m', self.CSI + '33;40m', self.CSI + '32;40m'
        if self.htabs[r][c] == ord('1'): n, noteType, tabStyle = self.getHarmonicNote(s, ord(tab)), 'harmonic', self.CSI + self.styles['H_TABS']
        else:                            n, noteType, tabStyle = self.getNote(s, ord(tab)), None, self.CSI + self.styles['TABS']
        if len(n.name) > 1:
            if n.name[1] == '#': noteStyle = self.CSI + '31;40m'
            else:                noteStyle = self.CSI + '36;40m'
        print('printTabFretInfo({}) r={}, c={}, tab={}, n.n={}, n.o={}, n.i={}, {}'.format(noteType, r, c, tab, n.name, n.getOctaveNum(), n.index, n.getPhysProps()), file=self.dbgFile)
        print(tabStyle + self.CSI + '{};{}H{}'.format(self.lastRow, 1, tab), end='', file=self.outFile)
        if f != 0: print(fretStyle + ' {}{}'.format(s, ss) + statStyle + ' string ' + fretStyle + '{}{}'.format(f, fs) + statStyle + ' fret ', end='', file=self.outFile)
        else:      print(fretStyle + ' {}{}'.format(s, ss) + statStyle + ' string ' + fretStyle + 'open' + statStyle + ' fret ', end='', file=self.outFile)
        if noteType: print(typeStyle + '{} '.format(noteType), end='', file=self.outFile)
        print(noteStyle + '{}{}'.format(n.name, n.getOctaveNum()), end='', file=self.outFile)
        print(statStyle + ' index=' + fretStyle + '{}'.format(n.index), end='', file=self.outFile)
        print(statStyle + ' freq=' + fretStyle + '{:03.2f}'.format(n.getFreq()) + statStyle + 'Hz', end='', file=self.outFile)
        print(statStyle + ' wvln=' + fretStyle + '{:04.3f}'.format(n.getWaveLen()) + statStyle + 'm', end='', file=self.outFile)
    
    def printTabModInfo(self, tab, r, c):
        ph, nh, s, ss = 0, 0,  r + 1, self.getOrdSfx(r + 1)
        prevFN, nextFN, prevNote, nextNote, dir1, dir2 = None, None, None, None, None, None
        if self.isFret(chr(self.tabs[r][c-1])): 
            prevFN = self.getFretNum(self.tabs[r][c-1])
            if self.htabs[r][c-1] == ord('1'): 
                prevNote = self.getHarmonicNote(s, self.tabs[r][c-1])
                ph=1
            else: prevNote = self.getNote(s, self.tabs[r][c-1])
        if self.isFret(chr(self.tabs[r][c+1])): 
            nextFN = self.getFretNum(self.tabs[r][c+1])
            if self.htabs[r][c+1] == ord('1'): 
                nextNote = self.getHarmonicNote(s, self.tabs[r][c+1])
                nh=1
            else: nextNote = self.getNote(s, self.tabs[r][c+1])
        if prevFN is not None and nextFN is not None:
            if   prevFN < nextFN: dir1, dir2 = 'up',   'on'
            elif prevFN > nextFN: dir1, dir2 = 'down', 'off'
        print('printTabModInfo({}, {}) tab={}, pfn={}, nfn={}'.format(r, c, tab, prevFN, nextFN), file=self.dbgFile)
        self.modsObj.setMods(dir1=dir1, dir2=dir2, prevFN=prevFN, nextFN=nextFN, prevNote=prevNote, nextNote=nextNote, ph=ph, nh=nh)
        print(self.CSI + self.styles['TABS'] + self.CSI + '{};{}H{} '.format(self.lastRow, 1, tab), end='', file=self.outFile)
        print(self.CSI + self.styles['TABS'] + '{}{}'.format(s, ss) + self.CSI + self.styles['STATUS'] + ' string {}'.format(self.mods[tab]), end='', file=self.outFile)
    
    def printDefTabInfo(self, tab, r, c):
        s, ss, tabStyle, statStyle = r + 1, self.getOrdSfx(r + 1), self.CSI + self.styles['TABS'], self.CSI + self.styles['STATUS']
        print('printDefTabInfo({}, {}) tab={}'.format(r, c, tab), file=self.dbgFile)
        print(tabStyle + self.CSI + '{};{}H{} '.format(self.lastRow, 1, tab), end='', file=self.outFile)
        print(tabStyle + '{}{}'.format(s, ss) + statStyle + ' string ' + tabStyle + 'muted' + statStyle + ' not played', end='', file=self.outFile)
    
    def prints(self, c, row, col, style):
       print(self.CSI + style + self.CSI + '{};{}H{}'.format(row, col, str(c)), end='', file=self.outFile)

    def printe(self, info, row=None, col=None, style=None):
        if row is None: row=self.row
        if col is None: col=self.col
        if style == None: style = self.styles['ERROR']
        print('printe({}, {}) {}'.format(row, col, info), file=self.dbgFile)
        print(self.CSI + style + self.CSI + '{};{}H{}'.format(self.lastRow, 1, info), end='')
        self.clearRow(arg=0, file=self.outFile)
        self.resetPos()
        
    def hilite(self, text):
        return self.CSI + self.styles['ERROR'] + text + self.CSI + self.styles['CONS']
        
    def getNote(self, str, tab):
        '''Return note object given string number and tab fret number byte.'''
        fret = self.getFretNum(tab)
        cfret = fret + self.getFretNum(self.capo)
        return notes.Note(self.getNoteIndex(str, cfret), self.enharmonic)

    def getHarmonicNote(self, str, tab):
        '''Return harmonic note object given string number and tab fret number byte.'''
        fret = self.getFretNum(tab)
        hfret = self.HARMONIC_FRETS[fret]
        chfret = hfret + self.getFretNum(self.capo)
        note = notes.Note(self.getNoteIndex(str, chfret), self.enharmonic)
        print('getHarmonicNote({}, {}) f={}, hf={}, chf={}, n.i={}, n.n={}, n.o={})'.format(str, tab, fret, hfret, chfret, note.index, note.name, note.getOctaveNum()), file=self.dbgFile)
        return note
        
    def getNoteIndex(self, str, f):
        '''Converts string numbering from 1 based with str=1 denoting the high E first string and str=numStrings the low E sixth string.'''
        s = self.numStrings - str                     # Reverse and zero base the string numbering: str[1 ... numStrings] => s[(numStrings - 1) ... 0]
        i = self.stringMap[self.stringKeys[s]] + f    # calculate the fretted note index using the sorted map
#        print('getNoteIndex() str={}, s={}, f={}, i={}, sk={}, sm={}'.format(str, s, f, i, self.stringKeys[s], self.stringMap[self.stringKeys[s]]), file=self.dbgFile)
        return i
    
    def printChord(self, c=None, dbg=1):
        '''Analyse the notes at the given column and if they form a chord print the chord in the chords section.'''
        self.chordsObj.printChord(c, dbg)
        
    def isTab(self, c):
        if c == '-' or self.isFret(c) or self.isMod(c): return True
        return False

    def isMod(self, c):
        if c in self.mods: return True
        return False

    @classmethod
    def isFret(cls, c):
        if '0' <= c <= '9' or 'a' <= c <= 'o': return True
        return False

    @staticmethod
    def getFretNum(fretByte):
        fretNum = fretByte - ord('0')
        if fretByte >= ord('a'): fretNum = fretByte - (ord('a') - 10)
        return fretNum
        
    @staticmethod
    def getFretByte(fretNum):
        fretByte = fretNum + ord('0')
        if 10 <= fretNum <= 24: fretByte = fretNum + ord('a') - 10
        return fretByte
    
    @staticmethod
    def getOrdSfx(n):
        m = n % 10
        if   m == 1 and n != 11: return 'st'
        elif m == 2 and n != 12: return 'nd'
        elif m == 3 and n != 13: return 'rd'
        else:                    return 'th'
    
    @staticmethod
    def clearScreen(arg=2, file=None):
        print(Tabs.CSI + '{}J'.format(arg), file=file)

    @staticmethod
    def clearRow(arg=2, file=None):
        print(Tabs.CSI + '{}K'.format(arg), end='', file=file)
        
    def printHelpSummary(self):
        summary = \
        '''
Note the console window should be at least as wide as the number of tabs + 2.  Window resizing is not supported.  
The command line arg -t specifies the number of tabs per string per line.  
The command line arg -f specifies the file name to read from and write to.  
The command line arg -s specifies the spelling of the string names e.g. -s 'E2A2D3G3B3E4' is 6 string standard guitar tuning.  
The command line arg -S specifies the spelling of the string names via an alias e.g. -s 'GUITAR' is 6 string standard guitar tuning.  
The command line arg -k specifies the fret to place the capo at [0-9], [a-o].  
The command line arg -i specifies the automatic cursor advance direction is downward rather than upward.  
The command line arg -F specifies the use of flat enharmonic notes instead of sharp enharmonic notes.  
The command line arg -a enables display of the optional label row and the cursor and edit modes.  
The command line arg -n enables display of the optional notes section.  
The command line arg -b enables display of the optional chords section.
The command line arg -l moves the cursor to the last tab on the current line of the current string  
The command line arg -L moves the cursor to the last tab on the current line of all strings  
The command line arg -z moves the cursor to the last tab on the last line of the current string  
The command line arg -Z moves the cursor to the last tab on the last line of all strings  
The command line arg -h enables display of this help info.  

Tabs are displayed in the tabs section with an optional row to label and highlight the selected tab column.  
An optional notes section and an optional chords section can also be displayed below the tabs section.  
A number of lines can be displayed where each line has its own tabs, notes, and chords sections.  
''' + self.hilite('Tabs section:') + ''' 
Tabs are displayed using rows and columns of ASCII characters, essentially one character per tab.  
Tabs are represented by the single digits [0-9] and the letters [a-o], rather than [10-24].  
The value '0' represents the open string.  The minus character '-' is used for padding and represents an unplayed string.  
The value '2' represents playing the string 1 full step above the nut, 'c' represents 12 half steps above the nut or an octave higher.  

Optional tab modification characters are used to denote tonal expression such as bending, sliding, hammer on/off, vibrato etc...  
Tab modifications are implemented as a customizable dictionary in the ''' + self.hilite('mods.py') + ''' module.  
You can change or add tab modifications by simply editing the ''' + self.hilite('mods.py') + ''' file. 
The dictionary keys are the modification characters and the values describe how to interpret the characters.  
When the cursor occupies the same row and column as a tab modifier the dictionary value is printed on the last row.  

Each row has a number of columns that represent the tab characters for a particular string as they are played sequentially in time from left to right.  
Rows are labelled using 1 based string numbers (increasing in the downward direction) in the first display column.  
The nut and capo are displayed in the 2nd column with the string label to the left and all the tabs to the right.  
The capo can have values corresponding to the fret numbers [0-9], [a-o], where 0 denotes no capo.  
To enter a tab simply navigate to the desired row and column using the arrow, Home, End, PageUp, or PageDown keys and then enter the character.  
Note the cursor will automatically advance to the right, up, down, up and right, or down and right depending on the cursor mode.  
Also note the tabs section is the only section that is editable.  The navigation keys will automatically skip over the notes and or chords sections.  
''' + self.hilite('Notes section:  \'Ctrl N\'') + ''' 
The notes section has the same number of rows and columns as the tabs section and displays the note names corresponding to the tabs in the tabs section.  
The notes section uses the color red to indicate a sharp note and blue to represent a flat note.  
Note any optional tab modification characters present in the tabs section are also displayed in the notes section.  
''' + self.hilite('Chords section:  \'Ctrl B\'') + ''' 
Chords are spelled vertically so that they line up with the tabs and notes and potentially every column can display a chord.  
Chord names are automatically calculated and recalculated whenever the number of tabs in a given column is greater than one.  
The maximum chord name length is set to 5 and is not currently configurable.
The chords section also uses red to indicate a sharp chord and blue to represent a flat chord, but only on the first character, the root note.  
Minor and diminished chords use the color blue for the 'm' or the 'dim' characters.  

Note the tabs, notes, and chords can be saved to a file and if you 'cat' the file you can see the ANSI colors.  
        '''
        print(summary, file=self.dbgFile)
        print(summary)
        
def main():
    Tabs()

if __name__ == "__main__":
    main()

# NOTE to fix the console foreground and background colors from a bad run try the color cmd, 'Color ?' or 'Color 07' restores white on black.
'''
e.g. Tabs Section: 6 string guitar with standard tuning 'E2A2D3G3B3E4': Carlos Santana, Black Magic Woman:
  1234567891123456789212345678931234567894123456789512345678961234567897123456789812345678991234567890123456789112345678921234567893123456789412345678951234567896
10----------------------------5=----------------5=---------------a--a---------------------------------------------------------------------------------------------
20--8/6=---------6+8+6=---------8=6/5=-8=6=5/3=---8=6/5=-8=6=5--a----d-f\da-d\f\d+a-------------------------------------------------------------------------------
30-------7\9\7=---------9\7=-----------------------------------a--------------------------------------------------------------------------------------------------
40----------------------------------------------------------------------------------------------------------------------------------------------------------------
50----------------------------------------------------------------------------------------------------------------------------------------------------------------
60----------------------------------------------------------------------------------------------------------------------------------------------------------------
Optional Notes Section: 6 string guitar with standard tuning 'E2A2D3G3B3E4': Carlos Santana, Black Magic Woman:
E0----------------------------A=----------------A=---------------D--D---------------------------------------------------------------------------------------------
B0--G/F=---------F+G+F=---------G=F/E=-G=F=E/D=---G=F/E=-G=F=E--A----C-D\CA-C\D\C+A-------------------------------------------------------------------------------
G0-------D\E\D=---------E\D=-----------------------------------F--------------------------------------------------------------------------------------------------
D0----------------------------------------------------------------------------------------------------------------------------------------------------------------
A0----------------------------------------------------------------------------------------------------------------------------------------------------------------
E0----------------------------------------------------------------------------------------------------------------------------------------------------------------
||
| -- Capo fret number (0 means no capo)
---- String numbers and String note names
 
Desired new features list:
    Optimize printTabs?
    Compress arpeggio -> chord; Expand chord -> arpeggio?
    Print arpeggio chord names?
    Analysis for scale and key signature calculation
    Improve file I/O and usage
    Scroll through pages and lines
    Handle window resizing
    Undo/redo functionality
    Indicate rhythmic info like note duration and rests etc
    Unicode chars
    Display sheet music notation
    Unit tests and or regression tests
'''
