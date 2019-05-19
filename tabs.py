'''tabs.py module.  Main entry point, class list: [Tabs].  Note main simply instantiates an instance of the Tabs class which handles the entire session.'''

'''Thus all methods are essentially private.  Note some functionality is deemed customizable by the user and is thus factored out into a separate module.  
e.g. The tab modifications are in mods.py, the string tunings and aliases are in strings.py, and the chord discovery and name calculations are in chords.py.'''

import os, sys, shutil

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
import collections

class Tabs(object):
    '''Model musical tab notation and tab editor functionality.'''
    ESC = '\033'
    CSI = '\033\133'
    QUIT_STR = 'Received Quit Cmd: Exiting'
    DBG_NAME = "Debug.txt"
    DBG_FILE = open(DBG_NAME, "w")
    
    def __init__(self, inName='tabs.tab', outName='tabs.tab'):
        '''Initialize the Tabs object and start the interactive loop method.  The inName and outName can be the same or different.'''
        self.init(inName, outName)
        self.loop()
    
    def init(self, inName='tabs.tab', outName='tabs.tab'):
        '''Initialize class instance, enable automatic reset of console after each call via implicit print(colorama.Style.RESET_ALL).'''
        colorama.init(autoreset=True)
        Tabs.clearScreen()
        
        self.initFiles(inName, outName)
        self.initConsts()
#        self.testDict()
#        self.testAnsi2()
#        self.testAnsi3()
        self.registerUiCmds()                                  # register the dictionary for all the user interactive commands
        self.mods = {}                                         # dict of tab modification characters -> contextual descriptions 
        self.dbgMove = True                                    # used for finding bugs in basic movement functionality
        self.capo = ord('0')                                   # essentially added to every tab that is a fret, written to the outFile and read from the inFile
        self.maxFret = ord('0')                                # update in setTab() and readTabs()
        self.chordsObj = None                                  # the chords.Chords instance
        
        self.htabs = []                                        # list of bytearrays, one for each string; for harmonic tabs
        self.tabCount = 0                                      # used by appendTabs() 
        self.tabs = []                                         # list of bytearrays, one for each string; for all the tabs
        self.chordInfo = {}                                    # dict column -> (list of dict intervals -> note names) i.e. dict col -> list of imaps for status chord info
        self.selectChords = {}                                 # dict chord name -> imap, for displaying the selected chord name and imap
        self.selectImaps = {}                                  # dict imap string -> imap, for displaying intervals corresponding to selected chord name & imap
        self.analyzeIndex = -1                                 # index being analyzed for chord info
        self.chordStatusCol = None                             # tab column index used to display chord info on status row
        
        self.arpeggiate = 0                                    # used to transform chords to arpeggios
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
        self.CHORDS_LEN = 0                                    # number of rows used to display chords on a given line
        self.NOTES_LEN = 0                                     # number of rows used to display notes  on a given line
        self.INTERVALS_LEN = 0                                 # number of rows used to display intervals on a given line
        self.NUM_FRETS = 24                                    # number of frets (might make this a list for each string)?
        self.IVAL_LABEL = 'INTRVL'                             # label displayed for intervals (first col)
        
        self.hiliteCount = 0                                   # statistic for measuring efficiency
        self.hiliteColNum = 0                                  # used to hilite the current cursor column and unhilite the previous cursor column
        self.hiliteRowNum = 0                                  # used to hilite the current cursor row    and unhilite the previous cursor row
        self.hilitePrevRowPos = 0
        self.row = self.ROW_OFF                                # current cursor row    number
        self.col = self.COL_OFF                                # current cursor column number
        self.editModeCol = 1                                   # column to display edit  mode
        self.cursorModeCol = 2                                 # column to display cursor mode
        self.lastRow = self.ROW_OFF + self.numLines * self.lineDelta() - 1  # the row used to display status, set here in case initStrings() fails e.g. tab mod info or error info etc...
        
        self.displayLabels = self.DISPLAY_LABELS['DISABLED']   # enable or disable the display of the modes and labels section before each line
        self.displayNotes = self.DISPLAY_NOTES['DISABLED']     # enable or disable the display of the notes section for each line
        self.displayIntervals = self.DISPLAY_INTERVALS['DISABLED'] # enable or disable the display of the intervals section for each line
        self.displayChords = self.DISPLAY_CHORDS['DISABLED']   # enable or disable the display of the chords section for each line
        self.cursorDir = self.CURSOR_DIRS['DOWN']              # affects the automatic cursor movement (up/down) when entering a tab in chord or arpeggio mode
        self.enharmonic = self.ENHARMONICS['SHARP']            # toggle between displaying enharmonic notes as flat or sharp
        self.editMode = self.EDIT_MODES['REPLACE']             # toggle between modifying the current character or inserting a new character
        self.cursorMode = self.CURSOR_MODES['MELODY']          # toggle between different cursor modes; melody, chord, and arpeggio
        
        self.cmdLine = ''
        for arg in sys.argv:
            self.cmdLine += arg + ' '
        print(self.cmdLine, file=Tabs.DBG_FILE)
        self.argMap = {}
        cmdArgs.parseCmdLine(self.argMap)
        print('tabs.py args={}'.format(self.argMap), file=Tabs.DBG_FILE)
        if 'f' in self.argMap and len(self.argMap['f']) > 0:
            self.inName = self.argMap['f'][0]                       # file to read from
            self.outName = self.argMap['f'][0]                      # file to write to, only written to with the saveTabs command
            backupName = self.outName + '.bak'
            if os.path.isfile(backupName):
                print('saving backup file: {}'.format(backupName), file=Tabs.DBG_FILE)
                shutil.copy2(self.outName, backupName)
        if 't' in self.argMap and len(self.argMap['t']) > 0:
            self.initTabLen(self.argMap['t'])                       # set number of tabs/columns per line (and per string)
        if 'S' in self.argMap and len(self.argMap['S']) > 0:
            self.initStrings(alias=self.argMap['S'])                # set string tuning with alias
        elif 's' in self.argMap and len(self.argMap['s']) > 0:
            self.initStrings(spelling=self.argMap['s'])             # set string tuning with string spelling
        else:
            self.initStrings()                                 # set default string tuning
        self.setLastRow()                                      # calculate last row, depends on numStrings which is supposed to be set in initStrings()
        self.numTabs = self.numStrings * self.numTabsPerString # total number of tab characters
        
        try:
            with open(self.inName, 'rb') as self.inFile:
                self.readTabs(readSize=500)
        except Exception as e: # FileNotFoundError as e:
            print('init() Exception: {}'.format(e), file=Tabs.DBG_FILE)
            mult = 1
            tabs = '0123456789abcdefghijklmno'
            print('init() seeding tabs with \'{}\', len(tabs):{}, numTabsPerString:{} = numLines:{} * numTabsPerStringPerLine:{}'.format(tabs, len(tabs), self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine), file=Tabs.DBG_FILE)
            if len(tabs) > self.numTabsPerStringPerLine: 
                tabs = tabs[:self.numTabsPerStringPerLine]
                print('init() truncated tabs to \'{}\', setting tabs = tabs[:self.numTabsPerStringPerLine], len(tabs):{} * mult:{} = {}'.format(tabs, len(tabs), mult, len(tabs) * mult), file=Tabs.DBG_FILE)
            else: 
                print('init() setting tabs len'.format(), file=Tabs.DBG_FILE)
                for i in range(len(tabs) - 1, -1, -1):
                    print('init() i={}'.format(i), file=Tabs.DBG_FILE)
                    if not (self.numTabsPerStringPerLine % i):
                        tabs = tabs[:i]
                        mult = int(self.numTabsPerStringPerLine / i)
                        break
                print('init() truncated tabs to \'{}\', setting tabs = tabs[:mult], len(tabs):{} * mult:{} = {}'.format(tabs, len(tabs), mult, len(tabs) * mult), file=Tabs.DBG_FILE)
            for r in range(0, self.numStrings):
                self.tabs.append(bytearray([ord(t) for t in tabs] * mult))
                self.htabs.append(bytearray([ord('0') for t in tabs] * mult))
        finally:
            self.modsObj = mods.Mods(self)
            self.mods = self.modsObj.getMods()
            print('init() mods=\{ ', file=Tabs.DBG_FILE)
            for k in self.mods:
                print('{}:{}, '.format(k, self.mods[k]), file=Tabs.DBG_FILE)
            if 'F' in self.argMap and len(self.argMap['F']) == 0:
                self.toggleEnharmonic()                           # toggle enharmonic note display from sharp to flat
            if 'i' in self.argMap and len(self.argMap['i']) == 0:
                self.toggleCursorDir(dbg=1)                       # toggle automatic cursor movement direction from down to up
            if 'k' in self.argMap and len(self.argMap['k']) > 0:
                self.setCapo(c=self.argMap['k'][0])               # set capo at desired fret
            if 'a' in self.argMap and len(self.argMap['a']) == 0:
                self.toggleDisplayLabels(pt=0)                    # toggle the display of the edit mode, cursor mode, and column number labels in first row for each line
            if 'b' in self.argMap and len(self.argMap['b']) == 0:
                self.toggleDisplayChords(pt=0)                    # enable the chords section display
            if 'o' in self.argMap and len(self.argMap['o']) == 0:
                self.toggleDisplayIntervals(pt=0)                 # enable the intervals section display
            if 'n' in self.argMap and len(self.argMap['n']) == 0:
                self.toggleDisplayNotes(pt=0)                     # enable the notes section display
            if 'l' in self.argMap and len(self.argMap['l']) == 0:
                self.goToLastTab(cs=1)                            # go to last tab on current line of current string
            if 'L' in self.argMap and len(self.argMap['L']) == 0:
                self.goToLastTab()                                # go to last tab on current line of all strings
            if 'z' in self.argMap and len(self.argMap['z']) == 0:
                self.goToLastTab(cs=1, ll=1)                      # go to last tab on last line of current string
            if 'Z' in self.argMap and len(self.argMap['Z']) == 0:
                self.goToLastTab(ll=1)                            # go to last tab on last line of all strings
            if 'h' in self.argMap and len(self.argMap['h']) == 0:
                self.printHelpInfo(ui=0)                          # display the help info
            self.printTabs()                                      # display all the tabs in the tabs section, optionally display the notes and chords sections and the modes/labels row
            self.moveTo(hi=1)                                     # display the status and hilite the first tab character
    
    def testDict(self):
        a = {'one': 1, 'two': 2, 'three': 3, 'four': 4}
        b = dict(one=1, two=2, three=3, four=4)
        c = dict(zip(['one', 'two', 'three', 'four'], [1, 2, 3, 4]))
        d = dict([('two', 2), ('one', 1), ('three', 3), ('four', 4)])
        e = dict({'three': 3, 'one': 1, 'two': 2, 'four': 4})
        print('a={}'.format(a), file=Tabs.DBG_FILE)
        print('b={}'.format(b), file=Tabs.DBG_FILE)
        print('c={}'.format(c), file=Tabs.DBG_FILE)
        print('d={}'.format(d), file=Tabs.DBG_FILE)
        print('e={}'.format(d), file=Tabs.DBG_FILE)
        m = collections.OrderedDict(sorted(a.items(), key=lambda t: t[0])) #one=1, two=2, three=3)
        print('m={}'.format(m), file=Tabs.DBG_FILE)
        m['two'] = 2
        m['three'] = 3
        m = collections.OrderedDict(sorted(a.items(), key=lambda t: t[1]))
        print('m={}'.format(m), file=Tabs.DBG_FILE)
        exit()
    
    def testAnsi(self):
        print(self.CSI + self.styles['TABS']       + self.CSI + '{};{}H{}'.format(1, 1, 'TABS'), file=file)
        print(self.CSI + self.styles['H_TABS']     + self.CSI + '{};{}H{}'.format(1, 20, 'H_TABS!'), file=file)
        print(self.CSI + self.styles['NAT_NOTE']   + self.CSI + '{};{}H{}'.format(2, 1, 'NAT_NOTE'), file=file)
        print(self.CSI + self.styles['NAT_H_NOTE'] + self.CSI + '{};{}H{}'.format(2, 20, 'NAT_H_NOTE'), file=file)
        print(self.CSI + self.styles['FLT_NOTE']   + self.CSI + '{};{}H{}'.format(3, 1, 'FLT_NOTE'), file=file)
        print(self.CSI + self.styles['FLT_H_NOTE'] + self.CSI + '{};{}H{}'.format(3, 20, 'FLT_H_NOTE'), file=file)
        print(self.CSI + self.styles['SHP_NOTE']   + self.CSI + '{};{}H{}'.format(4, 1, 'SHP_NOTE'), file=file)
        print(self.CSI + self.styles['SHP_H_NOTE'] + self.CSI + '{};{}H{}'.format(4, 20, 'SHP_H_NOTE'), file=file)
        exit()
    
    def testAnsi2(self):
        print(self.CSI + '22;31;47m' + self.CSI + '{};{}H{}'.format(1, 1, 'Normal Red on White'))
        print(self.CSI +  '1;31;47m' + self.CSI + '{};{}H{}'.format(2, 1, 'Bright Red on White'))
        print(self.CSI + '22;32;47m' + self.CSI + '{};{}H{}'.format(3, 1, 'Normal Green on White'))
        print(self.CSI +  '1;32;47m' + self.CSI + '{};{}H{}'.format(4, 1, 'Bright Green on White'))
        print(self.CSI + '22;33;47m' + self.CSI + '{};{}H{}'.format(5, 1, 'Normal Yellow on White'))
        print(self.CSI +  '1;33;47m' + self.CSI + '{};{}H{}'.format(6, 1, 'Bright Yellow on White'))
        print(self.CSI + '22;34;47m' + self.CSI + '{};{}H{}'.format(7, 1, 'Normal Blue on White'))
        print(self.CSI +  '1;34;47m' + self.CSI + '{};{}H{}'.format(8, 1, 'Bright Blue on White'))
        print(self.CSI + '22;35;47m' + self.CSI + '{};{}H{}'.format(9, 1, 'Normal Magenta on White'))
        print(self.CSI +  '1;35;47m' + self.CSI + '{};{}H{}'.format(10, 1, 'Bright Magenta on White'))
        print(self.CSI + '22;36;47m' + self.CSI + '{};{}H{}'.format(11, 1, 'Normal Cyan on White'))
        print(self.CSI +  '1;36;47m' + self.CSI + '{};{}H{}'.format(12, 1, 'Bright Cyan on White'))
        print(self.CSI + '22;40;47m' + self.CSI + '{};{}H{}'.format(13, 1, 'Normal Black on White'))
        print(self.CSI +  '1;40;47m' + self.CSI + '{};{}H{}'.format(14, 1, 'Bright Black on White'))
#        print(self.CSI + '50C', end='')
#        print(self.CSI + '5A', end='')
#        print(self.CSI +  '1;32;47m' + 'Up 5 and right 50', end='')
#        print(self.CSI +  '1;32;47m' + self.CSI + '{};{}H{}'.format(15, 1, 'Bright Green on White'))
#        print(self.CSI + '25D', end='')
#        print(self.CSI + '3B', end='')
#        print(self.CSI +  '1;32;47m' + 'Down 3 and left 5', end='')
#        print(self.CSI +  '1;31;47m' + self.CSI + '{};{}H{}'.format(2, 1, 'Bright Red on White'))
#        exit()
    
    def testAnsi3(self):
        print(self.CSI + '22;31;47m' + self.CSI + '1B' + self.CSI + '1C' + 'Normal Red on White', end='')
        print(self.CSI +  '1;31;47m' + self.CSI + '1B' + self.CSI + '1C' + 'Bright Red on White', end='')
        print(self.CSI + '22;32;47m' + self.CSI + '1B' + self.CSI + '1C' + 'Normal Green on White', end='')
        print(self.CSI +  '1;32;47m' + self.CSI + '1B' + self.CSI + '1C' + 'Bright Green on White', end='')
        exit()
    
    def initFiles(self, inName, outName):
        self.inName = inName
        self.inFile = None
        self.outName = outName
        self.outFile = None
    
    def initConsts(self): # foreground 30-37, background 40-47, 0=black, 1=red, 2=green, 3=yellow, 4= blue, 5=magenta, 6=cyan, 7=white
        self.COLORS = { 'BLACK':'0', 'RED':'1', 'GREEN':'2', 'YELLOW':'3', 'BLUE':'4', 'MAGENTA':'5', 'CYAN':'6', 'WHITE':'7' }
        self.RED_WHITE = self.initText('RED', 'WHITE')
        self.BLUE_WHITE = self.initText('BLUE', 'WHITE')
        self.CYAN_WHITE = self.initText('CYAN', 'WHITE')
        self.BLACK_WHITE = self.initText('BLACK', 'WHITE')
        self.GREEN_WHITE = self.initText('GREEN', 'WHITE')
        self.YELLOW_WHITE = self.initText('YELLOW', 'WHITE')
        self.MAGENTA_WHITE = self.initText('MAGENTA', 'WHITE')
        self.BLACK_YELLOW = self.initText('BLACK', 'YELLOW')
        self.GREEN_YELLOW = self.initText('GREEN', 'YELLOW')
        self.BLUE_YELLOW = self.initText('BLUE', 'YELLOW')
        self.RED_YELLOW = self.initText('RED', 'YELLOW')
#        self.WHITE_GREEN = self.initText('WHITE', 'GREEN')
#        self.GREEN_BLACK = self.initText('GREEN', 'BLACK')
        self.styles = { 'NAT_NOTE':self.GREEN_WHITE, 'NAT_H_NOTE':self.YELLOW_WHITE,  'NAT_CHORD':self.GREEN_WHITE, 'MIN_COL_NUM':self.RED_WHITE,      'TABS':self.BLACK_WHITE,  'NUT_UP':self.BLUE_YELLOW,  'NORMAL':'22;',
                        'FLT_NOTE':self.BLUE_WHITE,  'FLT_H_NOTE':self.CYAN_WHITE,    'FLT_CHORD':self.BLUE_WHITE,  'MAJ_COL_NUM':self.BLACK_WHITE,  'H_TABS':self.BLACK_YELLOW, 'NUT_DN':self.RED_YELLOW,   'BRIGHT':'1;',
                        'SHP_NOTE':self.RED_WHITE,   'SHP_H_NOTE':self.MAGENTA_WHITE, 'SHP_CHORD':self.RED_WHITE,        'STATUS':self.MAGENTA_WHITE, 'MODES':self.BLUE_WHITE,   'ERROR':self.RED_YELLOW,   'CONS':self.BLACK_WHITE,
                        'HLT_STUS':self.CYAN_WHITE,  'IVAL_LABEL':self.YELLOW_WHITE,  'CHORD_LABEL':self.GREEN_WHITE,   'NO_IVAL':self.YELLOW_WHITE }
        self.HARMONIC_FRETS = { 12:12, 7:19, 19:19, 5:24, 24:24, 4:28, 9:28, 16:28, 28:28 }
#        self.FRET_INDICES = { 0:0, 1:1, 2:2, 3:3, 4:4, 5:5, 6:6, 7:7, 8:8, 9:9, 10:'a' }  # for moving along the fretboard?
#        self.MAJ_INDICES = [ 0, 2, 4, 5, 7, 9, 11, 12 ]                                   # for key signatures and or scales?
#        self.MIN_INDICES = [ 0, 2, 3, 5, 7, 8, 10, 12 ]                                   # for key signatures and or scales?
        self.CURSOR_DIRS = { 'DOWN':0, 'UP':1 }
        self.CURSOR_MODES = { 'MELODY':0, 'CHORD':1, 'ARPEGGIO':2 }
        self.EDIT_MODES = { 'REPLACE':0, 'INSERT':1 }
        self.ENHARMONICS = { 'FLAT':0, 'SHARP':1 }
        self.DISPLAY_LABELS = { 'DISABLED':0, 'ENABLED':1 }
        self.DISPLAY_NOTES = { 'DISABLED':0, 'ENABLED':1 }
        self.DISPLAY_INTERVALS = { 'DISABLED':0, 'ENABLED':1 }
        self.DISPLAY_CHORDS = { 'DISABLED':0, 'ENABLED':1 }
    
    def initText(self, FG, BG):
        return '3' + self.COLORS[FG] + ';4' + self.COLORS[BG] + 'm'
#        return '3' + FG + ';4' + BG + 'm'
    
    def initStrings(self, alias=None, spelling=None):
        print('initStrings(alias={}, spelling={})'.format(alias, spelling), file=Tabs.DBG_FILE)
        try:
            self.strings = strings.Strings(Tabs.DBG_FILE, alias=alias, spelling=spelling)
        except Exception as ex:
            e = sys.exc_info()[0]
            info = 'initStrings() Exception: \'{}\', e={}'.format(ex, str(e))
            self.quit(info, code=1)
        self.stringMap = self.strings.map
        self.stringKeys = self.strings.keys
        self.numStrings = len(self.stringKeys)
        if len(self.strings.map) < 1:
            print('initStrings() ERROR! invalid stringMap, numStrings={}'.format(self.numStrings), file=Tabs.DBG_FILE)
            self.quit('initStrings() ERROR! Empty stringMap!', code=1)
        self.printStringMap(file=Tabs.DBG_FILE)
    
    def printStringMap(self, file):
        print('string map = {', end='', file=file)
        for k in self.stringKeys:
            print(' {}:{}'.format(k, self.stringMap[k]), end='', file=file)
        print(' }', file=file)
    
    def initTabLen(self, numTabs):
        self.numTabsPerStringPerLine = int(numTabs[0])
        self.numTabsPerString = self.numLines * self.numTabsPerStringPerLine
        print('initTabLen() numTabsPerString:{} = numLines:{} * numTabsPerStringPerLine:{}'.format(self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine), file=Tabs.DBG_FILE)
    
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
            print(info, file=Tabs.DBG_FILE)
            raise Exception(info)
        print('readTabs({}) fileSize {:,} bytes, reading first {:,} bytes:\'\n{}\''.format(rowStr, fileSize, readSize, ''.join([chr(data[p]) for p in range(0, readSize)])), file=Tabs.DBG_FILE)
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
                    if dbg: print('readTabs({}) detected fragment, len={} \'{}\' ii={}, p1={}, p2={}, i={}, bgn={}'.format(rowStr, len(fragment), ''.join([chr(fragment[p]) for p in range(0, len(fragment))]), ii, p1, p2, i, bgn), file=Tabs.DBG_FILE)
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
                                print('readTabs() s1={} & s2={} matched harmonic tab style r={}, c={}, {}'.format(s1, s2, (int(rowStr) - self.ROW_OFF) % self.numStrings, int(col) - self.COL_OFF, len(self.htabs)), file=Tabs.DBG_FILE)
                                htmp.append(ord('1'))
                            else:
                                htmp.append(ord('0'))
                    z1 = data.find(ord('<'), bgn, p1)
                    z2 = data.find(ord('>'), z1, p1)
                    if z1 != -1 and z2 != -1 and data[z1+1:z2] == b'BGN_TABS_SECTION':
                        bgnTabs = data[z1+1:z2]
                        print('readTabs() found {} mark at z1,z2={},{}'.format(bgnTabs, z1, z2), file=Tabs.DBG_FILE)
                        z = data.find(ord('c'), bgn, z1)
                        if z != -1:
                            zName = ''.join([chr(data[p]) for p in range(z, z+len('capo'))])
                            zLen = len(zName)
                            print('readTabs() found name={} at z={} with len={}!'.format(zName, z, zLen), file=Tabs.DBG_FILE)
                            if zName == 'capo' and chr(data[z+zLen]) == '=':
                                z += zLen + 1
                                self.capo = ord(data[z:z+1])
                                print('readTabs() parsing capo, raw value={}, setting capo={}'.format(data[z:z+1], self.capo), file=Tabs.DBG_FILE)
                    if bgnTabs:
                        tab = chr(data[i+1])
                        tmp.append(data[i+1])
                        if Tabs.isFret(tab):
                            tabFN = self.getFretNum(ord(tab))
                            maxFN = self.getFretNum(self.maxFret)
                            if tabFN > maxFN: 
                                self.maxFret = ord(tab)
                                print('readTabs() updating chr(mf)={}, maxFret={}, maxFN={}, tabFN={}'.format(chr(self.maxFret), self.maxFret, self.getFretNum(self.maxFret), tabFN), file=Tabs.DBG_FILE)
                        if hasFrag:
                            print('readTabs({}) {} {} [{},{}], ii={}, p1={}, p2={}, i={}, bgn={} {} \'{}\' data=\'{}\' tmp=\'{}\''.format(rowStr, cnt, len(fragment), row, col, ii, p1, p2, i, bgn, hasFrag, tab, ''.join([chr(data[p]) for p in range(ii, i+2)]), ''.join([chr(tmp[p]) for p in range(0, len(tmp))])), file=Tabs.DBG_FILE)
                            hasFrag = False
                        elif dbg:
                            print('readTabs({}) {} {} [{},{}], ii={}, p1={}, p2={}, i={}, bgn={} {} \'{}\' data=\'{}\' tmp=\'{}\''.format(rowStr, cnt, len(fragment), row, col, ii, p1, p2, i, bgn, hasFrag, tab, ''.join([chr(data[p]) for p in range(ii+2, i+2)]), ''.join([chr(tmp[p]) for p in range(0, len(tmp))])), file=Tabs.DBG_FILE)
                        z1 = data.find(ord('<'), bgn, p1)
                        z2 = data.find(ord('>'), z1, p1)
                        if z1 != -1 and z2 != -1 and data[z1+1:z2] == b'END_TABS_SECTION':
                            endTabs = data[z1+1:z2]
                            print('readTabs() found {} mark at z1,z2={},{}'.format(endTabs, z1, z2), file=Tabs.DBG_FILE)
                            break
                        elif self.numTabsPerStringPerLine == 0 and int(row) == self.ROW_OFF + 1:
                            self.numTabsPerStringPerLine = cnt - self.COL_OFF
                            self.numTabsPerString = self.numLines * self.numTabsPerStringPerLine
                            tmp, htmp, rowStr = self.appendTabs(tmp, htmp, rowStr)
                            tmp.append(data[i + 1])
                            if dbg: print('readTabs({}) {} [{},{}] \'{}\' setting numTabsPerStringPerLine={} tmp=\'{}\''.format(rowStr, cnt, row, col, tab, self.numTabsPerStringPerLine, ''.join([chr(tmp[p]) for p in range(0, len(tmp))])), file=Tabs.DBG_FILE)
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
                print('readTabs() No more data to read from inFile, fragment: \'{}\''.format(''.join([chr(fragment[p]) for p in range(0, len(fragment))])), file=Tabs.DBG_FILE)
                break
            data = fragment + data
            if dbg: print('readTabs() bytes read {:,}, reading next {:,} bytes and appending to fragment of len {} bytes ({:,} bytes):\n{}'.format(bytesRead, dataLen, len(fragment), dataLen + len(fragment), ''.join([chr(data[p]) for p in range(0, len(data))])), file=Tabs.DBG_FILE)
        print('readTabs() numStrings:{} =?= len(tabs):{}, numTabsPerString:{} =?= numLines:{} * numTabsPerStringPerLine:{}, totTabs:{}'.format(
            self.numStrings, len(self.tabs), self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, len(self.tabs) * len(self.tabs[0])), file=Tabs.DBG_FILE)
        self.dumpTabs('readTabs()')
        self.dumpTabs('readTabs(h)', h=1)
    
    def appendTabs(self, tmp, htmp, rowStr):
        rowStr = '{}'.format(int(rowStr) + 1)
        stringStr = '{}'.format(int(rowStr) - self.ROW_OFF)
        tabDataRow = tmp[self.COL_OFF-1 : self.COL_OFF-1 + self.numTabsPerStringPerLine]
        htabDataRow = htmp[self.COL_OFF-1 : self.COL_OFF-1 + self.numTabsPerStringPerLine]
        self.tabCount += len(tabDataRow)
        print('appendTabs({}) [{}, {}, {}, {}, {}] checking     \'{}\''.format(rowStr, self.numTabsPerStringPerLine, self.numLines, stringStr, self.numTabsPerString, self.tabCount, ''.join([chr(t) for t in tabDataRow])), file=Tabs.DBG_FILE)
        if self.tabCount > self.numStrings * self.numTabsPerStringPerLine:
            if ((self.tabCount - self.numTabsPerStringPerLine) % (self.numStrings * self.numTabsPerStringPerLine)) == 0:
                self.appendLine(pt=0)
            if int(rowStr) - (self.numLines - 1) * self.numStrings - self.ROW_OFF <= self.numStrings:
                r = (int(rowStr) - self.ROW_OFF - 1) % self.numStrings
                for c in range(0, len(tabDataRow)):
                    self.tabs[r][c + (self.numLines - 1) * self.numTabsPerStringPerLine] = tabDataRow[c]
                    self.htabs[r][c + (self.numLines - 1) * self.numTabsPerStringPerLine] = ord('0')
                print('appendTabs({}) [{}, {}, {}, {}, {}] appending[{}] \'{}\''.format(rowStr, self.numTabsPerStringPerLine, self.numLines, stringStr, self.numTabsPerString, self.tabCount, r, ''.join([chr(t) for t in tabDataRow])), file=Tabs.DBG_FILE)
        else:
            self.tabs.append(tabDataRow)
            self.htabs.append(htabDataRow)
            print('appendTabs({}) [{}, {}, {}, {}, {}] appending[ ] \'{}\''.format(rowStr, self.numTabsPerStringPerLine, self.numLines, stringStr, self.numTabsPerString, self.tabCount, ''.join([chr(t) for t in tabDataRow])), file=Tabs.DBG_FILE)
        tmp, htmp = [], []
        return [tmp, htmp, rowStr]
    
    def appendLine(self, pt=1):
        '''Append another line of tabs to the display.'''
        tabs, htabs = [], []
        print('appendLine(old) numTabsPerString:{} = numLines:{} * numTabsPerStringPerLine:{}, numTabs:{} = numStrings:{} * len(tabs[0]):{}'.format(self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.numTabs, self.numStrings, len(self.tabs[0])), file=Tabs.DBG_FILE)
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
        print('appendLine(new) numTabsPerString:{} = numLines:{} * numTabsPerStringPerLine:{}, numTabs:{} = numStrings:{} * len(tabs[0]):{}'.format(self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.numTabs, self.numStrings, len(self.tabs[0])), file=Tabs.DBG_FILE)
        if pt:
            self.printTabs()
    
    def removeLine(self):
        '''Remove last line of tabs from the display.'''
        tabs, htabs = [], []
        print('removeLine(old) numTabsPerString:{} = numLines:{} * numTabsPerStringPerLine:{}, numTabs:{} = numStrings:{} * len(tabs[0]):{}'.format(self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.numTabs, self.numStrings, len(self.tabs[0])), file=Tabs.DBG_FILE)
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
        print('removeLine(new) numTabsPerString:{} = numLines:{} * numTabsPerStringPerLine:{}, numTabs:{} = numStrings:{} * len(tabs[0]):{}'.format(self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.numTabs, self.numStrings, len(self.tabs[0])), file=Tabs.DBG_FILE)
        self.printTabs(cs=1)
    
    def quit(self, reason, code=0):
#        print('lastRow={}'.format(self.lastRow), file=Tabs.DBG_FILE)
        '''Quit with reason and exit code.'''
        self.printLineInfo('quit(ExitCode={}, reason=\'{}\')'.format(code, reason))
        print(self.CSI + self.styles['CONS'] + self.CSI + '{};{}HExitCode={}, reason=\'{}\''.format(self.lastRow + 1, 1, code, reason))
#        Tabs.DBG_FILE.flush()
#        os.fsync(Tabs.DBG_FILE)
        Tabs.DBG_FILE.close()
        exit(code)
    
    def printHelpInfo(self, ui=1):
        '''Print help info.  If ui: explicitly call printTabs(), else: assume printTabs() will be called by the invoker.  [cmd line opt -h]'''
        self.printHelpSummary()
        self.printHelpUiCmds()
        print('{}'.format('Press any key to continue... (Note some of the help text may have scrolled off the screen, you should be able to scroll back to view it.)'))
        b = ord(getwch())
        if ui:
            self.printTabs(cs=1)
    
    def printHelpUiCmds(self):
        print('{:>20} : {}'.format('User Interactive Cmd', 'Description'))
        print('{:>20} : {}'.format('User Interactive Cmd', 'Description'), file=Tabs.DBG_FILE)
        print('--------------------------------------------------------------------------------')
        print('--------------------------------------------------------------------------------', file=Tabs.DBG_FILE)
        for k in self.uiKeys:
            print('{:>20} : {}'.format(k, self.uiCmds[k].__doc__))
            print('{:>20} : {}'.format(k, self.uiCmds[k].__doc__), file=Tabs.DBG_FILE)
    
    def registerUiCmds(self):
        self.uiCmds = {}
        self.uiKeys = []
        self.registerUiCmd('Tablature',           self.setTab)
        self.registerUiCmd('Ctrl A',              self.toggleDisplayLabels)
        self.registerUiCmd('Shift A',             self.analyzeChord)
        self.registerUiCmd('Ctrl B',              self.toggleDisplayChords)
        self.registerUiCmd('Shift B',             self.copySelectTabs)
        self.registerUiCmd('Ctrl C',              self.copySelectTabs)
        self.registerUiCmd('Shift C',             self.copySelectTabs)
        self.registerUiCmd('Ctrl D',              self.deleteSelectTabs)
        self.registerUiCmd('Ctrl E',              self.eraseTabs)
        self.registerUiCmd('Ctrl F',              self.toggleEnharmonic)
        self.registerUiCmd('Ctrl G',              self.goTo)
        self.registerUiCmd('Ctrl H or Backspace', self.deletePrevTab)
        self.registerUiCmd('Shift H',             self.printHelpInfo)
        self.registerUiCmd('Ctrl I or Tab',       self.toggleCursorDir)
        self.registerUiCmd('Ctrl J',              self.shiftSelectTabs)
        self.registerUiCmd('Ctrl K',              self.printChord)
        self.registerUiCmd('Shift K',             self.setCapo)
        self.registerUiCmd('Ctrl L',              self.goToLastTab)
        self.registerUiCmd('Shift L',             self.goToLastTab)
        self.registerUiCmd('Ctrl M or Enter',     self.toggleCursorMode)
        self.registerUiCmd('Ctrl N',              self.toggleDisplayNotes)
        self.registerUiCmd('Ctrl O',              self.toggleDisplayIntervals)
        self.registerUiCmd('Ctrl P',              self.printTabs)
        self.registerUiCmd('Ctrl Q',              self.quit)
        self.registerUiCmd('Shift Q',             self.selectChord)
        self.registerUiCmd('Ctrl R',              self.resetTabs)
        self.registerUiCmd('Ctrl S',              self.saveTabs)
        self.registerUiCmd('Ctrl T',              self.appendLine)
        self.registerUiCmd('Shift T',             self.removeLine)
        self.registerUiCmd('Ctrl U',              self.unselectAll)
        self.registerUiCmd('Ctrl V',              self.pasteSelectTabs)
        self.registerUiCmd('Ctrl X',              self.cutSelectTabs)
        self.registerUiCmd('Shift X',             self.cutSelectTabs)
        self.registerUiCmd('Ctrl Z',              self.goToLastTab)
        self.registerUiCmd('Shift Z',             self.goToLastTab)
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
            b = ord(getwch())                                     # get wide char -> int
            if self.isTab(chr(b)): self.uiCmds['Tablature'](b)    # setTab()               # N/A
            elif b == 1:   self.uiCmds['Ctrl A']()                # toggleDisplayLabels()  # cmd line opt -a
            elif b == 65:  self.uiCmds['Shift A']()               # analyzeChord()         # N/A
            elif b == 2:   self.uiCmds['Ctrl B']()                # toggleDisplayChords()  # cmd line opt -b
            elif b == 66:  self.uiCmds['Shift B'](arpg=0)         # copySelectTabs()       # N/A
            elif b == 3:   self.uiCmds['Ctrl C']()                # copySelectTabs()       # N/A
            elif b == 67:  self.uiCmds['Shift C'](arpg=1)         # copySelectTabs()       # N/A
            elif b == 4:   self.uiCmds['Ctrl D']()                # deleteSelectTabs()     # N/A
            elif b == 5:   self.uiCmds['Ctrl E']()                # eraseTabs()            #?cmd line opt?
            elif b == 6:   self.uiCmds['Ctrl F']()                # toggleEnharmonic()     # cmd line opt -F?
            elif b == 7:   self.uiCmds['Ctrl G']()                # goTo()                 #?cmd line opt -g?
            elif b == 8:   self.uiCmds['Ctrl H or Backspace']()   # deletePrevTab()        # N/A
            elif b == 72:  self.uiCmds['Shift H']()               # printHelpInfo()        # cmd line opt -h
            elif b == 9:   self.uiCmds['Ctrl I or Tab']()         # toggleCursorDir()      # cmd line opt -i
            elif b == 10:  self.uiCmds['Ctrl J']()                # shiftSelectTabs()      # N/A
            elif b == 11:  self.uiCmds['Ctrl K'](dbg=1)           # printChord()           # N/A
            elif b == 75:  self.uiCmds['Shift K']()               # setCapo()              # cmd line opt -k?
            elif b == 12:  self.uiCmds['Ctrl L'](cs=1)            # goToLastTab()          # cmd line opt -l
            elif b == 76:  self.uiCmds['Shift L']()               # goToLastTab()          # cmd line opt -L
            elif b == 13:  self.uiCmds['Ctrl M or Enter']()       # toggleCursorMode()     # cmd line opt -m
            elif b == 14:  self.uiCmds['Ctrl N']()                # toggleDisplayNotes()   # cmd line opt -n
            elif b == 15:  self.uiCmds['Ctrl O']()                # toggleDisplayIntervals()   # cmd line opt -o
            elif b == 16:  self.uiCmds['Ctrl P']()                # printTabs()            # DBG?
            elif b == 17:  self.uiCmds['Ctrl Q'](self.QUIT_STR)   # quit()                 # DBG?
            elif b == 81:  self.uiCmds['Shift Q']()               # selectChord()          # N/A
            elif b == 18:  self.uiCmds['Ctrl R']()                # resetTabs()            # DBG?
            elif b == 19:  self.uiCmds['Ctrl S']()                # saveTabs()             # DBG?
            elif b == 20:  self.uiCmds['Ctrl T']()                # appendLine()           # DBG?
            elif b == 84:  self.uiCmds['Shift T']()               # removeLine()           # DBG?
            elif b == 21:  self.uiCmds['Ctrl U']()                # unselectAll()          # N/A
            elif b == 22:  self.uiCmds['Ctrl V']()                # pasteSelectTabs()      # N/A
            elif b == 24:  self.uiCmds['Ctrl X']()                # cutSelectTabs()        # N/A
            elif b == 88:  self.uiCmds['Shift X'](arpg=1)         # cutSelectTabs()        # N/A
            elif b == 26:  self.uiCmds['Ctrl Z'](ll=1, cs=1)      # goToLastTab()          # cmd line opt -z
            elif b == 90:  self.uiCmds['Shift Z'](ll=1)           # goToLastTab()          # cmd line opt -Z
            elif b == 27:  self.uiCmds['ESC']()                   # toggleHarmonicNote()   # N/A
            elif b == 32:  self.uiCmds['Space']()                 # moveCursor()           # N/A
            elif b == 155: self.uiCmds['Alt Arrow Left'](left=1)  # unselectCol()          # N/A
            elif b == 157: self.uiCmds['Alt Arrow Right']()       # unselectCol()          # N/A
            elif b == 152: self.uiCmds['Alt Arrow Up'](up=1)      # unselectRow()          # N/A
            elif b == 160: self.uiCmds['Alt Arrow Down']()        # unselectRow()          # N/A
#            elif b == 161: self.uiCmds['Alt Page Down']()         # movePageDown()         # N/A
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
        print('moveTo({}, {}, {}) row={}, col={}, line={}'.format(row, col, hi, self.row, self.col, self.row2Line(self.row)), file=Tabs.DBG_FILE)
        print(self.CSI + '{};{}H'.format(self.row, self.col), end='')
        self.printStatus()
        if self.displayLabels == self.DISPLAY_LABELS['ENABLED'] and hi == 1:
            self.hiliteRowColNum()
   
    def moveLeft(self, dbg=None):
        '''Move cursor left one column on current line, wrapping to end of row on previous line or last line.'''
        if dbg or self.dbgMove: print('moveLeft({}, {})'.format(self.row, self.col), file=Tabs.DBG_FILE)
        if self.col == self.bgnCol():
            line = self.row2Line(self.row)
            if line == 0: self.moveTo(row=self.row + self.lineDelta() * (self.numLines - 1), col=self.endCol(), hi=1)
            else:         self.moveTo(row=self.row - self.lineDelta(), col=self.endCol(), hi=1)
        else:             self.moveTo(col=self.col - 1, hi=1)
    
    def moveRight(self, dbg=None):
        '''Move cursor right one column on current line, wrapping to beginning of row on next line or first line.'''
        if dbg or self.dbgMove: print('moveRight({}, {})'.format(self.row, self.col), file=Tabs.DBG_FILE)
        if self.col == self.endCol():
            line = self.row2Line(self.row)
            if line == self.numLines - 1: self.moveTo(row=self.row - self.lineDelta() * (self.numLines - 1), col=self.bgnCol(), hi=1)
            else:                         self.moveTo(row=self.row + self.lineDelta(), col=self.bgnCol(), hi=1)
        else:                             self.moveTo(col=self.col + 1, hi=1)
    
    def moveUp(self, dbg=None):
        '''Move cursor up one row on current line, wrapping to last row on previous line or last line.'''
        if dbg or self.dbgMove: self.printLineInfo('moveUp({}, {})'.format(self.row, self.col))
        line = self.row2Line(self.row)
        if self.row == self.bgnRow(line):
            if line == 0: self.moveTo(row=self.endRow(self.numLines - 1), hi=1)
            else:         self.moveTo(row=self.endRow(line - 1), hi=1)
        else:             self.moveTo(row=self.row - 1, hi=1)
    
    def moveDown(self, dbg=None):
        '''Move cursor down one row on current line, wrapping to first row on next line or first line.'''
        if dbg or self.dbgMove: self.printLineInfo('moveDown({}, {})'.format(self.row, self.col))
        line = self.row2Line(self.row)
        if self.row == self.endRow(line):
            if line == self.numLines - 1: self.moveTo(row=self.bgnRow(0), hi=1)
            else:                         self.moveTo(row=self.bgnRow(line + 1), hi=1)
        else:                             self.moveTo(row=self.row + 1, hi=1)
    
    def moveHome(self, dbg=None):
        '''Move cursor to beginning of row on current line, wrapping to end of row on previous line or last line.'''
        if dbg or self.dbgMove: print('moveHome({}, {})'.format(self.row, self.col), file=Tabs.DBG_FILE)
        if self.col == self.bgnCol():
            line = self.row2Line(self.row)
            if line == 0: self.moveTo(row=self.row + self.lineDelta() * (self.numLines - 1), col=self.endCol(), hi=1)
            else:         self.moveTo(row=self.row - self.lineDelta(), col=self.endCol(), hi=1)
        else:             self.moveTo(col=self.bgnCol(), hi=1)
    
    def moveEnd(self, dbg=None):
        '''Move cursor to end of row on current line, wrapping to beginning of row on next line or first line.'''
        if dbg or self.dbgMove: print('moveEnd({}, {})'.format(self.row, self.col), file=Tabs.DBG_FILE)
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
    
    def testRow2Line(self):
        for row in range(-2, 76):
            row += self.ROW_OFF
            line = self.row2Line(row)
            print('row={} line={}'.format(row, line), file=Tabs.DBG_FILE)
    
    def row2Line(self, row):
        for line in range(0, self.numLines):
            if 0 < row < self.bgnRow(line + 1) - 1:
                return line
        self.printe('Range Error row={}'.format(row), x=0)
    
    def colIndex2Line(self, c):
        return int(c / self.numTabsPerStringPerLine)
    
    def rowCol2Indices(self, row, col):
        return self.row2Index(row), self.col2Index(col)
    
    def row2Index(self, row):
        return row - self.ROW_OFF - self.row2Line(row) * self.lineDelta()
    
    def col2Index(self, col):
        return col - self.COL_OFF + self.row2Line(self.row) * self.numTabsPerStringPerLine
    
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
        return self.numStrings + self.NOTES_LEN + self.INTERVALS_LEN + self.CHORDS_LEN + 1
    
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
                    self.prints(chr(self.capo), r + self.endRow(line) + 1, self.cursorModeCol, self.styles['NUT_DN'])
                elif self.cursorDir == self.CURSOR_DIRS['UP']:
                    self.prints(chr(self.capo), r + self.bgnRow(line), self.cursorModeCol, self.styles['NUT_UP'])
                    self.prints(chr(self.capo), r + self.endRow(line) + 1, self.cursorModeCol, self.styles['NUT_UP'])
        if dbg: self.printLineInfo('toggleCursorDir({}, {}, {}, {})'.format(self.row, self.col, self.cursorDir, self.CURSOR_DIRS[self.cursorDir]))
        self.resetPos()
    
    def toggleEnharmonic(self):
        '''Toggle display of enharmonic (sharp or flat) notes.  [cmd line opt -F]'''
        self.enharmonic = (self.enharmonic + 1) % len(self.ENHARMONICS)
        self.printTabs()
        self.printStatus()
    
    def toggleDisplayLabels(self, pt=1):
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
        if pt: self.printTabs(cs=1)
    
    def toggleDisplayNotes(self, pt=1):
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
        if pt: self.printTabs(cs=1)
    
    def toggleDisplayIntervals(self, pt=1):
        '''Toggle (enable or disable) display of intervals section.  [cmd line opt -o]'''
        self.displayIntervals = (self.displayIntervals + 1) % len(self.DISPLAY_INTERVALS)
        line = self.row2Line(self.row)
        self.printLineInfo('toggleDisplayIntervals({} {}) row,col=({}, {}), line={} bgn'.format(self.displayIntervals, pt, self.row, self.col, line))
        if self.displayIntervals == self.DISPLAY_INTERVALS['ENABLED']:
            self.INTERVALS_LEN = self.numStrings
            self.row += line * self.INTERVALS_LEN
        elif self.displayIntervals == self.DISPLAY_INTERVALS['DISABLED']:
            self.row -= line * self.INTERVALS_LEN
            self.INTERVALS_LEN = 0
        self.setLastRow()
        self.printLineInfo('toggleDisplayIntervals({} {}) row,col=({}, {}), line={} end'.format(self.displayIntervals, pt, self.row, self.col, line))
        if pt: self.printTabs(cs=1)
    
    def toggleDisplayChords(self, pt=1):
        '''Toggle (enable or disable) display of chords section.  [cmd line opt -b]'''
        self.displayChords = (self.displayChords + 1) % len(self.DISPLAY_CHORDS)
        line = self.row2Line(self.row)
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            if self.chordsObj is None:
                self.chordsObj = chords.Chords(self)
                print('toggleDisplayChords() loaded chords module and Chords class, chordsObj={}, getChordName={}'.format(self.chordsObj, self.chordsObj.getChordName), file=Tabs.DBG_FILE)
            self.CHORDS_LEN = 5
            self.row += line * self.CHORDS_LEN
        elif self.displayChords == self.DISPLAY_CHORDS['DISABLED']:
            self.row -= line * self.CHORDS_LEN
            self.CHORDS_LEN = 0
        self.setLastRow()
        self.printLineInfo('toggleDisplayChords({}) row,col=({}, {}), line={}'.format(self.displayChords, self.row, self.col, line))
        if pt: self.printTabs(cs=1)
    
    def printCursorAndEditModes(self, r):
        print('printCursorAndEditModes()'.format(), file=Tabs.DBG_FILE)
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
        print('printColNums({})'.format(row), file=Tabs.DBG_FILE)
        for c in range(0, self.numTabsPerStringPerLine):
            self.printColNum(row, c + 1, self.styles['NORMAL'])
    
    def printColNum(self, row, c, style):
        '''Print 1 based tab col index, c, as a single decimal digit.'''
        '''123456789112345678921234567893123456789412345678951234567896123456789712345678981234567899123456789012345678911234567892123456789312345678941234567895'''
        if c % 10: style += self.styles['MIN_COL_NUM']
        else:      style += self.styles['MAJ_COL_NUM']
        self.prints('{}'.format(Tabs.getColMod(c)), row, c + self.COL_OFF - 1, style)
    
    @staticmethod
    def getColMod(c):
        if c % 10:    return c % 10
        elif c < 100: return c // 10
        else:         return ((c - 100) // 10)
    
    def selectRow(self, up=0):
        '''Select row, append to selected rows list, hilite current tab, and advance (up or down) to next tab.'''
        row, col, r, c, br, er = self.row, self.col, self.row2Index(self.row), self.col2Index(self.col), self.bgnRow(self.row2Line(self.row)), self.endRow(self.row2Line(self.row))
        print('selectRow(up={}) ({},{}) bgn r={}, c={}, selectRows={}, selectCols={}, br={}, er={}'.format(up, row, col, r, c, self.selectRows, self.selectCols, br, er), file=Tabs.DBG_FILE)
        if len(self.selectRows) < self.numStrings:
            self.selectRows.append(r)
            self.selectCols.append(c)
            print('selectRow(up={}) ({},{}) after appending r={}, c={}, selectRows={}, selectCols={}'.format(up, row, col, r, c, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
            self.selectStyle(c, self.styles['BRIGHT'], rList=self.selectRows)
        if up == 1 and row == br or up == 0 and row == er:
            if up: dir, pos = 'up', 'bgn'
            else:  dir, pos = 'down', 'end'
            print('selectRow(up={}) ignoring cursor movement, because dir={} and row={} == {}Row'.format(up, dir, row, pos), file=Tabs.DBG_FILE)
            self.resetPos()
            return
        if up: self.moveUp()
        else:  self.moveDown()
    
    def unselectRow(self, up=0):
        '''Unselect row, remove it from selected rows list, un-hilite the current tab, and advance (up or down) to the next tab.'''
        if len(self.selectRows):
            r = self.row2Index(self.row)
            c = self.col2Index(self.col)
            print('unselectRow(up={}) ({},{}) checking if r={}, c={}, in selectRows={}, selectCols={}'.format(up, self.row, self.col, r, c, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
            if r in self.selectRows:
                print('unselectRow(up={}) ({},{}) before removing r={}, c={}, from selectRows={}, selectCols={}'.format(up, self.row, self.col, r, c, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
                self.selectRows.remove(r)
                print('unselectRow(up={}) ({},{}) after removing r={}, c={}, from selectRows={}, selectCols={}'.format(up, self.row, self.col, r, c, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
                self.selectStyle(c, self.styles['NORMAL'], r=r)
                if up: self.moveUp()
                else:  self.moveDown()
            else: print('unselectRow(up={}) ({},{}) nothing to unselect, r={} not in selectRows={}, selectCols={}'.format(up, self.row, self.col, r, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
        else: print('unselectRow(up={}) ({},{}) empty list, nothing to unselect, r={} selectRows={}, selectCols={}'.format(up, self.row, self.col, r, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
    
    def selectCol(self, left=0):
        '''Select column, append to selected columns list, hilite current tab, and advance (left or right) to next tab.'''
        cc = self.col2Index(self.col)
        print('selectCol(left={}) ({},{}), cc={} selectFlag={}, selectRows={}, selectCols={}'.format(left, self.row, self.col, cc, self.selectFlag, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
        if len(self.selectRows) == 0:
            self.selectFlag = 1
            for r in range(0, self.numStrings):
                self.selectRows.append(r)
            print('selectCol(left={}) ({},{}) appended all rows, cc={}, selectFlag={}, selectRows={}, selectCols={}'.format(left, self.row, self.col, cc, self.selectFlag, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
        elif self.selectFlag == 0:
            self.selectFlag = 1
            for c in range(0, len(self.selectCols)):
                self.selectStyle(c, self.styles['NORMAL'], rList=self.selectRows)
            self.selectCols = []
            print('selectCol(left={}) ({},{}) removed all cols, cc={}, selectFlag={}, selectRows={}, selectCols={}'.format(left, self.row, self.col, cc, self.selectFlag, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
        self.selectCols.append(cc)
        print('selectCol(left={}) ({},{}) appended cc={}, selectFlag={}, selectRows={}, selectCols={}'.format(left, self.row, self.col, cc, self.selectFlag, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
        self.selectStyle(cc, self.styles['BRIGHT'], rList=self.selectRows)
        if left: self.moveLeft()
        else:    self.moveRight()
    
    def unselectCol(self, left=0):
        '''Unselect column, remove it from selected columns list, un-hilite the current tab, and advance (left or right) to the next tab.'''
        if len(self.selectCols):
            c = self.col2Index(self.col)
            print('unselectCol(left={}) ({},{}) checking if c={} in selectCols={}'.format(left, self.row, self.col, c, self.selectCols), file=Tabs.DBG_FILE)
            if c in self.selectCols:
                print('unselectCol(left={}) ({},{}) before removing c={} from selectCols={}'.format(left, self.row, self.col, c, self.selectCols), file=Tabs.DBG_FILE)
                self.selectCols.remove(c)
                print('unselectCol(left={}) ({},{}) after removing c={} from selectCols={}'.format(left, self.row, self.col, c, self.selectCols), file=Tabs.DBG_FILE)
                self.selectStyle(c, self.styles['NORMAL'], rList=self.selectRows)
                if left: self.moveLeft()
                else:    self.moveRight()
            else: print('unselectCol(left={}) ({},{}) c={} not in selectCols={}, nothing to unselect'.format(left, self.row, self.col, c, self.selectCols), file=Tabs.DBG_FILE)
        else: print('unselectCol(left={}) ({},{}) selectCols={}, empty list, nothing to unselect'.format(left, self.row, self.col, self.selectCols), file=Tabs.DBG_FILE)
    
    def unselectAll(self):
        '''Unselect all rows and columns.'''
        print('unselectAll({},{}) bgn selectFlag={}, selectRows={}, selectCols={}, selectTabs={}'.format(self.row, self.col, self.selectFlag, self.selectRows, self.selectCols, self.selectTabs), file=Tabs.DBG_FILE)
        for c in range(0, len(self.selectCols)):
            self.selectStyle(self.selectCols[c], self.styles['NORMAL'], rList=self.selectRows)
        self.selectRows, self.selectCols, self.selectTabs, self.selectHTabs, self.selectFlag = [], [], [], [], 0
        self.resetPos()
        print('unselectAll({},{}) end selectFlag={}, selectRows={}, selectCols={}, selectTabs={}'.format(self.row, self.col, self.selectFlag, self.selectRows, self.selectCols, self.selectTabs), file=Tabs.DBG_FILE)
    
    def selectStyle(self, c, style, rList=None, r=None):
        print('selectStyle({}) c={}, rList={}, r={}'.format(style, c, rList, r), file=Tabs.DBG_FILE)
        if rList is not None and r is None:
            for rr in range(0, len(rList)):
                r = rList[rr]
                self.selectRowStyle(r, c, style)
        elif rList is None and r is not None:
            self.selectRowStyle(r, c, style)
    
    def selectRowStyle(self, r, c, style):
        tab = self.tabs[r][c]
        row, col = self.indices2RowCol(r, c)
        print('selectRowStyle({}) r={}, c={}, row={}, col={}, tabc={}'.format(style, r, c, row, col, chr(tab)), file=Tabs.DBG_FILE)
        if self.htabs[r][c] == ord('1'):
            self.prints(chr(tab), row, col, style + self.styles['H_TABS'])
        else:
            self.prints(chr(tab), row, col, style + self.styles['TABS'])
        if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
            if Tabs.isFret(chr(tab)):
                if self.htabs[r][c] == ord('1'):
                    n = self.getHarmonicNote(r + 1, tab)
                    self.printNote(row + self.numStrings, col, n, style, hn=1)
                else:
                    n = self.getNote(r + 1, tab)
                    self.printNote(row + self.numStrings, col, n, style)
            else:
                self.prints(chr(tab), row + self.numStrings, col, style + self.styles['NAT_NOTE'])
    
    def toggleHarmonicNote(self):
        '''Toggle between normal and harmonic note.  Modify note modeling the closest natural harmonic note in the tab fret number.'''
        line = self.row2Line(self.row)
        r, c = self.rowCol2Indices(self.row, self.col)
        tab = self.tabs[r][c]
        if self.htabs[r][c] == ord('0'):
            if Tabs.isFret(chr(tab)) and self.getFretNum(tab) in self.HARMONIC_FRETS:
                self.htabs[r][c] = ord('1')
                n = self.getHarmonicNote(r + 1, tab)
                self.prints(chr(tab), self.row, self.col, self.styles['H_TABS'])
                if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                    self.printNote(r + line * self.lineDelta() + self.endRow(0) + 1 , self.col, n, hn=1)
                    self.resetPos()
                pn = self.getNote(r + 1, tab)
                print('toggleHarmonicNote({},{}) r,c={},{}, tabc={}, pn.n={}, pn.i={} norm->harm n.n={}, n.i={}'.format(self.row, self.col, r, c, chr(tab), pn.name, pn.index, n.name, n.index), file=Tabs.DBG_FILE)
        else:
            self.htabs[r][c] = ord('0')
            n = self.getNote(r + 1, tab)
            self.prints(chr(tab), self.row, self.col, self.styles['TABS'])
            if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                self.printNote(r + line * self.lineDelta() + self.endRow(0) + 1 , self.col, n)
                self.resetPos()
            pn = self.getHarmonicNote(r + 1, tab)
            print('toggleHarmonicNote({},{}) r,c={},{}, tabc={}, pn.n={}, pn.i={} harm->norm n.n={}, n.i={}'.format(self.row, self.col, r, c, chr(tab), pn.name, pn.index, n.name, n.index), file=Tabs.DBG_FILE)
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.chordsObj.eraseChord(c)
            self.chordsObj.printChord(c=c)
        self.printStatus()
    
    def setCapo(self, c=None):
        '''Model a capo placed at fret position specified by user input of a single character, [0-9] [a-o].  [cmd line opt -k]'''
        if c is None: c = getwch()
        print('setCapo({}, {}) c={}, ord(c)={}, prevCapo={} bgn: check isFret(c)'.format(self.row, self.col, c, ord(c), self.capo), file=Tabs.DBG_FILE)
        if Tabs.isFret(c):
            capFN = self.getFretNum(ord(c))
            maxFN = self.getFretNum(self.maxFret)
            print('setCapo() c={}, ord(c)={}, chr(mf)={}, maxFret={}, check capFN:{} + maxFN:{} <= {}?'.format(c, ord(c), chr(self.maxFret), self.maxFret, capFN, maxFN, self.NUM_FRETS), file=Tabs.DBG_FILE)
            if capFN + maxFN > self.NUM_FRETS:
                info = 'setCapo() capFN:{} + maxFN:{} > {}!  c={}, ord(c)={}, capo={}, chr(mf)={}, maxFret={}'.format(capFN, maxFN, self.NUM_FRETS, c, ord(c), self.capo, chr(self.maxFret), self.maxFret)
                self.printe(info)
            else:
                self.capo = ord(c)            
                print('setCapo() c={}, ord(c)={}, capo={}, capFN={}, chr(mf)={}, maxFret={}, maxFN={} setting capo'.format(c, ord(c), self.capo, capFN, chr(self.maxFret), self.maxFret, maxFN), file=Tabs.DBG_FILE)
                self.printTabs()
    
    def findMaxFret(self):
        maxFN = 0
        for r in range(0, len(self.tabs)):
            for c in range(0, len(self.tabs[r])):
                tab = self.tabs[r][c]
                if Tabs.isFret(chr(tab)):
                    currFN = self.getFretNum(tab)
                    if currFN > maxFN:
                        maxFN = currFN
        print('findMaxFret() maxFN={}'.format(maxFN), file=Tabs.DBG_FILE)
        return self.getFretByte(maxFN)
    
    def setTab(self, tab, dbg=0):
        '''Set given tab byte at the current row and col, print the corresponding tab character and then move cursor according to the cursor mode.'''
        row, col = self.row, self.col
        rr, cc = self.rowCol2Indices(row, col)
        s, ss = rr + 1, self.getOrdSfx(rr + 1)
        print('setTab({}, {}, {}, {}) tab={}({}), {}({}{}) string, bgn'.format(rr, cc, self.row, self.col, tab, chr(tab), self.getNote(s, 0).name, s, ss), file=Tabs.DBG_FILE)
        if self.bgnCol() > self.col > self.endCol() or self.ROW_OFF > self.row > self.ROW_OFF + self.numLines * self.lineDelta():
            return self.printe('row/col out of range setTab({},{},{}, {}) tab={}({})'.format(rr, cc, self.row, self.col, tab, chr(tab)))
        if self.editMode == self.EDIT_MODES['INSERT']:
            for c in range(len(self.tabs[rr]) - 1, cc, - 1):
                self.tabs[rr][c] = self.tabs[rr][c - 1]
                self.htabs[rr][c] = self.htabs[rr][c - 1]
        prevTab = self.tabs[rr][cc]
        capTab = self.tabs[rr][cc] = tab
        if dbg: print('setTab({}({})) tabs={}({}) htabs={}({}) check isFret()'.format(tab, chr(tab), self.tabs[rr][cc], chr(self.tabs[rr][cc]), self.htabs[rr][cc], chr(self.htabs[rr][cc])), file=Tabs.DBG_FILE)
        if Tabs.isFret(chr(tab)):
            tabFN = self.getFretNum(tab)
            maxFN = self.getFretNum(self.maxFret)
            capFN = self.getFretNum(self.capo)
            if dbg: print('setTab() maxFN={}({}) check tabFN:{}({}) + capFN:{}({}) > {}?'.format(self.maxFret, maxFN, tab, tabFN, self.capo, capFN, self.NUM_FRETS), file=Tabs.DBG_FILE)
            if tabFN + capFN > self.NUM_FRETS:
                return self.printe('setTab() capFN:{} + tabFN:{} > {}! tabc={}, tab={}, chr(capo)={}, capo={}'.format(capFN, tabFN, self.NUM_FRETS, chr(tab), tab, chr(self.capo), self.capo))
            if dbg: print('setTab() check tabFn:{} > maxFn:{}?'.format(tabFN, maxFN), file=Tabs.DBG_FILE)
            if tabFN > maxFN: 
                self.maxFret = tab
                if dbg: print('setTab() updating maxFret: chr(mf)={}, maxFret={}, maxFN={}'.format(chr(self.maxFret), self.maxFret, self.getFretNum(self.maxFret)), file=Tabs.DBG_FILE)
            capTab = self.getFretByte(tabFN + capFN)
            if dbg: print('setTab() setting capTab:{}({}) = self.getFretByte(tabFN:{}({}) + capFN:{}({}))'.format(capTab, chr(capTab), tab, tabFN, self.capo, capFN), file=Tabs.DBG_FILE)
        if self.editMode == self.EDIT_MODES['INSERT']:
            self.printTabs()
        elif self.editMode == self.EDIT_MODES['REPLACE']:
            self.prints(chr(capTab), row, col, self.styles['TABS'])
            if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                if Tabs.isFret(chr(capTab)):
                    n = self.getNote(s, capTab)
                    print('setTab(DISPLAY_NOTES) capTab={}({}) nn={}'.format(capTab, chr(capTab), n.name), file=Tabs.DBG_FILE)
                    self.printNote(row + self.numStrings, col, n)
                else:
                    self.prints(chr(capTab), row + self.numStrings, col, self.styles['NAT_NOTE'])
            if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
                self.chordsObj.eraseChord(cc)
                if cc in self.chordInfo: 
                    if dbg: print('setTab(DISPLAY_CHORDS) chordInfo[{}]={}'.format(cc, self.chordInfo[cc]), file=Tabs.DBG_FILE)
                noteCount = 0
                for r in range(0, self.numStrings):
                    if Tabs.isFret(chr(self.tabs[r][cc])):
                        if dbg: self.printMapLimap(self.chordInfo, reason='setTab(DISPLAY_CHORDS) r={} cc={}'.format(r, cc))
                        noteCount += 1
                        if noteCount > 1:
                            print('setTab(DISPLAY_CHORDS) r={}, increment noteCount={}'.format(r, noteCount), file=Tabs.DBG_FILE)
                            self.chordsObj.printChord(c=cc)
                            break
                        else: 
                            print('setTab(DISPLAY_CHORDS) r={}, noteCount={}'.format(r, noteCount), file=Tabs.DBG_FILE)
            if self.displayIntervals == self.DISPLAY_INTERVALS['ENABLED']:
                irow = self.indices2Row(self.lineDelta() * self.colIndex2Line(cc) + self.numStrings + self.NOTES_LEN, col)
                for r in range(self.numStrings):
                    self.printInterval(irow + r, col, '-', dbg=0)
                if dbg: self.printMapLimap(self.chordInfo, reason='setTab(DISPLAY_INTERVALS) irow={} line={} cc={}'.format(irow, self.colIndex2Line(cc), cc))
                if cc not in self.chordInfo:
                    print('setTab(DISPLAY_INTERVALS) row={} col={} ival={}'.format(row, col, 'R'), file=Tabs.DBG_FILE)
                    if Tabs.isFret(chr(capTab)):
                        self.printInterval(row + self.numStrings + self.numStrings, col, 'R', dbg=0)
                    else: print('setTab(DISPLAY_INTERVALS) NOT a Fret tab={}'.format(chr(capTab)), file=Tabs.DBG_FILE)
                else:
                    for r in range(self.numStrings):
                        self.wrapPrintInterval(r, cc, dbg=dbg)
        self.moveCursor()
        self.dumpTabs('setTab() end')
    
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
        print('goToLastTab({}, {}) cs={}, ll={}, rowBng={}, rowEnd={}, lineBgn={}, lineEnd={}'.format(self.row, self.col, cs, ll, rowBgn, rowEnd, lineBgn, lineEnd), file=Tabs.DBG_FILE)
        for line in range(lineBgn, lineEnd, -1):
            for r in range(rowBgn, rowEnd):
                for c in range(line * self.numTabsPerStringPerLine - 1, (line - 1) * self.numTabsPerStringPerLine - 1, -1):
                    t = chr(self.tabs[r][c])
                    if t != '-' and self.isTab(t):
                        if c > cc:
                            rr, cc, ll = r, c, line
                            print('goToLastTab(updating col) t={}, line={}, r={}, c={}'.format(t, line, r, c), file=Tabs.DBG_FILE)
                        break
        if cc > 0:
            row, col = self.indices2RowCol(rr, cc)
            print('goToLastTab() row,col=({},{})'.format(row, col), file=Tabs.DBG_FILE)
            self.moveTo(row=row, col=col, hi=1)
    
    def moveCursor(self, row=None, col=None, back=0):
        '''Move cursor to the next row and or col using cursor mode (optionally hilite new row and col nums).'''
        print('moveCursor(row={}, col={}, back={}) old: row={}, col={}'.format(row, col, back, self.row, self.col), file=Tabs.DBG_FILE)
        if row != None: self.row = row
        if col != None: self.col = col
        if self.cursorMode == self.CURSOR_MODES['MELODY']:
            if back: self.moveLeft()
            else:    self.moveRight()
        elif self.cursorMode == self.CURSOR_MODES['CHORD'] or self.cursorMode == self.CURSOR_MODES['ARPEGGIO']:
            if self.cursorMode == self.CURSOR_MODES['ARPEGGIO']:
                self.moveRight()
            line = self.row2Line(self.row)
            if self.cursorDir == self.CURSOR_DIRS['DOWN']:
                if back:
                    if self.row > self.bgnRow(line):
                        self.moveUp()
                    else:
                        print('moveCursor(line={} DOWN !<) row={} ? endRow(line)={}'.format(line, self.row, self.endRow(line)), file=Tabs.DBG_FILE)
                        self.row = self.endRow(line)
                        self.moveLeft()
                else:
                    if self.row < self.endRow(line):
                        print('moveCursor(line={} DOWN <) row={} ? endRow(line)={}'.format(line, self.row, self.endRow(line)), file=Tabs.DBG_FILE)
                        self.moveDown()
                    else:
                        print('moveCursor(line={} DOWN !<) row={} ? endRow(line)={} bgnRow={}'.format(line, self.row, self.endRow(line), self.bgnRow(line)), file=Tabs.DBG_FILE)
                        self.row = self.bgnRow(line)
                        self.moveRight()
            elif self.cursorDir == self.CURSOR_DIRS['UP']:
                if back:
                    if self.row < self.endRow(line):
                        self.moveDown()
                    else:
                        print('moveCursor(line={} UP !>) row={} ? bgnRow(line)={}'.format(line, self.row, self.bgnRow(line)), file=Tabs.DBG_FILE)
                        self.row = self.bgnRow(line)
                        self.moveLeft()
                else:
                    if self.row > self.bgnRow(line):
                        print('moveCursor(line={} UP >) row={} ? bgnRow(line)={}'.format(line, self.row, self.bgnRow(line)), file=Tabs.DBG_FILE)
                        self.moveUp()
                    else:
                        print('moveCursor(line={} UP !>) row={} ? bgnRow(line)={} endRow(line)={}'.format(line, self.row, self.bgnRow(line), self.endRow(line)), file=Tabs.DBG_FILE)
                        self.row = self.endRow(line)
                        self.moveRight()
        print('moveCursor(row={}, col={}, back={}) new: row={}, col={}'.format(row, col, back, self.row, self.col), file=Tabs.DBG_FILE)
    
    def hiliteRowColNum(self, dbg=0):
        self.hiliteCount += 1
        if dbg: print('hiliteRowColNum({}, {}) hilitePrevRowPos={}, hiliteRowNum={}, hiliteColNum={}, hiliteCount={}'.format(self.row, self.col, self.hilitePrevRowPos, self.hiliteRowNum, self.hiliteColNum, self.hiliteCount), file=Tabs.DBG_FILE)
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
        if dbg: print('hiliteRowColNum({}, {}) hilitePrevRowPos={}, hiliteRowNum={}, hiliteColNum={}, hiliteCount={}'.format(self.row, self.col, self.hilitePrevRowPos, self.hiliteRowNum, self.hiliteColNum, self.hiliteCount), file=Tabs.DBG_FILE)
        self.prints(self.hiliteRowNum, self.row, self.editModeCol, self.styles['BRIGHT'] + self.styles['TABS'])
        self.resetPos()
    
    def deleteTab(self, row=None, col=None, back=0):
        row, col = self.row, self.col
        r, c = self.rowCol2Indices(row, col)
        tab = self.tabs[r][c]
        tabFN = self.getFretNum(tab)
        maxFN = self.getFretNum(self.maxFret)
        if self.editMode == self.EDIT_MODES['INSERT']:
            print('deleteTab(row={} col={} back={}) r={} c={} EDIT_MODES[INSERT]'.format(row, col, back, r, c), file=Tabs.DBG_FILE)
            for cc in range(c, len(self.tabs[r]) - 1):
                self.tabs[r][cc]  = self.tabs[r][cc + 1]
                self.htabs[r][cc] = self.htabs[r][cc + 1]
            cc = len(self.tabs[r]) - 1
            self.tabs[r][cc]  = ord('-')
            self.htabs[r][cc] = ord('0')
            if back: self.moveLeft()
            self.printTabs()
        elif self.editMode == self.EDIT_MODES['REPLACE']:
            print('deleteTab(row={} col={} back={}) r={} c={} EDIT_MODES[REPLACE]'.format(row, col, back, r, c), file=Tabs.DBG_FILE)
            self.moveCursor(back=back)
            self.tabs[r][c] = ord('-')
            self.htabs[r][c] = ord('0')
            self.prints(chr(self.tabs[r][c]), row, col, self.styles['TABS'])
            if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                self.prints(chr(self.tabs[r][c]), row + self.numStrings, col, self.styles['NAT_NOTE'])
            if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
                self.chordsObj.eraseChord(c)
                self.chordsObj.printChord(c=c)
            if self.displayIntervals == self.DISPLAY_INTERVALS['ENABLED']:
                self.printColumnIvals(c)
            self.moveTo()
        if Tabs.isFret(chr(tab)) and tabFN == maxFN:
            self.maxFret = self.findMaxFret()
#            print('deleteTab() reset maxFret={}, chr(maxFret)={}, maxFN={}, tab={}, tabc={}, tabFN={}'.format(self.maxFret, chr(self.maxFret), self.getFretNum(self.maxFret), tab, chr(tab), tabFN), file=Tabs.DBG_FILE)
    
    def deletePrevTab(self):
        '''Delete previous tab (backspace).'''
        if self.cursorMode == self.CURSOR_MODES['MELODY']:
            self.deleteTab(col=self.col-1, back=1)
        elif self.cursorMode == self.CURSOR_MODES['CHORD']:
            if self.cursorDir == self.CURSOR_DIRS['UP']:
                self.deleteTab(row=self.row+1, back=1)
            elif self.cursorDir == self.CURSOR_DIRS['DOWN']:
                self.deleteTab(row=self.row-1, back=1)
        elif self.cursorMode == self.CURSOR_MODES['ARPEGGIO']:
            if self.cursorDir == self.CURSOR_DIRS['UP']:
                self.deleteTab(row=self.row+1, col=self.col-1, back=1)
            elif self.cursorDir == self.CURSOR_DIRS['DOWN']:
                self.deleteTab(row=self.row-1, col=self.col-1, back=1)
    
    def eraseTabs(self):
        '''Erase all tabs (resets all tabs to '-').'''
        print('eraseTabs()', file=Tabs.DBG_FILE)
        for r in range(0, len(self.tabs)):
            for c in range(0, len(self.tabs[r])):
                self.tabs[r][c] = ord('-')
                self.htabs[r][c] = ord('0')
                if c in self.chordInfo:
                    del self.chordInfo[c]
        self.maxFret = ord('0')
        self.printTabs()
    
    def resetTabs(self):
        '''Reset all tabs to their initial state at start up.'''
        self.init()
    
    def saveTabs(self):
        '''Save all tabs (with ANSI codes) to the configured output file.  Use cat to display the file'''
        with open(self.outName, 'w') as self.outFile:
            self.printLineInfo('saveTabs({}, {}) bgn writing tabs to file'.format(self.row, self.col))
            Tabs.clearScreen(file=self.outFile, reason='saveTabs()')
            print(self.cmdLine, file=self.outFile)
            print('cmdLineArgs:', file=self.outFile)
            for k in self.argMap:
                print('    {}={}'.format(k, self.argMap[k]), file=self.outFile)
            self.printStringMap(file=self.outFile)
            self.printTabs()
            self.moveTo(hi=1)
            print(self.CSI + self.styles['NORMAL'] + self.styles['CONS'] + self.CSI + '{};{}H'.format(self.lastRow, 1), end='', file=self.outFile) # set the file cursor to the front of the next row (NUM_STR+r+1, 0) and set the foreground and background color
            self.dumpTabs('saveTabs(h)', h=1)
            self.printLineInfo('saveTabs({}, {}) end writing tabs to file'.format(self.row, self.col))
        self.outFile = None
        self.printTabs()
    
    def shiftSelectTabs(self):
        '''Shift selected tabs (left or right) specified by user numeric input of up to 3 characters terminated by space char.'''
        c, tmp = '', []
        while len(tmp) <= 3:
            c = getwch()
            if c != ' ': tmp.append(c)
            else: break
        shift = int(''.join(tmp))
        shifted = False
        print('shiftSelectTabs() shift={} selectCols={}'.format(shift, self.selectCols), file=Tabs.DBG_FILE)
        for cc in range(0, len(self.selectCols)):
            for r in range(0, self.numStrings):
                c = self.selectCols[cc]
                tab = self.tabs[r][c]
                if Tabs.isFret(chr(tab)):
                    tabFN = self.getFretNum(tab)
                    if 0 <= self.getFretNum(tab) + shift <= self.NUM_FRETS:
                        self.tabs[r][c] = self.getFretByte(self.getFretNum(tab) + shift)
                        shifted = True
                        print('shiftSelectTabs({},{}) tab={} tabFN={} shift={} shiftedFN={} shifted={}'.format(r, c, chr(tab), tabFN, shift, tabFN + shift, chr(self.tabs[r][c])), file=Tabs.DBG_FILE)
                    else: self.printe('shiftSelectTabs() out of range (0-{})! r={} c={} tab={} tabFN={} shift={}'.format(self.NUM_FRETS, r, c, chr(tab), tabFN, shift))
        self.selectCols = []
        if shifted:
            self.printTabs()
    
    def copySelectTabs(self, arpg=None):
        '''Copy selected tabs.  If arpg==1, transform selected tabs from a chord to an arpeggio, elif arpg==0, transform selected tabs from an arpeggio to a chord.'''
        self.arpeggiate, ns, nt, nsr, nsc = arpg, self.numStrings, len(self.tabs[0]), len(self.selectRows), len(self.selectCols)
        if nsr == 0 or nsc == 0:
            self.printe('copySelectTabs() no tabs selected, nsr={}, nsc={}, use the CTRL ARROW keys to select rows and or columns'.format(nsr, nsc))
            return
        if arpg is None: size, nc = nsc,           nsc
        elif  arpg == 1: size, nc = nsc * nsr,     nsc
        elif  arpg == 0: size, nc = int(nsc / ns), int(nsc / ns)
        self.printSelectTabs(info='copySelectTabs()', cols=1)
        for r in range(0, nsr):
            self.selectTabs.append(bytearray([ord(' ')] * size))
            self.selectHTabs.append(bytearray([ord('0')] * size))
        nst = len(self.selectTabs[0])
        print('copySelectTabs({},{}) row={}, col={}, ns={}, nsr={}, nsc={}, nt={}, nst={}, nc={}'.format(arpg, self.cursorDir, self.row, self.col, ns, nsr, nsc, nt, nst, nc), file=Tabs.DBG_FILE)
        for c in range(0, nc):
            cc = self.selectCols[c]
            for r in range(0, nsr):
                rr = self.selectRows[r]
                if arpg is None: cst, ct = c, cc
                elif arpg == 0:
                    if   self.cursorDir == self.CURSOR_DIRS['DOWN']: cst, ct = c, c * ns + r + cc - c
                    elif self.cursorDir == self.CURSOR_DIRS['UP']:   cst, ct = c, (c + 1) * ns - r - 1 + cc - c
                elif arpg == 1:
                    if   self.cursorDir == self.CURSOR_DIRS['DOWN']: cst, ct = c * nsr + r, cc
                    elif self.cursorDir == self.CURSOR_DIRS['UP']:   cst, ct = (c + 1) * nsr - r - 1, cc
                print('copySelectTabs({},{}) r={}, rr={}, c={}, cc={}, cst={}, ct={}, '.format(arpg, self.cursorDir, r, rr, c, cc, cst, ct), end='', file=Tabs.DBG_FILE)
                self.selectTabs[r][cst]  = self.tabs[rr][ct]
                self.selectHTabs[r][cst] = self.htabs[rr][ct]
                print('copySelectTabs() selectTabs[{}][{}]={}, tabs[{}][{}]={}'.format(r, cst, chr(self.selectTabs[r][cst]), rr, ct, chr(self.tabs[rr][ct])), file=Tabs.DBG_FILE)
            self.printSelectTabs(info='copySelectTabs()')
    
    def deleteSelectTabs(self, delSel=True):
        '''Delete selected tabs.'''
        self.printLineInfo('deleteSelectTabs({}, {}) delSel={} selectCols={}'.format(self.row, self.col, delSel, self.selectCols))
        self.selectCols.sort(key = int, reverse = True)
        for c in range(0, len(self.selectCols)):
            self.deleteTabs(self.selectCols[c])
        if delSel:
            self.selectCols = []
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.chordsObj.printChords()
        self.maxFret = self.findMaxFret()
        self.resetPos()
    
    def cutSelectTabs(self, arpg=None):
        '''Cut selected tabs.'''
        self.copySelectTabs(arpg=arpg)
        self.deleteSelectTabs(delSel=False)
    
    def printSelectTabs(self, info='', cols=0):
        print('printSelectTabs(cols={}, info={}) len(selectCols)={}, len(selectTabs)={}'.format(cols, info, len(self.selectCols), len(self.selectTabs)), file=Tabs.DBG_FILE)
        if cols:
            for c in range(0, len(self.selectCols)):
                print('    selectCols[{}]={}'.format(c, self.selectCols[c]), file=Tabs.DBG_FILE)
        for c in range(0, len(self.selectTabs)):
            print('    selectTabs[{}]={}'.format(c, self.selectTabs[c]), file=Tabs.DBG_FILE)
    
    def deleteTabs(self, cc):
        row, col = self.indices2RowCol(0, cc)
        print('deleteTabs({})'.format(cc), file=Tabs.DBG_FILE)
        if cc in self.chordInfo:
            print('deleteTabs() deleting chordInfo[{}]={}'.format(cc, self.chordInfo[cc]), file=Tabs.DBG_FILE)
            del self.chordInfo[cc]
            print('deleteTabs() chordInfo={}'.format(self.chordInfo), file=Tabs.DBG_FILE)
#        self.dumpTabs('deleteTabs({}, {}) (row,col)=({},{}), cc={} bgn: '.format(self.row, self.col, row, col, cc))
        if self.editMode == self.EDIT_MODES['INSERT']:
            for r in range(0, self.numStrings):
                for c in range(cc, len(self.tabs[r]) - 1):
                    self.tabs[r][c] = self.tabs[r][c + 1]
                    self.htabs[r][c] = self.htabs[r][c + 1]
                    if r == 0 and c+1 in self.chordInfo:
                        self.chordInfo[c] = self.chordInfo[c + 1]
                        del self.chordInfo[c + 1]
            self.printTabs()
        elif self.editMode == self.EDIT_MODES['REPLACE']:
            for r in range(0, self.numStrings):
                tab = '-'
                self.tabs[r][cc] = ord(tab)
                self.htabs[r][cc] = ord('0')
                self.prints(tab, r + row, col, self.styles['TABS'])
                if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                    rr = r + row + self.numStrings
                    print('deleteTabs(DISPLAY_NOTES) prints({}, {}, {})'.format(tab, rr, col), file=Tabs.DBG_FILE)
                    self.prints(tab, rr, col, self.styles['NAT_NOTE'])
                if self.displayIntervals == self.DISPLAY_INTERVALS['ENABLED']:
                    rr = r + row + self.numStrings + self.NOTES_LEN
                    print('deleteTabs(DISPLAY_INTERVALS) prints({}, {}, {})'.format(tab, rr, col), file=Tabs.DBG_FILE)
                    self.prints(tab, rr, col, self.styles['NAT_NOTE'])
#        self.dumpTabs('deleteTabs({}, {}) col={} end: '.format(self.row, self.col, col))
    
    def _initPasteInfo(self):
        nc, rangeError, row, col, rr, cc = 0, 0, self.row, self.col, 0, 0
        line, ns, nt, nsr, nsc, nst = self.row2Line(self.row), self.numStrings, len(self.tabs[0]), len(self.selectRows), len(self.selectCols), len(self.selectTabs)
        if nst == 0:
            self.printe('_initPasteInfo() no tabs to paste, nsr={}, nsc={}, nst={}, use CTRL/SHIFT C or X to copy or cut selected tabs'.format(nsr, nsc, nst))
            return rangeError, nc, row, col, self.row2Index(row), cc, line, ns, nt, nsr, nsc, nst
        nst, br, er = len(self.selectTabs[0]), self.bgnRow(line), self.endRow(line)
        print('_initPasteInfo({},{}) ({},{}) bgn ns={}, nt={}, nsr={}, nsc={}, nst={}, line={}, br={}, er={}'.format(self.arpeggiate, self.cursorDir, row, col, ns, nt, nsr, nsc, nst, line, br, er), file=Tabs.DBG_FILE)
        while row + nsr - 1 > er:
            row -= 1
            if row < br: self.printe('_initPasteInfo() tried to adjust row={} < br={}, nsr={}'.format(row, br, nsr))
            print('_initPasteInfo(--row) row={} + nsr={} - 1 <= er={}'.format(row, nsr, er), file=Tabs.DBG_FILE)
        rr, cc = self.rowCol2Indices(row, col)
        if self.arpeggiate is None: nc = nsc
        else:                       nc = nst
        print('_initPasteInfo({},{}) row={}, col={}, rr={}, cc={}, nc={}'.format(self.arpeggiate, self.cursorDir, row, col, rr, cc, nc), file=Tabs.DBG_FILE)
        if self.editMode == self.EDIT_MODES['INSERT']:
            for c in range(nt - 1, cc - 1, -1):
                for r in range(0, nsr):
                    if c >= nc + cc:
                        self.tabs[r][c] = self.tabs[r][c - nc]
                        self.htabs[r][c] = self.htabs[r][c - nc]
                        print('_initPasteInfo(INSERT) c={} >= cc={} + nc={}, tabs[{}][{}]={}'.format(c, cc, nc, r, c, chr(self.tabs[r][c])), file=Tabs.DBG_FILE)
                    elif self.arpeggiate:
                        self.tabs[r][c] = ord('-')
                        self.htabs[r][c] = ord('-')
                        print('_initPasteInfo(INSERT) c={} < cc={} + nst={}, tabs[{}][{}]={}'.format(c, cc, nst, r, c, chr(self.tabs[r][c])), file=Tabs.DBG_FILE)
        elif self.editMode == self.EDIT_MODES['REPLACE'] and self.arpeggiate and cc + nst < nt:
            for c in range(cc, cc + nst):
                for r in range(0, nsr):
                    self.tabs[r][c] = ord('-')
                    self.htabs[r][c] = ord('-')
                    print('_initPasteInfo(REPLACE) tabs[{}][{}]={}'.format(r, c, chr(self.tabs[r][c])), file=Tabs.DBG_FILE)
        for c in range(0, nsc):
            if rangeError: break
            for r in range(0, nsr):
                if self.arpeggiate == 1:
                    if   self.cursorDir == self.CURSOR_DIRS['DOWN']: ccc = c * nsr + r
                    elif self.cursorDir == self.CURSOR_DIRS['UP']:   ccc = (c + 1) * nsr - r - 1
                else: ccc = c
                print('_initPasteInfo(check) r={}, rr={}, c={}, cc={}, ccc={}, nt={}, nst={}'.format(r, rr, c, cc, ccc, nt, nst), end='', file=Tabs.DBG_FILE)
                if c < nst:
                    if ccc + cc < nt:
                        self.tabs[r + rr][ccc + cc] = self.selectTabs[r][ccc]
                        self.htabs[r + rr][ccc + cc] = self.selectHTabs[r][ccc]
                        print(', selectTabs[{}][{}]={}, tabs[{}][{}]={}'.format(r, ccc, chr(self.selectTabs[r][ccc]), r + rr, ccc + cc, chr(self.tabs[r + rr][ccc + cc])), file=Tabs.DBG_FILE)
                    else:
                        print(file=Tabs.DBG_FILE)
                        self.printe('_initPasteInfo() ccc={} + cc={} >= len(tabs[0])={} skip remaining rows and columns'.format(ccc, cc, len(self.tabs[0])))
                        rangeError = 1
                        break
            print('_initPasteInfo(loop1) c={} selectCols[c]={} selectCols={}'.format(c, self.selectCols[c], self.selectCols), file=Tabs.DBG_FILE)
            if not rangeError: self.selectStyle(self.selectCols[c], self.styles['NORMAL'], rList=self.selectRows)
        return rangeError, nc, row, col, rr, cc, line, ns, nt, nsr, nsc, nst
    
    def pasteSelectTabs(self, dbg=0):
        '''Paste selected tabs as is or either stretched in time (like arpeggios) or compressed in time.'''
        rangeError, nc, row, col, rr, cc, line, ns, nt, nsr, nsc, nst = self._initPasteInfo()
        if nst == 0: return
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.chordsObj.printChords()
        if self.editMode == self.EDIT_MODES['INSERT']:
            self.printTabs()
        elif self.editMode == self.EDIT_MODES['REPLACE']:
            for c in range(cc, cc + nc):
                if c >= len(self.tabs[0]):
                    self.printe('pasteSelectTabs() c={} + nc={} >= len(tabs[0])={} skip remaining columns'.format(c, nc, len(self.tabs[0])))
                    break
                col = self.index2Col(c)
                if c % self.numTabsPerStringPerLine == 0:
                    row += self.lineDelta()
                    if dbg: print('pasteSelectTabs(wrap) row={}, col={}, c={}'.format(row, col, c), file=Tabs.DBG_FILE)
                for r in range(rr, rr + nsr):
                    row = self.indices2Row(r, c)
                    tab = self.tabs[r][c]
                    if dbg: print('pasteSelectTabs(loop2) row={}, col={}, r={}, c={}, tabc[{}][{}]={}'.format(row, col, r, c, r, c, chr(tab)), file=Tabs.DBG_FILE)
                    if self.htabs[r][c] == ord('1'):
                        self.prints(chr(tab), row, col, self.styles['H_TABS'])
                    else:
                        self.prints(chr(tab), row, col, self.styles['TABS'])
                    if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                        if Tabs.isFret(chr(tab)):
                            if self.htabs[r][c] == ord('1'):
                                n = self.getHarmonicNote(r + 1, tab)
                                self.printNote(row + r + self.numStrings, col, n, hn=1)
                            else:
                                n = self.getNote(r + 1, tab)
                                self.printNote(row + self.numStrings, col, n)
                        else:
                            self.prints(chr(tab), row + self.numStrings, col, self.styles['NAT_NOTE'])
                    if self.displayIntervals == self.DISPLAY_INTERVALS['ENABLED']:
                        if dbg: print('pasteSelectTabs(DISPLAY_INTERVALS) row={} col={} r={} c={} cc={} tab={} selectCols={} chordInfo={}'.format(row, col, r, c, cc, chr(tab), self.selectCols, self.chordInfo), file=Tabs.DBG_FILE)
                        self.printInterval(row + self.numStrings + self.NOTES_LEN, col, '-', dbg=0)
                        if c in self.chordInfo:
                            self.wrapPrintInterval(r, c, dbg=dbg)
            self.resetPos()
        if not rangeError:
            self.selectTabs, self.selectHTabs, self.selectCols, self.selectRows = [], [], [], []
        self.resetPos()
        self.arpeggiate, self.selectFlag = 0, 0
        self.dumpTabs('pasteSelectTabs({},{}) end row={}, col={}'.format(self.arpeggiate, self.cursorDir, row, col))
    
    def dumpTabs(self, reason='', h=None):
        print('dumpTabs({})'.format(reason), file=Tabs.DBG_FILE)
        for line in range(0, self.numLines):
            for r in range(0, self.numStrings): #len(self.tabs)):
                if r == 0:
                    print('L={}: '.format(line), end='', file=Tabs.DBG_FILE)
                    for c in range(0, self.numTabsPerStringPerLine):
                        print('{}'.format(Tabs.getColMod(c)), end='', file=Tabs.DBG_FILE)
                    print(file=Tabs.DBG_FILE)
                print('R={}: '.format(r), end='', file=Tabs.DBG_FILE)
                for c in range(0, self.numTabsPerStringPerLine):
                    if h is None:
                        print(chr(self.tabs[r][c + line * self.numTabsPerStringPerLine]), end='', file=Tabs.DBG_FILE)
                    else:
                        print(chr(self.htabs[r][c + line * self.numTabsPerStringPerLine]), end='', file=Tabs.DBG_FILE)
                print('', file=Tabs.DBG_FILE)
    
    def printLineInfo(self, reason):
        print('{} numStrings={}, numLines={}, lineDelta={},'.format(reason, self.numStrings, self.numLines, self.lineDelta()), end='', file=Tabs.DBG_FILE)
        for line in range(0, self.numLines):
            print(' bgnRow{}={}, endRow{}={},'.format(line, self.bgnRow(line), line, self.endRow(line)), end='', file=Tabs.DBG_FILE)
        print(' ROW_OFF={} lastRow={}, bgnCol={}, endCol={}, line={}'.format(self.ROW_OFF, self.lastRow, self.bgnCol(), self.endCol(), self.row2Line(self.row)), file=Tabs.DBG_FILE)
    
    def printTabs(self, cs=0):
        '''Print tabs using ANSI escape sequences to control the cursor position, foreground and background colors, and brightness'''
        self.printLineInfo('printTabs(cs={}) outFile={} bgn'.format(cs, self.outFile))
        if cs: Tabs.clearScreen(reason='printTabs()')
        self.printFileMark('<BGN_TABS_SECTION>')
        for line in range(self.numLines):
            for r in range(0, self.numStrings):
                row = r + line * self.lineDelta() + self.ROW_OFF
                for c in range(self.numTabsPerStringPerLine):
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
            self.printNotes()
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.chordsObj.printChords()
        if self.displayIntervals == self.DISPLAY_INTERVALS['ENABLED']:
            self.printIntervals()
        if self.displayLabels == self.DISPLAY_LABELS['ENABLED']:
            self.printLabels()
        if self.row > 0 and self.col > 0:
            print(self.CSI + self.styles['NORMAL'] + self.styles['CONS'] + self.CSI + '{};{}H'.format(self.row, self.col), end='') # restore the console cursor to the given position (row, col) and set the foreground and background color
        self.printLineInfo('printTabs({}, {}) end'.format(self.row, self.col))
    
    def printFileMark(self, mark):
        if self.outFile != None:
            if mark == '<BGN_TABS_SECTION>' or mark == '<END_TABS_SECTION>':
                print('{}'.format(mark), file=self.outFile)
            else:
                print(self.CSI + self.styles['NORMAL'] + self.styles['CONS'] + self.CSI + '{};{}H{}'.format(1, 1, mark), file=self.outFile)
    
    def getNoteStyle(self, n, style, hn=None):
        if hn is None:
            natStyle = style + self.styles['NAT_NOTE']
            fltStyle = style + self.styles['FLT_NOTE']
            shpStyle = style + self.styles['SHP_NOTE']
        else:
            natStyle = style + self.styles['NAT_H_NOTE']
            fltStyle = style + self.styles['FLT_H_NOTE']
            shpStyle = style + self.styles['SHP_H_NOTE']
        return self.getEnharmonicStyle(n.name, natStyle, fltStyle, shpStyle)
    
    def printNotes(self):
        self.printFileMark('<BGN_NOTES_SECTION>')
        for line in range(0, self.numLines):
            for r in range(0, self.numStrings):
                row = r + line * self.lineDelta() + self.endRow(0) + 1
                for c in range (0, self.numTabsPerStringPerLine):
                    capTab = tab = self.tabs[r][c + line * self.numTabsPerStringPerLine]
                    if Tabs.isFret(chr(tab)):
                        capTab = self.getFretByte(self.getFretNum(tab) + self.getFretNum(self.capo))
                    if c == 0:
                        n = self.getNote(r + 1, ord('0'))
                        self.printNote(row, self.editModeCol, n)
                        if self.cursorDir == self.CURSOR_DIRS['DOWN']:
                            self.prints(chr(self.capo), row, self.cursorModeCol, self.styles['NUT_DN'])
                        elif self.cursorDir == self.CURSOR_DIRS['UP']:
                            self.prints(chr(self.capo), row, self.cursorModeCol, self.styles['NUT_UP'])
                    if Tabs.isFret(chr(capTab)):
                        if chr(self.htabs[r][c + line * self.numTabsPerStringPerLine]) == '1':
                            print('printNotes() tab={}, capTab={}, tabc={}, chr(capTab)={}, tabFN={}, capoFN={}'.format(tab, capTab, chr(tab), chr(capTab), self.getFretNum(tab), self.getFretNum(capTab)), file=Tabs.DBG_FILE)
                            n = self.getHarmonicNote(r + 1, tab)
                            self.printNote(row, c + self.COL_OFF, n, hn=1)
                        else:
                            n = self.getNote(r + 1, tab)
                            self.printNote(row, c + self.COL_OFF, n)
                    else: self.prints(chr(tab), row, c + self.COL_OFF, self.styles['NAT_NOTE'])
                print(file=self.outFile)
            print()
        self.printFileMark('<END_NOTES_SECTION>')
    
    def printNote(self, row, col, n, style='', hn=None, dbg=0):
        if dbg: print('printNote() row={},col={}, nn={}'.format(row, col, n.name), file=Tabs.DBG_FILE)
        style = self.getNoteStyle(n, style, hn)
        self.prints(n.name[0], row, col, style)
    
    def printColumnIvals(self, c, dbg=0):
        line = self.colIndex2Line(c)
        if dbg: print('printColumnIvals() line={} selectChords={}'.format(line, self.selectChords), file=Tabs.DBG_FILE)
        for r in range(0, self.numStrings):
            row = r + line * self.lineDelta() + self.endRow(0) + self.NOTES_LEN + 1
            cc = c % self.numTabsPerStringPerLine
            self.prints('-', row, cc + self.COL_OFF, self.styles['NAT_H_NOTE'])
            if r == 0 and c == 0:
                self.printMapLimap(self.chordInfo, reason='printColumnIvals() line={} r={} row={} c={} cc={}'.format(line, r, row, c, cc))
            if c in self.chordInfo: 
                self.wrapPrintInterval(r, c, dbg=dbg)
    
    def printIntervals(self, dbg=0):
        self.printFileMark('<BGN_INTERVALS_SECTION>')
        if dbg:
            print('printIntervals() chordInfo={}'.format(self.chordInfo), file=Tabs.DBG_FILE)
            print('printIntervals() selectChords={}'.format(self.selectChords), file=Tabs.DBG_FILE)
        for line in range(0, self.numLines):
            for r in range(0, self.numStrings):
                row = r + line * self.lineDelta() + self.endRow(0) + self.NOTES_LEN + 1
                self.prints(self.IVAL_LABEL[r], row, 1, self.styles['IVAL_LABEL'])
                for c in range(2, self.COL_OFF):
                    self.prints(' ', row, c, self.styles['IVAL_LABEL'])
            for c in range (0, self.numTabsPerStringPerLine):
                cc = c + line * self.numTabsPerStringPerLine
                self.printColumnIvals(cc)
        self.printFileMark('<END_INTERVALS_SECTION>')
    
    def printInterval(self, row, col, ival, dbg=0):
        style = self.styles['NAT_H_NOTE']
        if dbg: print('printInterval() row={} col={} ival={}'.format(row, col, ival), file=Tabs.DBG_FILE)
        if len(ival) > 1:
            if ival == 'm2' or ival == 'm3' or ival == 'b5' or ival == 'b7': style = self.styles['FLT_H_NOTE']
            elif ival == 'a5': style = self.styles['SHP_H_NOTE']
            ival = ival[1]
        self.prints(ival, row, col, style)
    
    def wrapPrintInterval(self, r, c, dbg=0):
        imap = self.chordInfo[c][0]
        imapstr = Tabs.imap2String(imap)
        if imapstr in self.selectImaps:
            imap = self.selectImaps[imapstr]
            if r == 0:
                print('wrapPrintInterval({:>3}) FOUND imapstr={} in'.format(c, imapstr, self.selectImaps, imap), end=' ', file=Tabs.DBG_FILE)
                self.printSelectImaps()
                print('wrapPrintInterval({:>3}) SWAPPING imap={}'.format(c, self.imap2String(imap)), file=Tabs.DBG_FILE)
        im = {imap[k]:k for k in imap}
        tab = self.tabs[r][c]
        if dbg: print('wrapPrintInterval() r={} c={} tab={} im={} imapstr={} imap={} selectImaps={}'.format(r, c, chr(tab), im, imapstr, imap, self.selectImaps), file=Tabs.DBG_FILE)
        if Tabs.isFret(chr(tab)):
            row, col = self.indices2RowCol(r, c)
            if chr(self.htabs[r][c]) == '1':
                n = self.getHarmonicNote(r + 1, tab)
            else:
                n = self.getNote(r + 1, tab)
            nn = n.name
            if nn in im:
                self.printInterval(row + self.numStrings + self.NOTES_LEN, col, im[nn])
    
    def printLabels(self):
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
#        self.printFileMark('<END_LABELS_SECTION>')
    
    def printChordInfoMap(self, ci, reason=None):
        print('printChordInfoMap() {} chordInfo={{'.format(reason), file=self.DBG_FILE)
        for cik in ci:
            print('{} : {}'.format(cik, self.chordsObj.chordNames[cik]), end=' ', file=self.DBG_FILE)
            for m in ci[cik]:
                imap = self.imap2String(m)
                print('[{}]'.format(imap), end=' ', file=self.DBG_FILE)
            print('', file=self.DBG_FILE)
        print('}', file=self.DBG_FILE)
    
    def printMapLimap(self, m, reason=None):
        print('printMapLimap() {} chordInfo(len={})={{'.format(reason, len(m)), file=self.DBG_FILE)
        for k in m:
            temp = '{:>3} : {:<7}'.format(k, self.chordsObj.chordNames[k])
            self.printLimap(m[k], reason=temp)
    
    def printLimap(self, limap, reason=None):
        print('{} limap={{'.format(reason), end=' ', file=self.DBG_FILE)
        for m in limap:
            imap = self.imap2String(m)
            print('[{}]'.format(imap), end=',', file=self.DBG_FILE)
        print('}', file=self.DBG_FILE)
    
    @staticmethod
    def imap2String(imap):
        s = ''
        for k in imap: s += '{} '.format(imap[k])
        s += '\\ '
        for k in imap: s += '{} '.format(k)
        return s.strip()
    
    def printStatus(self):
        r, c = self.rowCol2Indices(self.row, self.col)
        print('printStatus({}, {}) r={}, c={}, tab={}'.format(self.row, self.col, r, c, self.tabs[r][c]), file=Tabs.DBG_FILE)
        tab = chr(self.tabs[r][c])
        if   Tabs.isFret(tab): self.printFretStatus(tab, r, c)
        elif tab in self.mods: self.printModStatus(tab, r, c)
        else:                  self.printDefaultStatus(tab, r, c)
        Tabs.clearRow(arg=0, row=self.lastRow, col=0, file=self.outFile)
        self.printChordStatus(tab, r, c)
        self.resetPos()
    
    def printFretStatus(self, tab, r, c):
        s, ss = r + 1, self.getOrdSfx(r + 1)
        f, fs = self.getFretNum(ord(tab)), self.getOrdSfx(self.getFretNum(ord(tab)))
        statStyle, fretStyle, typeStyle, noteStyle = self.CSI + self.styles['STATUS'], self.CSI + self.styles['TABS'], self.CSI + self.styles['TABS'], self.CSI + self.styles['TABS']
        if self.htabs[r][c] == ord('1'): n, noteType, tabStyle = self.getHarmonicNote(s, ord(tab)), 'harmonic', self.CSI + self.styles['H_TABS']
        else:                            n, noteType, tabStyle = self.getNote(s, ord(tab)), None, self.CSI + self.styles['TABS']
        if len(n.name) > 1:
            if n.name[1] == '#': noteStyle = self.CSI + self.styles['SHP_NOTE']
            else:                noteStyle = self.CSI + self.styles['FLT_NOTE']
        print('printFretStatus({}) r={}, c={}, tab={}, n.n={}, n.o={}, n.i={}, {}'.format(noteType, r, c, tab, n.name, n.getOctaveNum(), n.index, n.getPhysProps()), file=Tabs.DBG_FILE)
        print(tabStyle + self.CSI + '{};{}H{}'.format(self.lastRow, 1, tab), end='', file=self.outFile)
        if f != 0: print(fretStyle + ' {}{}'.format(s, ss) + statStyle + ' string ' + fretStyle + '{}{}'.format(f, fs) + statStyle + ' fret ', end='', file=self.outFile)
        else:      print(fretStyle + ' {}{}'.format(s, ss) + statStyle + ' string ' + fretStyle + 'open' + statStyle + ' fret ', end='', file=self.outFile)
        if noteType: print(typeStyle + '{} '.format(noteType), end='', file=self.outFile)
        print(noteStyle + '{}{}'.format(n.name, n.getOctaveNum()), end='', file=self.outFile)
        print(statStyle + ' index=' + fretStyle + '{}'.format(n.index), end='', file=self.outFile)
        print(statStyle + ' freq=' + fretStyle + '{:03.2f}'.format(n.getFreq()) + statStyle + 'Hz', end='', file=self.outFile)
        print(statStyle + ' wvln=' + fretStyle + '{:04.3f}'.format(n.getWaveLen()) + statStyle + 'm', end='', file=self.outFile)
    
    def printModStatus(self, tab, r, c):
        ph, nh, s, ss = 0, 0,  r + 1, self.getOrdSfx(r + 1)
        prevFN, nextFN, prevNote, nextNote, dir1, dir2 = None, None, None, None, None, None
        if Tabs.isFret(chr(self.tabs[r][c-1])): 
            prevFN = self.getFretNum(self.tabs[r][c-1])
            if self.htabs[r][c-1] == ord('1'): 
                prevNote = self.getHarmonicNote(s, self.tabs[r][c-1])
                ph=1
            else: prevNote = self.getNote(s, self.tabs[r][c-1])
        if Tabs.isFret(chr(self.tabs[r][c+1])): 
            nextFN = self.getFretNum(self.tabs[r][c+1])
            if self.htabs[r][c+1] == ord('1'): 
                nextNote = self.getHarmonicNote(s, self.tabs[r][c+1])
                nh=1
            else: nextNote = self.getNote(s, self.tabs[r][c+1])
        if prevFN is not None and nextFN is not None:
            if   prevFN < nextFN: dir1, dir2 = 'up',   'on'
            elif prevFN > nextFN: dir1, dir2 = 'down', 'off'
        print('printModStatus({}, {}) tab={}, pfn={}, nfn={}'.format(r, c, tab, prevFN, nextFN), file=Tabs.DBG_FILE)
        self.modsObj.setMods(dir1=dir1, dir2=dir2, prevFN=prevFN, nextFN=nextFN, prevNote=prevNote, nextNote=nextNote, ph=ph, nh=nh)
        print(self.CSI + self.styles['TABS'] + self.CSI + '{};{}H{} '.format(self.lastRow, 1, tab), end='', file=self.outFile)
        print(self.CSI + self.styles['TABS'] + '{}{}'.format(s, ss) + self.CSI + self.styles['STATUS'] + ' string {}'.format(self.mods[tab]), end='', file=self.outFile)
    
    def printDefaultStatus(self, tab, r, c):
        s, ss, tabStyle, statStyle = r + 1, self.getOrdSfx(r + 1), self.CSI + self.styles['TABS'], self.CSI + self.styles['STATUS']
        print('printDefaultStatus({}, {}) tab={}'.format(r, c, tab), file=Tabs.DBG_FILE)
        print(tabStyle + self.CSI + '{};{}H{} '.format(self.lastRow, 1, tab), end='', file=self.outFile)
        print(tabStyle + '{}{}'.format(s, ss) + statStyle + ' string ' + tabStyle + 'muted' + statStyle + ' not played', end='', file=self.outFile)
    
    def printChordStatus(self, tab, r, c, dbg=0):
        if c in self.chordInfo:
            if dbg: self.printMapLimap(self.chordInfo, reason='printChordStatus() len(chordInfo[{}])={}'.format(c, len(self.chordInfo[c])))
            self.printChordInfo(tab, r, c, 0)
    
    def analyzeChord(self):
        r, c = self.rowCol2Indices(self.row, self.col)
        tab = chr(self.tabs[r][c])
        print('analyzeChord({}, {}) r={}, c={}, tab={}'.format(self.row, self.col, r, c, tab), file=Tabs.DBG_FILE)
        if c in self.chordInfo:
            self.analyzeIndex += 1
            m = self.analyzeIndex % len(self.chordInfo[c])
            print('analyzeChord() m={} analyzeIndex={} len(chordInfo[{}])={}'.format(m, self.analyzeIndex, c, len(self.chordInfo[c])), file=Tabs.DBG_FILE)
            self.printChordInfo(tab, r, c, m)
        self.resetPos()
    
    def selectChord(self, dbg=0):
        r, c = self.rowCol2Indices(self.row, self.col)
        if dbg: print('selectChord() row={} col={} r={} c={}'.format(self.row, self.col, r, c), file=Tabs.DBG_FILE)
        if c in self.chordInfo:
            self.printLimap(self.chordInfo[c], reason='selectChord()')
            m = self.analyzeIndex % len(self.chordInfo[c])
            name, imap = self.printChordInfo(chr(self.tabs[r][c]), r, c, m)
            self.selectChords[name] = imap
            print('selectChord() m={} analyzeIndex={} selectChords[{}]={}'.format(m, self.analyzeIndex, name, self.imap2String(self.selectChords[name])), file=Tabs.DBG_FILE)
            im = self.chordInfo[c][0]
            print('selectChord() adding imapKey={} : imapVal={} to '.format(self.imap2String(im), self.imap2String(imap), self.selectImaps), file=Tabs.DBG_FILE)
            self.printSelectImaps()
            self.selectImaps[self.imap2String(im)] = imap
            self.printSelectImaps()
            self.printTabs()
        self.resetPos()
    
    def printSelectImaps(self):
        print('selectImaps={{'.format(), end=' ', file=Tabs.DBG_FILE)
        for k1 in self.selectImaps:
            print('{} : {}'.format(k1, self.imap2String(self.selectImaps[k1])), end=', ', file=Tabs.DBG_FILE)
        print('}', file=Tabs.DBG_FILE)
    
    def printChordInfo(self, tab, r, c, m, dbg=0):
        imap = self.chordInfo[c][m]
        imapKeys = sorted(imap, key=self.chordsObj.imapKeyFunc, reverse=False)
        if dbg: 
            print('printChordInfo() imap[{}]= [ '.format(m), end='', file=Tabs.DBG_FILE)
            for k in imapKeys: print('{}:{} '.format(k, imap[k]), end='', file=Tabs.DBG_FILE)
            print('], tab={}, r={}, c={}'.format(tab, r, c), file=Tabs.DBG_FILE)
        info, infoLen, i, n, hk, chordKey, chordName, chordDelim = [], 0, 0, None, '', '', '', ' > '
        if Tabs.isFret(tab):
            if self.htabs[r][c] == ord('1'): n = self.getHarmonicNote(r + 1, ord(tab)).name
            else:                            n = self.getNote(r + 1, ord(tab)).name
        for k in imapKeys:
            chordKey += imap[k] + ' '
            info.append('{}:{} '.format(k, imap[k]))
            infoLen += len(info[-1])
            if imap[k] == n: hk = k
            if dbg: print('printChordInfo({}) infoLen={}, info={}, imap[{}]={}, n={}, hk={}, chordKey={}'.format(len(info)-1, infoLen, info, k, imap[k], n, hk, chordKey), file=Tabs.DBG_FILE)
        infoCol = self.numTabsPerStringPerLine + self.COL_OFF - infoLen + 1
        if info: info[-1] = info[-1][:-1]
        if chordKey: chordKey = chordKey[:-1]
        if chordKey in self.chordsObj.chords:
            chordName = self.chordsObj.chords[chordKey]
            infoCol -= (len(chordName) + len(chordDelim))
        if self.chordStatusCol is not None:
            if infoCol < self.chordStatusCol: self.chordStatusCol = infoCol
        else: self.chordStatusCol = infoCol
        print('printChordInfo() chordName={}, info={}, icol={}, chordStatusCol={}'.format(chordName, info, infoCol, self.chordStatusCol), file=Tabs.DBG_FILE)
        Tabs.clearRow(arg=0, row=self.lastRow, col=self.chordStatusCol, file=self.outFile)
        style = self.CSI + self.styles['HLT_STUS']
        if len(chordName) > 0:
            style = self.getEnharmonicStyle(chordName, self.styles['NAT_NOTE'], self.styles['FLT_NOTE'], self.styles['SHP_NOTE'])
            print(self.CSI + style + self.CSI + '{};{}H{}'.format(self.lastRow, infoCol, chordName), end='', file=self.outFile)
            print(self.CSI + self.styles['STATUS'] + '{}'.format(chordDelim), end='', file=self.outFile)
        else: print(style + self.CSI + '{};{}H{}'.format(self.lastRow, infoCol, chordName), end='', file=self.outFile)
        for k in imapKeys:
            if k == hk: style = self.CSI + self.styles['HLT_STUS']
            else:       style = self.CSI + self.styles['STATUS']
            print(style + '{}'.format(info[i]), end='', file=self.outFile)
            i += 1
        return chordName, imap
    
    def getEnharmonicStyle(self, name, defStyle, flatStyle, sharpStyle):
        if len(name) > 1:
            if name[1] == 'b':
                if self.enharmonic == self.ENHARMONICS['FLAT']:  return flatStyle
                else:                                            return sharpStyle
            elif name[1] == '#':
                if self.enharmonic == self.ENHARMONICS['SHARP']: return sharpStyle
                else:                                            return flatStyle
        return defStyle
    
    def prints(self, c, row, col, style):
       print(self.CSI + style + self.CSI + '{};{}H{}'.format(row, col, str(c)), end='', file=self.outFile)
    
    def printe(self, info, row=None, col=None, style=None, x=0):
        if row is None:     row = self.row
        if col is None:     col = self.col
        if style is None: style = self.styles['ERROR']
        info = 'ERROR! printe({}, {}) {}'.format(row, col, info)
        print(info, file=Tabs.DBG_FILE)
        print(self.CSI + style + self.CSI + '{};{}H{}'.format(self.lastRow, 1, info), end='')
        Tabs.clearRow(arg=0, file=self.outFile)
        self.resetPos()
        if x: exit()
    
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
        n = notes.Note(self.getNoteIndex(str, chfret), self.enharmonic)
        print('getHarmonicNote({}, {}) f={}, hf={}, chf={}, n.i={}, n.n={}, n.o={})'.format(str, tab, fret, hfret, chfret, n.index, n.name, n.getOctaveNum()), file=Tabs.DBG_FILE)
        return n
    
    def getNoteIndex(self, str, f):
        '''Converts string numbering from 1 based with str=1 denoting the high E first string and str=numStrings the low E sixth string.'''
        s = self.numStrings - str                     # Reverse and zero base the string numbering: str[1 ... numStrings] => s[(numStrings - 1) ... 0]
        i = self.stringMap[self.stringKeys[s]] + f    # calculate the fretted note index using the sorted map
#        print('getNoteIndex() str={}, s={}, f={}, i={}, sk={}, sm={}'.format(str, s, f, i, self.stringKeys[s], self.stringMap[self.stringKeys[s]]), file=Tabs.DBG_FILE)
        return i
    
    def printChord(self, c=None, dbg=0):
        '''Analyse the notes at the given column and if they form a chord print the chord in the chords section.'''
        self.chordsObj.printChord(c, dbg)
    
    def isTab(self, c):
        if c == '-' or Tabs.isFret(c) or self.isMod(c): return True
        return False
    
    def isMod(self, c):
        if c in self.mods: return True
        return False
    
    @staticmethod
    def isFret(c):
        if '0' <= c <= '9' or 'a' <= c <= 'o': return True
        return False
    
    @staticmethod
    def getFretNum(fretByte):
        fretNum = fretByte - ord('0')
        if fretByte >= ord('a'): fretNum = fretByte - (ord('a') - 10)
        return fretNum
    
#    @staticmethod
    def getFretByte(self, fretNum):
        fretByte = fretNum + ord('0')
        if 10 <= fretNum <= self.NUM_FRETS: fretByte = fretNum + ord('a') - 10
        return fretByte
    
    @staticmethod
    def getOrdSfx(n):
        m = n % 10
        if   m == 1 and n != 11: return 'st'
        elif m == 2 and n != 12: return 'nd'
        elif m == 3 and n != 13: return 'rd'
        else:                    return 'th'
    
    @staticmethod
    def clearRow(arg=2, row=None, col=None, file=None): # arg=0: cursor to end of line, arg=1: begin of line to cursor, arg=2: entire line 
        print('clearRow() arg={} row={}, col={}'.format(arg, row, col), file=Tabs.DBG_FILE)
        if row is not None and col is not None:
            print(Tabs.CSI + '{};{}H'.format(row, col), end='', file=file)
        print(Tabs.CSI + '{}K'.format(arg), end='', file=file)
    
    @staticmethod
    def clearScreen(arg=2, file=None, reason=None):
        print('clearScreen() arg={} file={} reason={}'.format(arg, file, reason), file=Tabs.DBG_FILE)
        print(Tabs.CSI + '{}J'.format(arg), file=file)
    
    def printHelpSummary(self):
        summary = \
        '''
Note the console window should be at least as wide as the number of tabs + 2.  Window resizing is not supported.  
The command line arg -t sets the number of tabs per string per line.  
The command line arg -f sets the file name to read from and write to.  
The command line arg -s sets the spelling of the string names e.g. -s 'E2A2D3G3B3E4' is 6 string standard guitar tuning.  
The command line arg -S sets the spelling of the string names via an alias e.g. -s 'GUITAR' is 6 string standard guitar tuning.  
The command line arg -k sets the fret to place the capo at [0-9], [a-o].  
The command line arg -i sets the automatic cursor advance direction is downward rather than upward.  
The command line arg -F sets the use of flat enharmonic notes instead of sharp enharmonic notes.  
The command line arg -a enables display of the optional label row and the cursor and edit modes.  
The command line arg -n enables display of the optional notes section.  
The command line arg -o enables display of the optional intervals section.  
The command line arg -b enables display of the optional chords section.
The command line arg -l moves the cursor to the last tab on the current line of the current string  
The command line arg -L moves the cursor to the last tab on the current line of all strings  
The command line arg -z moves the cursor to the last tab on the last line of the current string  
The command line arg -Z moves the cursor to the last tab on the last line of all strings  
The command line arg -h enables display of this help info.  

Tabs are displayed in the tabs section with an optional row to label and highlight the selected tab column.  
An optional notes section and an optional chords section can also be displayed below the tabs section.  
A number of lines can be displayed where each line has its own tabs, notes, intervals, and chords sections.  
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
''' + self.hilite('Intervals section:  \'Ctrl B\'') + ''' 
The intervals section has the same number of rows and columns as the tabs section and displays the note intervals corresponding to the chord in the chords section.  
The intervals section uses the color red to indicate a sharp interval and blue to represent a flat interval.  
''' + self.hilite('Chords section:  \'Ctrl B\'') + ''' 
Chords are spelled vertically so that they line up with the tabs and notes and potentially every column can display a chord.  
Chord names are automatically calculated and recalculated whenever the number of tabs in a given column is greater than one.  
The maximum chord name length is set to 5 and is not currently configurable.
The chords section also uses red to indicate a sharp chord and blue to represent a flat chord, but only on the first character, the root note.  
Minor and diminished chords use the color blue for the 'm' or the 'dim' characters.  

Note the tabs, notes, and chords can be saved to a file and if you 'cat' the file you can see the ANSI colors.  
        '''
        print(summary, file=Tabs.DBG_FILE)
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
| -- Capo fret numbers (0 means no capo)
---- String numbers and String note names
 
Desired new features list:
    Optimize printTabs?
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
    
    Consider chords without a root note (C# E G B -> A9)?
    Consider using color coded chord types on the 2nd chord character (omit m and or M): white for none, blue for m, red for M, magenta for mM)
'''

'''
Colorama doc
ESC [ y;x H     # position cursor at x across, y down
ESC [ y;x f     # position cursor at x across, y down
ESC [ n A       # move cursor n lines up
ESC [ n B       # move cursor n lines down
ESC [ n C       # move cursor n characters forward
ESC [ n D       # move cursor n characters backward
'''
#117, 119 CTRL END, CTRL HOME
#159, 151 ALT END, ALT HOME
#118, 134 CTRL DOWN, CTRL UP
#161, 153 ALT DOWN, ALT UP 

# python tabs.py -anb -t 208 -f data/208/SDan/DoItAgain.tab
# 211 x 73 @ 16 Lucida Sans Typewriter
