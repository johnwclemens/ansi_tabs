'''tabs.py module.  Main entry point, class list: [Tabs].  Note main simply instantiates an instance of the Tabs class which handles the entire session.'''

'''Thus all methods are essentially private.  Note some functionality is deemed customizable by the user and is thus factored out into a separate module.  
e.g. The tab modifications are in mods.py, the string tunings and aliases are in strings.py, and the chord discovery and name calculations are in chords.py.'''

import os, sys, shutil

impFile = open('tabs_imp.log', 'w')

'''Lame attempt at portability.  Should work on Windows, might work on Linux'''
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
    '''Model musical tab notation and tab editor functionality'''
    ESC = '\033'
    CSI = '\033\133'
    DBG_NAME = "Debug.txt"
    DBG_FILE = open(DBG_NAME, "w")
    
    def __init__(self, inName='tabs.tab', outName='tabs.tab'):
        '''Initialize the Tabs object and start the user interactive console command loop method'''
        self.init(inName, outName)
        self.loop()
    
    def init(self, inName='tabs.tab', outName='tabs.tab'):
        '''Init class instance, enable automatic reset of console via print(colorama.Style.RESET_ALL)'''
        cnt = sys.stdout.write('init() before colorama.int()')
        print('init() cnt={} type(sys.stdout)={}'.format(cnt, type(sys.stdout)), file=Tabs.DBG_FILE)
        colorama.init(autoreset=True)
        cnt = sys.stdout.write('init() after colorama.int()')
        print('init() cnt={} type(sys.stdout)={}'.format(cnt, type(sys.stdout)), file=Tabs.DBG_FILE)

        Tabs.clearScreen()
        self.initFiles(inName, outName)
        self.initConsts()
        self.registerUiCmds()                                       # register the dictionary for all the user interactive commands
        self.cmds = []                                              # list of user interactive cmd history
        self.cmdsIndex = None                                       # cmd history index
        self.errors = []                                            # list of error message history
        self.errorsIndex = None                                     # error history index
        self.mods = {}                                              # dict of tab modification characters -> contextual descriptions
        self.txts = {}                                              # same as mods, except with ANSI codes removed
        self.capo = ord('0')                                        # essentially added to every tab that is a fret, written to the outFile and read from the inFile
        self.maxFretInfo = {'MAX':0, 'LINE':-1, 'STR':-1, 'COL':-1} # dict -> max fret info (max, line, row, col)
        self.chordsObj = None                                       # the chords.Chords instance
        self.dbgMove = 1                                            # used for finding bugs in basic movement functionality
        self.cmdFilterStr = 'None:'
        self.filterCmds = 1
        
        self.htabs = []                                             # list of bytearrays, one for each string; for harmonic tabs
        self.tabCount = 0                                           # used by appendTabs()
        self.tabs = []                                              # list of bytearrays, one for each string; for all the tabs
        self.chordInfo = {}                                         # dict column index -> (list of dict intervals -> note names) i.e. dict col -> list of imaps for status chord info
        self.selectChords = {}                                      # dict chord name -> imap, for displaying the selected chord name and imap
        self.selectImaps = {}                                       # dict imap string -> imap, for displaying intervals corresponding to selected chord name & imap
        self.chordAliases = {}                                      # dict column index -> chord names
        self.analyzeIndices = {}                                    # dict column index -> imap index being analyzed for chord info
        self.chordStatusCol = None                                  # tab column index used to display chord info on status row
        self.selectChordAliases = {}                                # dict column index -> chord names, temp storage for cut & paste
        self.selectAnalyzeIndices = {}                              # dict column index -> chordInfo index, temp storage for cut & paste
        
        self.arpeggiate = 0                                         # used to transform chords to arpeggios
        self.selectFlag = 0                                         # used to un-hilite selected rows
        self.selectTabs = []                                        # list of bytearrays, one for each string; for selected tabs
        self.selectHTabs = []                                       # list of bytearrays, one for each string; for selected tabs
        self.selectRows = []                                        # list of row    indices, one for each selected row;    for selected rows
        self.selectCols = []                                        # list of column indices, one for each selected column; for selected columns
        self.stringMap = {}                                         # dict of string note name -> note index
        self.stringKeys = []                                        # list of keys; stringMap keys sorted by note index
        self.numStrings = 1                                         # number of strings on the musical instrument, set here in case initStrings() fails
        
        self.numLines = 1                                           # number of music lines to display
        self.numTabsPerStringPerLine = 10                           # number of tabs to display on each line (for each string)
        self.numTabsPerString = self.numLines * self.numTabsPerStringPerLine  # total number of tabs per string
        
        self.ROW_OFF = 1                                            # offset between cursor row    number and tabs row    index
        self.COL_OFF = 3                                            # offset between cursor column number and tabs column index
        self.NOTES_LEN = 0                                          # number of rows used to display notes  on a given line
        self.INTERVALS_LEN = 0                                      # number of rows used to display intervals on a given line
        self.CHORDS_LEN = 0                                         # number of rows used to display chords on a given line
        self.NUM_FRETS = 24                                         # number of frets (might make this a list for each string)?
        self.IVAL_LABEL = 'INTRVL'                                  # label displayed for intervals (first col)
        
        self.hiliteCount = 0                                        # statistic for measuring efficiency
        self.hiliteColNum = 0                                       # used to hilite the current cursor column and unhilite the previous cursor column
        self.hiliteRowNum = 0                                       # used to hilite the current cursor row    and unhilite the previous cursor row
        self.hilitePrevRowPos = 0
        self.row = self.ROW_OFF                                     # current cursor row    number
        self.col = self.COL_OFF                                     # current cursor column number
        self.editModeCol = 1                                        # column to display edit  mode
        self.cursorModeCol = 2                                      # column to display cursor mode
        self.lastRow = self.ROW_OFF + self.numLines * self.lineDelta() - 1  # row used to display status, set here in case initStrings() fails e.g. tab mod info or error info etc...
        
        self.displayLabels = self.DISPLAY_LABELS['DISABLED']        # enable or disable the display of the modes and labels section before each line
        self.displayNotes = self.DISPLAY_NOTES['DISABLED']          # enable or disable the display of the notes section for each line
        self.displayIntervals = self.DISPLAY_INTERVALS['DISABLED']  # enable or disable the display of the intervals section for each line
        self.displayChords = self.DISPLAY_CHORDS['DISABLED']        # enable or disable the display of the chords section for each line
        self.cursorDir = self.CURSOR_DIRS['DOWN']                   # affects the automatic cursor movement (up or down) when entering a tab in chord or arpeggio mode
        self.enharmonic = self.ENHARMONICS['SHARP']                 # select enharmonic notes as flat or sharp
        self.editMode = self.EDIT_MODES['REPLACE']                  # select insert mode as insert or replace
        self.cursorMode = self.CURSOR_MODES['MELODY']               # select cursor mode as melody, arpeggio or chord
        self.cursorDirStyle = self.styles['NUT_DN']                 # select cursor direction as up or down (displayed on capo/nut)
        self.testAscii()
        
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
            if os.path.isfile(self.outName):
                print('saving backup file: {}'.format(backupName), file=Tabs.DBG_FILE)
                shutil.copy2(self.outName, backupName)
        if 't' in self.argMap and len(self.argMap['t']) > 0:
            self.initTabLen(self.argMap['t'])                       # set number of tabs/columns per line (and per string)
        if 'S' in self.argMap and len(self.argMap['S']) > 0:
            self.initStrings(alias=self.argMap['S'])                # set string tuning with alias
        elif 's' in self.argMap and len(self.argMap['s']) > 0:
            self.initStrings(spelling=self.argMap['s'])             # set string tuning with string spelling
        else:
            self.initStrings()                                      # set default string tuning
        self.setLastRow()                                           # calculate last row, depends on numStrings which is supposed to be set in initStrings()
        self.numTabs = self.numStrings * self.numTabsPerString      # total number of tab characters
        self.tests()
#        self.testList()
        
        try:
            with open(self.inName, 'rb') as self.inFile:
                self.readTabs(readSize=8192)
        except FileNotFoundError as e: #Exception as e:
            print('init() Exception: {} - {}'.format(e, sys.exc_info()[0]), file=Tabs.DBG_FILE)
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
            self.txts = self.modsObj.getTxts()
            print('init() txts=\{ ', file=Tabs.DBG_FILE)
            for k in self.txts:
                print('{}:{}, '.format(k, self.txts[k]), file=Tabs.DBG_FILE)
            if 'help' in self.argMap and len(self.argMap['help']) == 0: self.printHelpInfo(ui=0)      # display the help info
            if '?' in self.argMap and len(self.argMap['?']) == 0: self.printHelpInfo(ui=0)            # display the help info
            if 'h' in self.argMap and len(self.argMap['h']) == 0: self.printHelpInfo(ui=0)            # display the help info
            if 'k' in self.argMap and len(self.argMap['k'])  > 0: self.setCapo(c=self.argMap['k'][0]) # set capo at desired fret
            if 'F' in self.argMap and len(self.argMap['F']) == 0: self.toggleEnharmonic()             # enharmonic notes displayed as sharp or flat
            if 'i' in self.argMap and len(self.argMap['i']) == 0: self.toggleCursorDir(dbg=1)         # automatic cursor movement direction as down or up
            if 'a' in self.argMap and len(self.argMap['a']) == 0: self.toggleDisplayLabels(pt=0)      # display edit mode, cursor mode, and column numbers
            if 'b' in self.argMap and len(self.argMap['b']) == 0: self.toggleDisplayChords(pt=0)      # chords display section
            if 'I' in self.argMap and len(self.argMap['I']) == 0: self.toggleDisplayIntervals(pt=0)   # intervals display section
            if 'n' in self.argMap and len(self.argMap['n']) == 0: self.toggleDisplayNotes(pt=0)       # notes display section
            if 'D' in self.argMap and len(self.argMap['D'])  > 0: self.toggleBrightness(pt=0, bi=int(self.argMap['D'][0])) # color scheme
            if 'U' in self.argMap and len(self.argMap['U'])  > 0: self.toggleColors(pt=0,     ci=int(self.argMap['U'][0])) # brightness
            if 'l' in self.argMap and len(self.argMap['l']) == 0: self.goToLastTab(cs=1)              # go to last tab on current line of current string
            if 'L' in self.argMap and len(self.argMap['L']) == 0: self.goToLastTab()                  # go to last tab on current line of all strings
            if 'z' in self.argMap and len(self.argMap['z']) == 0: self.goToLastTab(cs=1, ll=1)        # go to last tab on last line of current string
            if 'Z' in self.argMap and len(self.argMap['Z']) == 0: self.goToLastTab(ll=1)              # go to last tab on last line of all strings
            parse1, data1 = self.parseStateData(self.chordAliases, 'StartChordAliases')
            parse2, data2 = self.parseStateData(self.analyzeIndices, 'StartAnalyzeIndices')
            if parse1 and parse2:
                self.chordAliases = data1
                self.analyzeIndices = data2
                print('init() chordAliases(len={})={}'.format(len(self.chordAliases), self.chordAliases), file=Tabs.DBG_FILE)
                print('init() analyzeIndices(len={})={}'.format(len(self.analyzeIndices), self.analyzeIndices), file=Tabs.DBG_FILE)
                for c in self.chordAliases:
                    print('init() calling moveToCol({}) printChord({}) & selectChord()'.format(c, c), file=Tabs.DBG_FILE)
                    self.moveToCol(c)
                    self.chordsObj.printChord(c, pc=0)           # need to populate chordInfo before calling selectChord
                    self.selectChord(pt=0)
            self.printTabs()                                     # display the tabs, notes, intervals, and chords sections and the modes/labels row
            self.moveTo(self.ROW_OFF, self.COL_OFF, hi=1)        # display the status and hilite the first tab character
            self.printh('{}: {}'.format('?', self.printHelpInfo.__doc__))
    
    def parseStateData(self, data, dataType):
        try:
            parsed = 0
            with open(self.inName, 'r') as self.inFile:
                for line in self.inFile:
                    if line.strip() == dataType:
                        print('parseStateData() bgn parsing {}'.format(dataType), file=Tabs.DBG_FILE)
                        parsed = 1
                        break
                    if line.strip() == '<BGN_TABS_SECTION>':
                        self.printe('parseStateData() Error parsing dataType={} inFile={}'.format(dataType, self.inFile.name))
                        break
                print('parseStateData() break out of dataType={} for loop parsed={}'.format(dataType, parsed), file=Tabs.DBG_FILE)
                if parsed == 1:
                    line = self.inFile.readline().strip()
                    print('parseStateData() parsed dataType={} = {}'.format(dataType, line), file=Tabs.DBG_FILE)
                    data = eval(line)
                    print('parseStateData() type(data) = {}'.format(type(data)), file=Tabs.DBG_FILE)
        except Exception as e: self.printe('parseStateData({}) Exception: Error parsing inFile={}'.format(e, self.inFile))
        return isinstance(data, dict), data
    
    def testDict(self):
        a = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5}
        b = dict(one=1, two=2, three=3, four=4, five=5)
        c = dict(zip(['one', 'two', 'three', 'four', 'five'], [1, 2, 3, 4, 5]))
        d = dict([('two', 2), ('one', 1), ('three', 3), ('four', 4), ('five', 5)])
        e = dict({'three': 3, 'one': 1, 'four': 4, 'five': 5, 'two': 2})
        print('a={}'.format(a), file=Tabs.DBG_FILE)
        print('b={}'.format(b), file=Tabs.DBG_FILE)
        print('c={}'.format(c), file=Tabs.DBG_FILE)
        print('d={}'.format(d), file=Tabs.DBG_FILE)
        print('e={}'.format(e), file=Tabs.DBG_FILE)
        m = collections.OrderedDict(sorted(a.items(), key=lambda t: t[0])) #one=1, two=2, three=3)
        print('m={} sorted(a.items(), key=lambda t: t[0])'.format(m), file=Tabs.DBG_FILE)
        m['two'] = 2
        m['three'] = 3
        m = collections.OrderedDict(sorted(a.items(), key=lambda t: t[1]))
        print('m={} sorted(a.items(), key=lambda t: t[1])'.format(m), file=Tabs.DBG_FILE)
        exit()
    
    def testList(self):
        a = [1, 2, 3, [1, 2, 3], 4, 5]
        print('testList() a={}'.format(a), file=Tabs.DBG_FILE)
        b = [e for e in reversed(a)]
        print('testList() b={}'.format(b), file=Tabs.DBG_FILE)
        exit()
    
    def testAscii(self):
        print('testAscii()', file=Tabs.DBG_FILE)
        for i in range(0, 128): print('    {}({})'.format(i, chr(i)), file=Tabs.DBG_FILE)
    
    def testAnsi(self):
        print(Tabs.CSI + self.styles['TABS']       + Tabs.CSI + '{};{}H{}'.format(1, 1, 'TABS'), file=file)
        print(Tabs.CSI + self.styles['H_TABS']     + Tabs.CSI + '{};{}H{}'.format(1, 20, 'H_TABS!'), file=file)
        print(Tabs.CSI + self.styles['NAT_NOTE']   + Tabs.CSI + '{};{}H{}'.format(2, 1, 'NAT_NOTE'), file=file)
        print(Tabs.CSI + self.styles['NAT_H_NOTE'] + Tabs.CSI + '{};{}H{}'.format(2, 20, 'NAT_H_NOTE'), file=file)
        print(Tabs.CSI + self.styles['FLT_NOTE']   + Tabs.CSI + '{};{}H{}'.format(3, 1, 'FLT_NOTE'), file=file)
        print(Tabs.CSI + self.styles['FLT_H_NOTE'] + Tabs.CSI + '{};{}H{}'.format(3, 20, 'FLT_H_NOTE'), file=file)
        print(Tabs.CSI + self.styles['SHP_NOTE']   + Tabs.CSI + '{};{}H{}'.format(4, 1, 'SHP_NOTE'), file=file)
        print(Tabs.CSI + self.styles['SHP_H_NOTE'] + Tabs.CSI + '{};{}H{}'.format(4, 20, 'SHP_H_NOTE'), file=file)
        exit()
    
    def testAnsi2(self):
        print(Tabs.CSI + '22;30;47m' + Tabs.CSI + '{};{}H{}'.format( 1, 1, 'Normal Black   on White'))
        print(Tabs.CSI +  '1;30;47m' + Tabs.CSI + '{};{}H{}'.format( 2, 1, 'Bright Black   on White'))
        print(Tabs.CSI + '22;31;47m' + Tabs.CSI + '{};{}H{}'.format( 3, 1, 'Normal Red     on White'))
        print(Tabs.CSI +  '1;31;47m' + Tabs.CSI + '{};{}H{}'.format( 4, 1, 'Bright Red     on White'))
        print(Tabs.CSI + '22;32;47m' + Tabs.CSI + '{};{}H{}'.format( 5, 1, 'Normal Green   on White'))
        print(Tabs.CSI +  '1;32;47m' + Tabs.CSI + '{};{}H{}'.format( 6, 1, 'Bright Green   on White'))
        print(Tabs.CSI + '22;33;47m' + Tabs.CSI + '{};{}H{}'.format( 7, 1, 'Normal Yellow  on White'))
        print(Tabs.CSI +  '1;33;47m' + Tabs.CSI + '{};{}H{}'.format( 8, 1, 'Bright Yellow  on White'))
        print(Tabs.CSI + '22;34;47m' + Tabs.CSI + '{};{}H{}'.format( 9, 1, 'Normal Blue    on White'))
        print(Tabs.CSI +  '1;34;47m' + Tabs.CSI + '{};{}H{}'.format(10, 1, 'Bright Blue    on White'))
        print(Tabs.CSI + '22;35;47m' + Tabs.CSI + '{};{}H{}'.format(11, 1, 'Normal Magenta on White'))
        print(Tabs.CSI +  '1;35;47m' + Tabs.CSI + '{};{}H{}'.format(12, 1, 'Bright Magenta on White'))
        print(Tabs.CSI + '22;36;47m' + Tabs.CSI + '{};{}H{}'.format(13, 1, 'Normal Cyan    on White'))
        print(Tabs.CSI +  '1;36;47m' + Tabs.CSI + '{};{}H{}'.format(14, 1, 'Bright Cyan    on White'))
        
        print(Tabs.CSI + '22;37;40m' + Tabs.CSI + '{};{}H{}'.format(15, 1, 'Normal White   on Black'))
        print(Tabs.CSI +  '1;37;40m' + Tabs.CSI + '{};{}H{}'.format(16, 1, 'Bright White   on Black'))
        print(Tabs.CSI + '22;31;40m' + Tabs.CSI + '{};{}H{}'.format(17, 1, 'Normal Red     on Black'))
        print(Tabs.CSI +  '1;31;40m' + Tabs.CSI + '{};{}H{}'.format(18, 1, 'Bright Red     on Black'))
        print(Tabs.CSI + '22;32;40m' + Tabs.CSI + '{};{}H{}'.format(19, 1, 'Normal Green   on Black'))
        print(Tabs.CSI +  '1;32;40m' + Tabs.CSI + '{};{}H{}'.format(20, 1, 'Bright Green   on Black'))
        print(Tabs.CSI + '22;33;40m' + Tabs.CSI + '{};{}H{}'.format(21, 1, 'Normal Yellow  on Black'))
        print(Tabs.CSI +  '1;33;40m' + Tabs.CSI + '{};{}H{}'.format(22, 1, 'Bright Yellow  on Black'))
        print(Tabs.CSI + '22;34;40m' + Tabs.CSI + '{};{}H{}'.format(23, 1, 'Normal Blue    on Black'))
        print(Tabs.CSI +  '1;34;40m' + Tabs.CSI + '{};{}H{}'.format(24, 1, 'Bright Blue    on Black'))
        print(Tabs.CSI + '22;35;40m' + Tabs.CSI + '{};{}H{}'.format(25, 1, 'Normal Magenta on Black'))
        print(Tabs.CSI +  '1;35;40m' + Tabs.CSI + '{};{}H{}'.format(26, 1, 'Bright Magenta on Black'))
        print(Tabs.CSI + '22;36;40m' + Tabs.CSI + '{};{}H{}'.format(27, 1, 'Normal Cyan    on Black'))
        print(Tabs.CSI +  '1;36;40m' + Tabs.CSI + '{};{}H{}'.format(28, 1, 'Bright Cyan    on Black'))
        exit()
    
    def testAnsi3(self):
        print(Tabs.CSI + '22;37;40m' + Tabs.CSI + '0B' + Tabs.CSI +  '0D' + 'Normal White on Black',   end='')
        print(Tabs.CSI +  '1;37;40m' + Tabs.CSI + '1B' + Tabs.CSI + '21D' + 'Bright White on Black',   end='')
        print(Tabs.CSI + '22;37;41m' + Tabs.CSI + '1B' + Tabs.CSI +  '0D' + 'Normal White on Red',     end='')
        print(Tabs.CSI +  '1;37;41m' + Tabs.CSI + '1B' + Tabs.CSI + '19D' + 'Bright White on Red',     end='')
        print(Tabs.CSI + '22;37;42m' + Tabs.CSI + '1B' + Tabs.CSI +  '0D' + 'Normal White on Green',   end='')
        print(Tabs.CSI +  '1;37;42m' + Tabs.CSI + '1B' + Tabs.CSI + '21D' + 'Bright White on Green',   end='')
        print(Tabs.CSI + '22;37;43m' + Tabs.CSI + '1B' + Tabs.CSI +  '0D' + 'Normal White on Yellow',  end='')
        print(Tabs.CSI +  '1;37;43m' + Tabs.CSI + '1B' + Tabs.CSI + '22D' + 'Bright White on Yellow',  end='')
        print(Tabs.CSI + '22;37;44m' + Tabs.CSI + '1B' + Tabs.CSI +  '0D' + 'Normal White on Blue',    end='')
        print(Tabs.CSI +  '1;37;44m' + Tabs.CSI + '1B' + Tabs.CSI + '20D' + 'Bright White on Blue',    end='')
        print(Tabs.CSI + '22;37;45m' + Tabs.CSI + '1B' + Tabs.CSI +  '0D' + 'Normal White on Magenta', end='')
        print(Tabs.CSI +  '1;37;45m' + Tabs.CSI + '1B' + Tabs.CSI + '23D' + 'Bright White on Magenta', end='')
        print(Tabs.CSI + '22;37;46m' + Tabs.CSI + '1B' + Tabs.CSI +  '0D' + 'Normal White on Cyan',    end='')
        print(Tabs.CSI +  '1;37;46m' + Tabs.CSI + '1B' + Tabs.CSI + '20D' + 'Bright White on Cyan',    end='')
        self.quit(reason='testAnsi3()', code=4)
    
    def testStruct(self):
        s = {}
        limap = [{'R':'A', 'm3':'C', '5':'E'}, {'R':'C', 'M3':'E', '6':'A'}, {'R':'E', '4':'A', 'a5':'C'}]
        chords = ['Am', 'C6n5', '']
        s[0] = {'INDEX':1, 'CHORDS':chords, 'LIMAP':limap}
        limap = [{'R':'A', 'm3':'C', '5':'E', 'b7':'G'}, {'R':'C', 'M3':'E', '5':'G', '6':'A'}, {'R':'E', 'm3':'G', '4':'A', 'a5':'C'}, {'R':'G', '2':'A', '4':'C', '6':'E'}]
        chords = ['Am7', 'C6', '', '']
        s[2] = {'INDEX':2, 'CHORDS':chords, 'LIMAP':limap}
        print('testStruct() s={}'.format(s), file=Tabs.DBG_FILE)
        index = s[0]['INDEX']
        limap = s[0]['LIMAP']
        chords = s[0]['CHORDS']
        print('testStruct() index={} chords={} limap={}'.format(index, chords, limap), file=Tabs.DBG_FILE)
        imap = s[0]['LIMAP'][index]
        chord = s[0]['CHORDS'][index]
        print('testStruct() index={} chord={} imap={}'.format(index, chord, imap), file=Tabs.DBG_FILE)
        self.dumpLimap(s[0]['LIMAP'], reason='testStruct()')
        self.dumpChordInfo(s, reason='testStruct()')
    
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
        self.WHITE_YELLOW = self.initText('WHITE', 'YELLOW')
        self.BLACK_YELLOW = self.initText('BLACK', 'YELLOW')
        self.GREEN_YELLOW = self.initText('GREEN', 'YELLOW')
        self.BLUE_YELLOW = self.initText('BLUE', 'YELLOW')
        self.CYAN_YELLOW = self.initText('CYAN', 'YELLOW')
        self.RED_YELLOW = self.initText('RED', 'YELLOW')
        self.WHITE_BLUE = self.initText('WHITE', 'BLUE')
        self.WHITE_BLACK = self.initText('WHITE', 'BLACK')
        self.YELLOW_BLACK = self.initText('YELLOW', 'BLACK')
        self.RED_BLACK = self.initText('RED', 'BLACK')
        self.BLUE_BLACK = self.initText('BLUE', 'BLACK')
        self.GREEN_BLACK = self.initText('GREEN', 'BLACK')
        self.CYAN_BLACK = self.initText('CYAN', 'BLACK')
        self.MAGENTA_BLACK = self.initText('MAGENTA', 'BLACK')
        self.MAGENTA_GREEN = self.initText('MAGENTA', 'GREEN')
        self.WHITE_GREEN = self.initText('WHITE', 'GREEN')
        self.RED_GREEN = self.initText('RED', 'GREEN')
        self.BLUE_GREEN = self.initText('BLUE', 'GREEN')
        self.BLACK_GREEN = self.initText('BLACK', 'GREEN')
        self.WHITE_MAGENTA = self.initText('WHITE', 'MAGENTA')
        self.BLACK_MAGENTA = self.initText('BLACK', 'MAGENTA')
        self.BLACK_RED = self.initText('BLACK', 'RED')
        self.WHITE_RED = self.initText('WHITE', 'RED')
        self.CYAN_RED = self.initText('CYAN', 'RED')
        self.BLACK_CYAN = self.initText('BLACK', 'CYAN')
        self.BLUE_CYAN = self.initText('BLUE', 'CYAN')
        self.WHITE_CYAN = self.initText('WHITE', 'CYAN')
        self.RED_CYAN = self.initText('RED', 'CYAN')
        self.colorsIndex = 0
        self.brightness = 0
        self.initColors()
        self.initBrightness()
        self.HARMONIC_FRETS = { 12:12, 7:19, 19:19, 5:24, 24:24, 4:28, 9:28, 16:28, 28:28 }
        self.CURSOR_DIRS = { 'DOWN':0, 'UP':1 }
        self.CURSOR_MODES = { 'MELODY':0, 'CHORD':1, 'ARPEGGIO':2 }
        self.EDIT_MODES = { 'REPLACE':0, 'INSERT':1 }
        self.ENHARMONICS = { 'FLAT':0, 'SHARP':1 }
        self.DISPLAY_LABELS = { 'DISABLED':0, 'ENABLED':1 }
        self.DISPLAY_NOTES = { 'DISABLED':0, 'ENABLED':1 }
        self.DISPLAY_INTERVALS = { 'DISABLED':0, 'ENABLED':1 }
        self.DISPLAY_CHORDS = { 'DISABLED':0, 'ENABLED':1 }
    
    def initBrightness(self):
        print('initBrightness() brightness={}'.format(self.brightness), file=Tabs.DBG_FILE)
        if   self.brightness == 0:
            self.brightnessA, self.brightnessB, self.bStyle = self.styles['NORMAL'], self.styles['BRIGHT'], self.styles['NORMAL']
        elif self.brightness == 1:
            self.brightnessA, self.brightnessB, self.bStyle = self.styles['BRIGHT'], self.styles['NORMAL'], self.styles['BRIGHT']
        else: self.printe('initBrightness() brightness={} our of range [0-1]'.format(self.brightness))
    
    def initColors(self):
        print('initColors() colorsIndex={}'.format(self.colorsIndex), file=Tabs.DBG_FILE)
        if   self.colorsIndex == 0:
            self.styles = { 'NAT_NOTE':self.GREEN_WHITE,    'NAT_H_NOTE':self.YELLOW_WHITE,  'NAT_IVAL':self.YELLOW_WHITE,  'NAT_CHORD':self.BLACK_WHITE,    'TABS':self.RED_WHITE,
                            'FLT_NOTE':self.BLUE_WHITE,     'FLT_H_NOTE':self.CYAN_WHITE,    'FLT_IVAL':self.CYAN_WHITE,    'FLT_CHORD':self.CYAN_WHITE,   'H_TABS':self.CYAN_WHITE,
                            'SHP_NOTE':self.RED_WHITE,      'SHP_H_NOTE':self.MAGENTA_WHITE, 'SHP_IVAL':self.RED_WHITE,     'SHP_CHORD':self.MAGENTA_WHITE, 'MODES':self.BLUE_WHITE,
                              'NUT_UP':self.WHITE_MAGENTA, 'MIN_COL_NUM':self.RED_WHITE,   'IVAL_LABEL':self.MAGENTA_WHITE,    'STATUS':self.MAGENTA_WHITE, 'ERROR':self.WHITE_RED,
                              'NUT_DN':self.WHITE_CYAN,    'MAJ_COL_NUM':self.BLUE_WHITE, 'CHORD_LABEL':self.GREEN_WHITE,    'HLT_STUS':self.GREEN_WHITE,    'CONS':self.BLACK_WHITE,
                             'NO_IVAL':self.BLACK_WHITE,     'MOD_DELIM':self.YELLOW_WHITE,    'NORMAL':'22;',                 'BRIGHT':'1;' }
        elif self.colorsIndex == 1:
            self.styles = { 'NAT_NOTE':self.BLACK_GREEN,    'NAT_H_NOTE':self.WHITE_YELLOW,  'NAT_IVAL':self.BLACK_YELLOW,  'NAT_CHORD':self.BLACK_CYAN,     'TABS':self.GREEN_WHITE,
                            'FLT_NOTE':self.BLUE_GREEN,     'FLT_H_NOTE':self.WHITE_CYAN,    'FLT_IVAL':self.BLUE_YELLOW,   'FLT_CHORD':self.BLUE_CYAN,    'H_TABS':self.WHITE_GREEN,
                            'SHP_NOTE':self.MAGENTA_GREEN,  'SHP_H_NOTE':self.WHITE_MAGENTA, 'SHP_IVAL':self.RED_YELLOW,    'SHP_CHORD':self.RED_CYAN,      'MODES':self.WHITE_BLUE,
                              'NUT_UP':self.WHITE_RED,     'MIN_COL_NUM':self.BLACK_CYAN,  'IVAL_LABEL':self.BLACK_YELLOW,     'STATUS':self.BLACK_YELLOW,  'ERROR':self.WHITE_RED,
                              'NUT_DN':self.WHITE_BLUE,    'MAJ_COL_NUM':self.RED_CYAN,   'CHORD_LABEL':self.BLACK_CYAN,     'HLT_STUS':self.BLACK_GREEN,    'CONS':self.BLACK_WHITE,
                             'NO_IVAL':self.WHITE_CYAN,      'MOD_DELIM':self.BLACK_CYAN,      'NORMAL':'22;',                 'BRIGHT':'1;' }
        elif self.colorsIndex == 2:
            self.styles = { 'NAT_NOTE':self.GREEN_BLACK,    'NAT_H_NOTE':self.YELLOW_BLACK,    'NAT_IVAL':self.YELLOW_BLACK,  'NAT_CHORD':self.GREEN_BLACK,    'TABS':self.CYAN_BLACK,
                            'FLT_NOTE':self.BLUE_BLACK,     'FLT_H_NOTE':self.CYAN_BLACK,      'FLT_IVAL':self.CYAN_BLACK,    'FLT_CHORD':self.BLUE_BLACK,   'H_TABS':self.GREEN_BLACK,
                            'SHP_NOTE':self.RED_BLACK,      'SHP_H_NOTE':self.MAGENTA_BLACK,   'SHP_IVAL':self.RED_BLACK,     'SHP_CHORD':self.RED_BLACK,     'MODES':self.CYAN_BLACK,
                              'NUT_UP':self.MAGENTA_BLACK, 'MIN_COL_NUM':self.RED_BLACK,     'IVAL_LABEL':self.YELLOW_BLACK,     'STATUS':self.MAGENTA_BLACK, 'ERROR':self.RED_BLACK,
                              'NUT_DN':self.WHITE_BLACK,   'MAJ_COL_NUM':self.YELLOW_BLACK, 'CHORD_LABEL':self.GREEN_BLACK,    'HLT_STUS':self.GREEN_BLACK,    'CONS':self.WHITE_BLACK,
                             'NO_IVAL':self.WHITE_BLACK,     'MOD_DELIM':self.BLUE_BLACK,        'NORMAL':'22;',                 'BRIGHT':'1;' }
        else: self.printe('initColors() colorsIndex={} out of range [0-2]'.format(self.colorsIndex))
    def initText(self, FG, BG):
        return '3' + self.COLORS[FG] + ';4' + self.COLORS[BG] + 'm'
    
    def initStrings(self, alias=None, spelling=None):
        print('initStrings(alias={}, spelling={})'.format(alias, spelling), file=Tabs.DBG_FILE)
        try:
            self.strings = strings.Strings(Tabs.DBG_FILE, alias=alias, spelling=spelling)
        except Exception as ex:
            e = sys.exc_info()[0]
            self.quit('initStrings() Exception: \'{}\', e={}'.format(ex, str(e)), code=2)
        self.stringMap = self.strings.map
        self.stringKeys = self.strings.keys
        self.numStrings = len(self.stringKeys)
        if len(self.strings.map) < 1:
            print('initStrings() ERROR! invalid stringMap, numStrings={}'.format(self.numStrings), file=Tabs.DBG_FILE)
            self.quit('initStrings() ERROR! Empty stringMap!', code=2)
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
    
    def readTabs(self, readSize=4096):
        dbg = 1
        fileSize = self.initInFile()
        tmp, htmp = [], []
        cnt, bytesRead, bgnTabs, endTabs, hasFrag, rowStr = 0, 0, None, None, 0, '{}'.format(self.ROW_OFF)
        data = self.inFile.read(readSize)
        if not len(data) or not fileSize:
            info = 'readTabs({}) ERROR! Invalid input file: file={} fileSize {:,} bytes, readSize {:,}, len(data)={}, data={}'.format(rowStr, self.inFile, fileSize, readSize, len(data), data) 
            print(info, file=Tabs.DBG_FILE)
            raise Exception(info)
        print('readTabs({}) fileSize {:,} bytes, reading first {:,} bytes:\'\n{}\''.format(rowStr, fileSize, readSize, ''.join([chr(data[p]) for p in range(0, readSize)])), file=Tabs.DBG_FILE)
        while len(data) != 0:
            bytesRead += len(data)
            p1, p2, i, bgn, fragment, end = -1, -1, 0, 0, b'', len(data)
            while i != -1:
                ii = i
                cnt += 1
                i = data.find(ord('H'), bgn, end)
                if i == -1 or i + 1 >= len(data):
                    fragment += data[ii+2:end]
                    hasFrag = 1
                    if dbg: print('readTabs({}) detected fragment, len={} \'{}\' ii={}, p1={}, p2={}, i={}, bgn={}'.format(rowStr, len(fragment), ''.join([chr(fragment[p]) for p in range(0, len(fragment))]), ii, p1, p2, i, bgn), file=Tabs.DBG_FILE)
                else:
                    p2 = data.rfind(ord(';'), i-4, i)
                    p1 = data.rfind(ord('['), i-7, p2) + 1
                    row = ''.join([chr(data[p]) for p in range(p1, p2)])
                    col = ''.join([chr(data[p]) for p in range(p2+1, i)])
                    if data[p1-3] == ord('m') and data[p1-6] == ord(';'):
                        s2 = ''.join([chr(data[p]) for p in range(p1-5, p1-3)])
                        if data[p1-9] == ord('[') or data[p1-9] == ord(';'):
                            s1 = ''.join([chr(data[p]) for p in range(p1-8, p1-6)])
                            if s1 == self.styles['H_TABS'][0:2] and s2 == self.styles['H_TABS'][3:5]:
                                print('readTabs() s1={} & s2={} matched harmonic tab style r={}, c={}, {}'.format(s1, s2, (int(rowStr) - self.ROW_OFF) % self.numStrings, int(col) - self.COL_OFF, len(self.htabs)), file=Tabs.DBG_FILE)
                                htmp.append(ord('1'))
                            else:
                                htmp.append(ord('0'))
                        else: self.printe('readTabs(parsing) s1={} s2={} \'{}\''.format(s1, s2, ''.join([chr(data[p]) for p in range(i-15, i)])))
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
                            if col != '1' and col != '2':
                                tabFN = self.getFretNum(ord(tab))
                                maxFN = self.getFretNum(self.maxFretInfo['MAX'])
                                if tabFN > maxFN:
                                    self.maxFretInfo['MAX'], self.maxFretInfo['LINE'], self.maxFretInfo['STR'], self.maxFretInfo['COL'] = ord(tab), self.row2Line(int(rowStr)), int(rowStr), int(col)
                                    self.dumpMaxFretInfo('readTabs({} {})'.format(row, col))
                        if hasFrag:
                            print('readTabs({}) {} {} [{},{}] ii={} p1={} p2={} i={} bgn={} {} \'{}\' data=\'{}\' tmp=\'{}\''.format(rowStr, cnt, len(fragment), row, col, ii, p1, p2, i, bgn, hasFrag, tab, ''.join([chr(data[p]) for p in range(ii, i+2)]), ''.join([chr(tmp[p]) for p in range(0, len(tmp))])), file=Tabs.DBG_FILE)
                            hasFrag = 0
                        elif dbg:
                            print('readTabs({}) {} {} [{},{}] ii={} p1={} p2={} i={} bgn={} {} \'{}\' data=\'{}\' tmp=\'{}\''.format(rowStr, cnt, len(fragment), row, col, ii, p1, p2, i, bgn, hasFrag, tab, ''.join([chr(data[p]) for p in range(ii+2, i+2)]), ''.join([chr(tmp[p]) for p in range(0, len(tmp))])), file=Tabs.DBG_FILE)
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
                        elif self.isTab(tab) and self.numTabsPerStringPerLine != 0 and int(col) == self.COL_OFF - 1 + self.numTabsPerStringPerLine:
                            tmp, htmp, rowStr = self.appendTabs(tmp, htmp, rowStr)
                    else:
                        self.quit('readTabs() prior to bgnTabs!', code=1)
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
        print('appendTabs({}) len(tmp)={} len(htmp)={}'.format(rowStr, len(tmp), len(htmp)), file=Tabs.DBG_FILE)
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
    
    def appendLine(self, uicKey=None, pt=1, dbg=0):
        '''Append another line of tabs to the display'''
        tabs, htabs = [], []
        print('appendLine(old) numTabsPerString:{} = numLines:{} * numTabsPerStringPerLine:{}, numTabs:{} = numStrings:{} * len(tabs[0]):{}'.format(self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.numTabs, self.numStrings, len(self.tabs[0])), file=Tabs.DBG_FILE)
        self.numLines += 1
        self.numTabsPerString = self.numLines * self.numTabsPerStringPerLine
        print('appendLine() len(tabs)={} len(htabs)={}'.format(len(self.tabs), len(self.htabs)), file=Tabs.DBG_FILE)
        for r in range(0, self.numStrings): print('appendLine() len(tabs[{}])={} len(htabs[{}])={}'.format(r, len(self.tabs[r]), r, len(self.htabs[r])), file=Tabs.DBG_FILE)
        for r in range(0, self.numStrings):
            print('appendLine() r={} len(tabs[{}])={} len(htabs[{}])={}'.format(r, r, len(self.tabs[r]), r, len(self.htabs[r])), file=Tabs.DBG_FILE)
            tabs.append(bytearray([ord('-')] * self.numTabsPerString))
            htabs.append(bytearray([0] * self.numTabsPerString))
            for c in range(0, len(self.tabs[r])):
                if dbg:
                    print('appendLine() r={} c={}'.format(r, c), file=Tabs.DBG_FILE)
                    print('appendLine() tabs[{}][{}]={}'.format(r, c, chr(self.tabs[r][c])), file=Tabs.DBG_FILE)
                    print('appendLine() htabs[{}][{}]={}'.format(r, c, chr(self.htabs[r][c])), file=Tabs.DBG_FILE)
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
            self.printh('{}: {}'.format(uicKey, self.appendLine.__doc__))
    
    def removeLine(self, uicKey=None):
        '''Remove last line of tabs from the display'''
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
        self.printh('{}: {}'.format(uicKey, self.removeLine.__doc__))
    
    def quit(self, uicKey=None, reason='Received Quit Cmd, Exiting', code=0):
        '''Quit with exit code and reason'''
        for i in range(18): print('##########', end='', file=Tabs.DBG_FILE)
        print(file=Tabs.DBG_FILE)
        self.dumpLineInfo('    quit(ExitCode={}, reason=\'{}\')'.format(code, reason))
        for i in range(18): print('##########', end='', file=Tabs.DBG_FILE)
        print(file=Tabs.DBG_FILE)
        self.dumpInfo('quit()')
        self.printErrorHistory()
        self.printCmdHistory(back=0)
        print('quit() rCmds=[', file=Tabs.DBG_FILE)
        for k in self.rCmds:
            if type(self.rCmds[k]) == str: print('{:>22} = {}'.format(k, self.rCmds[k]), file=Tabs.DBG_FILE)
            else:
                print('{:>22} = [ '.format(k), end='', file=Tabs.DBG_FILE)
                for kk in self.rCmds[k]: print('{}, '.format(kk), end='', file=Tabs.DBG_FILE)
                print(']', file=Tabs.DBG_FILE)
        print(']', file=Tabs.DBG_FILE)
        txt  = 'ExitCode={}, reason={} '.format(code, reason)
        txt += '{}: {}'.format(uicKey, self.quit.__doc__)
        cBgn = len(txt) + 1
        blank = ''
        for c in range(cBgn, self.endCol() + 1): blank += ' '
        print(Tabs.CSI + self.bStyle + self.styles['CONS'] + Tabs.CSI + '{};{}HExitCode={}, reason={} '.format(self.lastRow + 1, 1, code, reason), end='')
        print(Tabs.CSI + self.bStyle + self.styles['HLT_STUS'] + '{}: {}{}'.format(uicKey, self.quit.__doc__, blank), end='')
#        Tabs.DBG_FILE.flush()
#        os.fsync(Tabs.DBG_FILE)
        Tabs.DBG_FILE.close()
        exit(code)
    
    def printHelpInfo(self, uicKey=None, ui=1):
        '''Print help info (press the '?' key) [cmd line opt -h or -? or --help]'''
        self.clearScreen()
        self.printHelpSummary()
        self.printHelpUiCmds()
        print('{}'.format('Press any key to continue... (Note some of the help text may have scrolled off the screen, you should be able to scroll back to view it.)'))
        b = ord(getwch())
        self.clearScreen()
        if ui: self.printTabs(cs=1)
        self.printh('{}: {}'.format(uicKey, self.printHelpInfo.__doc__))
    
    def printHelpUiCmds(self):
        print('{:>20} : {}'.format('User Interactive Cmd', 'Description'))
        print('{:>20} : {}'.format('User Interactive Cmd', 'Description'), file=Tabs.DBG_FILE)
        print('--------------------------------------------------------------------------------')
        print('--------------------------------------------------------------------------------', file=Tabs.DBG_FILE)
        for k in self.uiKeys:
            print('{:>20} : {}'.format(k, self.uiCmds[k].__doc__))
            print('{:>20} : {}'.format(k, self.uiCmds[k].__doc__), file=Tabs.DBG_FILE)
    
    def registerUiCmds(self):
        self.rCmds = {}
        self.uiCmds = {}
        self.uiKeys = []
        self.registerUiCmd('Tablature',           self.setTab)
        self.registerUiCmd('Ctrl A',              self.toggleDisplayLabels)
        self.registerUiCmd('Ctrl B',              self.toggleDisplayChords)
        self.registerUiCmd('Ctrl C',              self.copySelectTabs)
        self.registerUiCmd('Ctrl D',              self.deleteSelectTabs)
        self.registerUiCmd('Ctrl E',              self.eraseTabs)
        self.registerUiCmd('Ctrl F',              self.toggleEnharmonic)
        self.registerUiCmd('Ctrl G',              self.goToCol)
        self.registerUiCmd('Ctrl H Backspace',    self.deletePrevTab)
        self.registerUiCmd('Ctrl I Tab',          self.toggleCursorDir)
        self.registerUiCmd('Ctrl J',              self.shiftSelectTabs)
        self.registerUiCmd('Ctrl K',              self.printChord)
        self.registerUiCmd('Ctrl L',              self.goToLastTab)
        self.registerUiCmd('Ctrl M Enter',        self.toggleCursorMode)
        self.registerUiCmd('Ctrl N',              self.toggleDisplayNotes)
        self.registerUiCmd('Ctrl P',              self.printTabs)
        self.registerUiCmd('Ctrl Q',              self.quit)
        self.registerUiCmd('Ctrl R',              self.resetTabs)
        self.registerUiCmd('Ctrl S',              self.saveTabs)
        self.registerUiCmd('Ctrl T',              self.appendLine)
        self.registerUiCmd('Ctrl U',              self.unselectAll)
        self.registerUiCmd('Ctrl V',              self.pasteSelectTabs)
        self.registerUiCmd('Ctrl X',              self.cutSelectTabs)
        self.registerUiCmd('Ctrl Z',              self.goToLastTab)
        self.registerUiCmd('Escape',              self.printStatus)
        self.registerUiCmd('Space',               self.moveCursor)
        self.registerUiCmd('?',                   self.printHelpInfo)
        self.registerUiCmd('Shift A',             self.analyzeChord)
        self.registerUiCmd('Shift B',             self.copySelectTabs)
        self.registerUiCmd('Shift C',             self.copySelectTabs)
        self.registerUiCmd('Shift D',             self.toggleBrightness)
        self.registerUiCmd('Shift E',             self.printErrorHistory)
        self.registerUiCmd('Shift F',             self.printMaxFretInfo)
        self.registerUiCmd('Shift H',             self.toggleHarmonicNote)
        self.registerUiCmd('Shift I',             self.toggleDisplayIntervals)
        self.registerUiCmd('Shift K',             self.setCapo)
        self.registerUiCmd('Shift L',             self.goToLastTab)
        self.registerUiCmd('Shift Q',             self.selectChord)
        self.registerUiCmd('Shift R',             self.printCmdHistory)
        self.registerUiCmd('Shift S',             self.printCmdHistory)
        self.registerUiCmd('Shift T',             self.removeLine)
        self.registerUiCmd('Shift U',             self.toggleColors)
        self.registerUiCmd('Shift W',             self.printErrorHistory)
        self.registerUiCmd('Shift X',             self.cutSelectTabs)
        self.registerUiCmd('Shift Z',             self.goToLastTab)
        self.registerUiCmd('Home',                self.moveHome)
        self.registerUiCmd('End',                 self.moveEnd)
        self.registerUiCmd('Page Up',             self.movePageUp)
        self.registerUiCmd('Page Down',           self.movePageDown)
        self.registerUiCmd('Insert',              self.toggleEditMode)
        self.registerUiCmd('Delete',              self.deleteTab)
        self.registerUiCmd('Up Arrow',            self.moveUp)
        self.registerUiCmd('Down Arrow',          self.moveDown)
        self.registerUiCmd('Left Arrow',          self.moveLeft)
        self.registerUiCmd('Right Arrow',         self.moveRight)
        self.registerUiCmd('Alt Left Arrow',      self.unselectCol)
        self.registerUiCmd('Alt Right Arrow',     self.unselectCol)
        self.registerUiCmd('Alt Up Arrow',        self.unselectRow)
        self.registerUiCmd('Alt Down Arrow',      self.unselectRow)
        self.registerUiCmd('Ctrl Left Arrow',     self.selectCol)
        self.registerUiCmd('Ctrl Right Arrow',    self.selectCol)
        self.registerUiCmd('Ctrl Up Arrow',       self.selectRow)
        self.registerUiCmd('Ctrl Down Arrow',     self.selectRow)
    
    def registerUiCmd(self, key, method):
        print('registerUiCmd() key={} method={}'.format(key, method.__name__), file=Tabs.DBG_FILE)
        if key not in self.uiKeys:
            self.uiCmds[key] = method
        else: self.printe('registerUiCmd() duplicate key={}'.format(key), x)
        if method.__name__ in self.rCmds:
            print('registerUiCmd() type(self.rCmds[method.__name__]){}'.format(type(self.rCmds[method.__name__])), file=Tabs.DBG_FILE)
            if type(self.rCmds[method.__name__]) is str:
                self.rCmds[method.__name__] = [self.rCmds[method.__name__], key]
            else: self.rCmds[method.__name__].append(key)
        else: self.rCmds[method.__name__] = key
        self.uiKeys = sorted(self.uiCmds)
    
    def dispatch(self, **kwargs):
        args, b, uicKey, dbg = {}, -1, None, 0
        if dbg: print('dispatch() kwargs={}\ndispatch()'.format(kwargs), end=' ', file=Tabs.DBG_FILE)
        for key, val in kwargs.items():
            if dbg: print('{}={}'.format(key, val), end=', ', file=Tabs.DBG_FILE)
            if    key == 'b':      b = val
            elif  key == 'uicKey': uicKey = val
            else:                  args[key] = val
        if dbg: print(file=Tabs.DBG_FILE)
        if 0 <= b <= 127: print('dispatch() {}(uicKey={}, b={}({}), args={})'.format(self.uiCmds[uicKey].__name__, uicKey, b, chr(b), args), file=Tabs.DBG_FILE)
        else:             print('dispatch() {}(uicKey={}, b={}, args={})'.format(self.uiCmds[uicKey].__name__, uicKey, b, args), file=Tabs.DBG_FILE)
        self.uiCmds[uicKey](uicKey=uicKey, **args)
    
    def loop(self):
        '''Run the user interactive loop, executing commands as they are entered via the keyboard'''
        while True:
            c = getwch(); b = ord(c)                                              # get wide char -> int
            if self.isTab(c): self.dispatch(tab=b, uicKey='Tablature')            # setTab()                 # N/A
            elif b == 0:      continue                                            # null escape?
            elif b == 1:      self.dispatch(b=b, uicKey='Ctrl A')                 # toggleDisplayLabels()    # cmd line opt -a
            elif b == 2:      self.dispatch(b=b, uicKey='Ctrl B')                 # toggleDisplayChords()    # cmd line opt -b
            elif b == 3:      self.dispatch(b=b, uicKey='Ctrl C')                 # copySelectTabs()         # N/A
            elif b == 4:      self.dispatch(b=b, uicKey='Ctrl D')                 # deleteSelectTabs()       # N/A
            elif b == 5:      self.dispatch(b=b, uicKey='Ctrl E')                 # eraseTabs()              #?cmd line opt?
            elif b == 6:      self.dispatch(b=b, uicKey='Ctrl F')                 # toggleEnharmonic()       # cmd line opt -F?
            elif b == 7:      self.dispatch(b=b, uicKey='Ctrl G')                 # goToCol()                #?cmd line opt -g?
            elif b == 8:      self.dispatch(b=b, uicKey='Ctrl H Backspace')       # deletePrevTab()          # N/A
            elif b == 9:      self.dispatch(b=b, uicKey='Ctrl I Tab')             # toggleCursorDir()        # cmd line opt -i
            elif b == 10:     self.dispatch(b=b, uicKey='Ctrl J')                 # shiftSelectTabs()        # N/A
            elif b == 11:     self.dispatch(b=b, uicKey='Ctrl K', dbg=3)          # printChord()             # N/A
            elif b == 12:     self.dispatch(b=b, uicKey='Ctrl L', cs=1)           # goToLastTab()            # cmd line opt -l
            elif b == 13:     self.dispatch(b=b, uicKey='Ctrl M Enter')           # toggleCursorMode()       # cmd line opt -m
            elif b == 14:     self.dispatch(b=b, uicKey='Ctrl N')                 # toggleDisplayNotes()     # cmd line opt -n
            elif b == 16:     self.dispatch(b=b, uicKey='Ctrl P')                 # printTabs()              # DBG?
            elif b == 17:     self.dispatch(b=b, uicKey='Ctrl Q')                 # quit()                   # DBG?
            elif b == 18:     self.dispatch(b=b, uicKey='Ctrl R')                 # resetTabs()              # DBG?
            elif b == 19:     self.dispatch(b=b, uicKey='Ctrl S')                 # saveTabs()               # DBG?
            elif b == 20:     self.dispatch(b=b, uicKey='Ctrl T')                 # appendLine()             # DBG?
            elif b == 21:     self.dispatch(b=b, uicKey='Ctrl U')                 # unselectAll()            # N/A
            elif b == 22:     self.dispatch(b=b, uicKey='Ctrl V')                 # pasteSelectTabs()        # N/A
            elif b == 24:     self.dispatch(b=b, uicKey='Ctrl X')                 # cutSelectTabs()          # N/A
            elif b == 26:     self.dispatch(b=b, uicKey='Ctrl Z', ll=1, cs=1)     # goToLastTab()            # cmd line opt -z
            elif b == 27:     self.dispatch(b=b, uicKey='Escape')                 # printStatus()            # N/A
#            elif b == 28:     self.dispatch(b=b, uicKey='Ctrl \\')
#            elif b == 29:     self.dispatch(b=b, uicKey='Ctrl ]')
#            elif b == 30:     self.dispatch(b=b, uicKey='Ctrl ^')
#            elif b == 31:     self.dispatch(b=b, uicKey='Ctrl _')
            elif b == 32:     self.dispatch(b=b, uicKey='Space')                  # moveCursor()             # N/A
            elif b == 63:     self.dispatch(b=b, uicKey='?')                      # printHelpInfo()          # cmd line opt -?
            elif b == 65:     self.dispatch(b=b, uicKey='Shift A')                # analyzeChord()           # N/A
            elif b == 66:     self.dispatch(b=b, uicKey='Shift B', arpg=0)        # copySelectTabs()         # N/A
            elif b == 67:     self.dispatch(b=b, uicKey='Shift C', arpg=1)        # copySelectTabs()         # N/A
            elif b == 68:     self.dispatch(b=b, uicKey='Shift D')                # toggleBrightness()       # N/A
            elif b == 69:     self.dispatch(b=b, uicKey='Shift E')                # printErrorHistory()      # N/A
            elif b == 70:     self.dispatch(b=b, uicKey='Shift F')                # printMaxFretInfo()       # N/A
            elif b == 72:     self.dispatch(b=b, uicKey='Shift H')                # toggleHarmonicNote()     # N/A
            elif b == 73:     self.dispatch(b=b, uicKey='Shift I')                # toggleDisplayIntervals() # cmd line opt -I
            elif b == 75:     self.dispatch(b=b, uicKey='Shift K')                # setCapo()                # cmd line opt -k?
            elif b == 76:     self.dispatch(b=b, uicKey='Shift L')                # goToLastTab()            # cmd line opt -L
            elif b == 81:     self.dispatch(b=b, uicKey='Shift Q')                # selectChord()            # N/A
            elif b == 82:     self.dispatch(b=b, uicKey='Shift R')                # printCmdHistory()        # N/A
            elif b == 83:     self.dispatch(b=b, uicKey='Shift S', back=0)        # printCmdHistory()        # N/A
            elif b == 84:     self.dispatch(b=b, uicKey='Shift T')                # removeLine()             # DBG?
            elif b == 85:     self.dispatch(b=b, uicKey='Shift U')                # toggleColors()           # DBG?
            elif b == 87:     self.dispatch(b=b, uicKey='Shift W', back=0)        # printErrorHistory()      # N/A
            elif b == 88:     self.dispatch(b=b, uicKey='Shift X', arpg=1)        # cutSelectTabs()          # N/A
            elif b == 90:     self.dispatch(b=b, uicKey='Shift Z', ll=1)          # goToLastTab()            # cmd line opt -Z
            elif b == 155:    self.dispatch(b=b, uicKey='Alt Left Arrow', left=1) # unselectCol()            # N/A
            elif b == 157:    self.dispatch(b=b, uicKey='Alt Right Arrow')        # unselectCol()            # N/A
            elif b == 152:    self.dispatch(b=b, uicKey='Alt Up Arrow', up=1)     # unselectRow()            # N/A
            elif b == 160:    self.dispatch(b=b, uicKey='Alt Down Arrow')         # unselectRow()            # N/A
#            elif b == 161:    self.dispatch(b=b, uicKey='Alt Page Down')          # movePageDown()           # N/A
            elif b == 224:                                                                 # Escape Sequence        # N/A
                b = ord(getwch())                                                          # Read the escaped character
                if   b == 75:     self.dispatch(b=b, uicKey='Left Arrow')                  # moveLeft()             # N/A
                elif b == 77:     self.dispatch(b=b, uicKey='Right Arrow')                 # moveRight()            # N/A
                elif b == 72:     self.dispatch(b=b, uicKey='Up Arrow')                    # moveUp()               # N/A
                elif b == 80:     self.dispatch(b=b, uicKey='Down Arrow')                  # moveDown()             # N/A
                elif b == 71:     self.dispatch(b=b, uicKey='Home')                        # moveHome()             #?cmd line opt?
                elif b == 79:     self.dispatch(b=b, uicKey='End')                         # moveEnd()              #?cmd line opt?
                elif b == 73:     self.dispatch(b=b, uicKey='Page Up')                     # movePageUp()           #?cmd line opt?
                elif b == 81:     self.dispatch(b=b, uicKey='Page Down')                   # movePageDown()         #?cmd line opt?
                elif b == 82:     self.dispatch(b=b, uicKey='Insert')                      # toggleEditMode()       # cmd line opt
                elif b == 83:     self.dispatch(b=b, uicKey='Delete')                      # deleteTab()            # N/A
                elif b == 115:    self.dispatch(b=b, uicKey='Ctrl Left Arrow', left=1)     # selectCol()            # N/A
                elif b == 116:    self.dispatch(b=b, uicKey='Ctrl Right Arrow')            # selectCol()            # N/A
                elif b == 141:    self.dispatch(b=b, uicKey='Ctrl Up Arrow', up=1)         # selectRow()            # N/A
                elif b == 145:    self.dispatch(b=b, uicKey='Ctrl Down Arrow')             # selectRow()            # N/A
                else:             self.printe('loop() unsupported Escape Cmd: {}({})'.format(b, chr(b)))
            elif 0 <= b <= 127:   self.printe('loop() unsupported Cmd Key: {}({})'.format(b, chr(b)))
            else: self.printe('loop() unsupported Cmd Key: {}'.format(b))
    
    def resetPos(self):
        print(Tabs.CSI + '{};{}H'.format(self.row, self.col), end='')
    
    def moveToCol(self, c):
        row, col = self.indices2RowCol(0, c)
        print('moveToCol(c={}) row={} col={}'.format(c, row, col), file=Tabs.DBG_FILE)
        self.moveTo(row, col)
    
    def moveTo(self, row=None, col=None, hi=0):
        '''Move to given row and col (optionally hilite row and col num)'''
        if row is not None: self.row = row
        if col is not None: self.col = col
        print('moveTo({}, {}, {}) row={} col={} line={}'.format(row, col, hi, self.row, self.col, self.row2Line(self.row)), file=Tabs.DBG_FILE)
        self.resetPos()
        self.printStatus()
        if hi == 1 and self.displayLabels == self.DISPLAY_LABELS['ENABLED']:
            self.hiliteRowColNum()
   
    def moveLeft(self, uicKey=None, dbg=0):
        '''Move cursor left 1 column on current line wrapping to end of row on previous line or last line'''
        if dbg or self.dbgMove: print('moveLeft({}, {})'.format(self.row, self.col), file=Tabs.DBG_FILE)
        if self.col == self.bgnCol():
            line = self.row2Line(self.row)
            if line == 0: self.moveTo(row=self.row + self.lineDelta() * (self.numLines - 1), col=self.endCol(), hi=1)
            else:         self.moveTo(row=self.row - self.lineDelta(), col=self.endCol(), hi=1)
        else:             self.moveTo(col=self.col - 1, hi=1)
        self.printh('{}: {}'.format(uicKey, self.moveLeft.__doc__))
    
    def moveRight(self, uicKey=None, dbg=0):
        '''Move cursor right 1 column on current line wrapping to start of row on next line or first line'''
        oldRow, oldCol = self.rowCol2Indices(self.row, self.col)
        if self.col == self.endCol():
            line = self.row2Line(self.row)
            if line == self.numLines - 1: self.moveTo(row=self.row - self.lineDelta() * (self.numLines - 1), col=self.bgnCol(), hi=1)
            else:                         self.moveTo(row=self.row + self.lineDelta(), col=self.bgnCol(), hi=1)
        else:                             self.moveTo(col=self.col + 1, hi=1)
        info = 'moveRight() from ({}, {}) to ({}, {})'.format(oldRow, oldCol, self.rowCol2Indices(self.row, self.col)[0], self.rowCol2Indices(self.row, self.col)[1])
        if dbg or self.dbgMove: print(info, file=Tabs.DBG_FILE)
        self.printh('{}: {}'.format(self.rCmds['moveRight'], info))
    
    def moveUp(self, uicKey=None, dbg=0):
        '''Move cursor up 1 row on current line wrapping to last row on previous line or last line'''
        if dbg or self.dbgMove: self.dumpLineInfo('moveUp({}, {})'.format(self.row, self.col))
        line = self.row2Line(self.row)
        if self.row == self.bgnRow(line):
            if line == 0: self.moveTo(row=self.endRow(self.numLines - 1), hi=1)
            else:         self.moveTo(row=self.endRow(line - 1), hi=1)
        else:             self.moveTo(row=self.row - 1, hi=1)
        self.printh('{}: {}'.format(uicKey, self.moveUp.__doc__))
    
    def moveDown(self, uicKey=None, dbg=0):
        '''Move cursor down 1 row on current line wrapping to first row on next line or first line'''
        oldRow, oldCol = self.rowCol2Indices(self.row, self.col)
        line = self.row2Line(self.row)
        if self.row == self.endRow(line):
            if line == self.numLines - 1: self.moveTo(row=self.bgnRow(0), hi=1)
            else:                         self.moveTo(row=self.bgnRow(line + 1), hi=1)
        else:                             self.moveTo(row=self.row + 1, hi=1)
        info = 'moveDown() from ({}, {}) to ({}, {})'.format(oldRow, oldCol, self.rowCol2Indices(self.row, self.col)[0], self.rowCol2Indices(self.row, self.col)[1])
        if dbg or self.dbgMove: print(info, file=Tabs.DBG_FILE)
        self.printh('{}: {}'.format(self.rCmds['moveDown'], info))
    
    def moveHome(self, uicKey=None, dbg=0):
        '''Move cursor to start of row on current line wrapping to end of row on previous line or last line'''
        if dbg or self.dbgMove: print('moveHome({}, {})'.format(self.row, self.col), file=Tabs.DBG_FILE)
        if self.col == self.bgnCol():
            line = self.row2Line(self.row)
            if line == 0: self.moveTo(row=self.row + self.lineDelta() * (self.numLines - 1), col=self.endCol(), hi=1)
            else:         self.moveTo(row=self.row - self.lineDelta(), col=self.endCol(), hi=1)
        else:             self.moveTo(col=self.bgnCol(), hi=1)
        self.printh('{}: {}'.format(uicKey, self.moveHome.__doc__))
    
    def moveEnd(self, uicKey=None, dbg=0):
        '''Move cursor to end of row on current line wrapping to start of row on next line or first line'''
        if dbg or self.dbgMove: print('moveEnd({}, {})'.format(self.row, self.col), file=Tabs.DBG_FILE)
        if self.col == self.endCol():
            line = self.row2Line(self.row)
            if line == self.numLines - 1: self.moveTo(row=self.row - self.lineDelta() * (self.numLines - 1), col=self.bgnCol(), hi=1)
            else:                         self.moveTo(row=self.row + self.lineDelta(), col=self.bgnCol(), hi=1)
        else:                             self.moveTo(col=self.endCol(), hi=1)
        self.printh('{}: {}'.format(uicKey, self.moveEnd.__doc__))
    
    def movePageUp(self, uicKey=None, dbg=0):
        '''Move cursor to first row on current line wrapping to last row on previous line or last line'''
        if dbg or self.dbgMove: self.dumpLineInfo('movePageUp({}, {})'.format(self.row, self.col))
        line = self.row2Line(self.row)
        if self.row == self.bgnRow(line):
            if line == 0: self.moveTo(row=self.endRow(self.numLines - 1), hi=1)
            else:         self.moveTo(row=self.endRow(line - 1), hi=1)
        else:             self.moveTo(row=self.bgnRow(line), hi=1)
        self.printh('{}: {}'.format(uicKey, self.movePageUp.__doc__))
    
    def movePageDown(self, uicKey=None, dbg=0):
        '''Move cursor to last row on current line wrapping to first row on next line or first line'''
        if dbg or self.dbgMove: self.dumpLineInfo('movePageDown({}, {})'.format(self.row, self.col))
        line = self.row2Line(self.row)
        if self.row == self.endRow(line):
            if line == self.numLines - 1: self.moveTo(row=self.bgnRow(0), hi=1)
            else:                         self.moveTo(row=self.bgnRow(line + 1), hi=1)
        else:                             self.moveTo(row=self.endRow(line), hi=1)
        self.printh('{}: {}'.format(uicKey, self.movePageDown.__doc__))
    
    def moveCursor(self, uicKey=None, row=None, col=None, back=0):
        '''Move cursor to next row and or col with automatic cursor mode optionally hilite new row and col'''
        print('moveCursor(row={}, col={}, back={}) old: row={} col={} bgn'.format(row, col, back, self.row, self.col), file=Tabs.DBG_FILE)
        if row != None: self.row = row
        if col != None: self.col = col
        if self.cursorMode == self.CURSOR_MODES['MELODY']:
            if back == 1: self.moveLeft()
            else:    self.moveRight()
        elif self.cursorMode == self.CURSOR_MODES['CHORD'] or self.cursorMode == self.CURSOR_MODES['ARPEGGIO']:
            if self.cursorMode == self.CURSOR_MODES['ARPEGGIO']:
                self.moveRight()
            line = self.row2Line(self.row)
            if self.cursorDir == self.CURSOR_DIRS['DOWN']:
                if back == 1:
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
                if back == 1:
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
        print('moveCursor(row={}, col={}, back={}) new: row={}, col={} end'.format(row, col, back, self.row, self.col), file=Tabs.DBG_FILE)
        self.printh('{}: {}'.format(uicKey, self.moveCursor.__doc__))
    
    def tests(self):
        for c in (0, 207, 208, 415, 416, 623, 624, 831): print('tests() line=colIndex2Line({})={}'.format(c, self.colIndex2Line(c)), file=Tabs.DBG_FILE)
    
    def testRow2Line(self):
        for row in range(-2, 76):
            row += self.ROW_OFF
            line = self.row2Line(row)
            print('row={} line={}'.format(row, line), file=Tabs.DBG_FILE)
    
    def row2Line(self, row):
        for line in range(0, self.numLines):
            if 0 < row < self.bgnRow(line + 1) - 1:
                return line
        self.printe('Range Error row={}'.format(row))
    
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
    
    def _toggleCursorDir(self, dbg=1):
        for line in range(0, self.numLines):
            for r in range(0, self.numStrings):
                if self.cursorDir == self.CURSOR_DIRS['DOWN']: self.cursorDirStyle = self.styles['NUT_DN']
                elif self.cursorDir == self.CURSOR_DIRS['UP']: self.cursorDirStyle = self.styles['NUT_UP']
                self.prints(chr(self.capo), r + self.bgnRow(line)                                                        , self.cursorModeCol, self.cursorDirStyle)
                self.prints(chr(self.capo), r + self.bgnRow(line) + self.numStrings                                      , self.cursorModeCol, self.cursorDirStyle)
                self.prints(chr(self.capo), r + self.bgnRow(line) + self.numStrings + self.NOTES_LEN                     , self.cursorModeCol, self.cursorDirStyle)
            for r in range(0, self.CHORDS_LEN):
                self.prints(chr(self.capo), r + self.bgnRow(line) + self.numStrings + self.NOTES_LEN + self.INTERVALS_LEN, self.cursorModeCol, self.cursorDirStyle)
        if dbg: self.dumpLineInfo('toggleCursorDir({}) line={} row={} col={}'.format(self.cursorDir, line, self.row, self.col))
    
    def toggleCursorDir(self, uicKey=None, dbg=1):
        '''Toggle direction (up or down) of cursor vertical movement [cmd line opt -i]'''
        self.cursorDir = (self.cursorDir + 1) % len(self.CURSOR_DIRS)
        self._toggleCursorDir()
        self.printh('{}: {}'.format(uicKey, self.toggleCursorDir.__doc__))
    
    def toggleEditMode(self, uicKey=None, dbg=1):
        '''Toggle between editing modes (insert or replace)'''
        self.editMode = (self.editMode + 1) % len(self.EDIT_MODES)
        if self.displayLabels == self.DISPLAY_LABELS['ENABLED']:
            for line in range(0, self.numLines):
                r = line * self.lineDelta() + 1
                if self.editMode == self.EDIT_MODES['INSERT']:
                    self.prints('I', r, self.editModeCol, self.styles['MODES'])
                elif self.editMode == self.EDIT_MODES['REPLACE']:
                    self.prints('R', r, self.editModeCol, self.styles['MODES'])
            if dbg: self.dumpLineInfo('toggleEditMode({}, {})'.format(self.row, self.col))
        self.printh('{}: {}'.format(uicKey, self.toggleEditMode.__doc__))
    
    def toggleCursorMode(self, uicKey=None, dbg=1):
        '''Toggle cursor automatic movement modes (M=melody, C=chord, or A=arpeggio)'''
        oldMode = self.getCursorMode()
        self.cursorMode = (self.cursorMode + 1) % len(self.CURSOR_MODES)
        if self.displayLabels == self.DISPLAY_LABELS['ENABLED']:
            for line in range(0, self.numLines):
                r = line * self.lineDelta() + 1
                newMode = self.getCursorMode()
                self.prints(newMode, r, self.cursorModeCol, self.styles['MODES'])
            if dbg: self.dumpLineInfo('toggleCursorMode({}, {})'.format(self.row, self.col))
        info = 'toggleCursorMode() toggling cursor mode from {} to {}'.format(oldMode, newMode)
        self.printh('{}: {}'.format(self.rCmds['toggleCursorMode'], info))
    
    def getCursorMode(self):
        if self.cursorMode == self.CURSOR_MODES['MELODY']:     return 'M'
        elif self.cursorMode == self.CURSOR_MODES['CHORD']:    return 'C'
        elif self.cursorMode == self.CURSOR_MODES['ARPEGGIO']: return 'A'
    
    def toggleEnharmonic(self, uicKey=None):
        '''Toggle display of enharmonic between sharp and flat notes [cmd line opt -F]'''
        self.enharmonic = (self.enharmonic + 1) % len(self.ENHARMONICS)
        self.printTabs()
        self.printh('{}: {}'.format(uicKey, self.toggleEnharmonic.__doc__))
    
    def toggleDisplayLabels(self, uicKey=None, pt=1):
        '''Toggle display of Labels row, including cursor and insert mode characters [cmd line opt -a]'''
        self.displayLabels = (self.displayLabels + 1) % len(self.DISPLAY_LABELS)
        line = self.row2Line(self.row)
        if self.displayLabels == self.DISPLAY_LABELS['ENABLED']:
            self.ROW_OFF = 2
            self.row += 1
        elif self.displayLabels == self.DISPLAY_LABELS['DISABLED']:
            self.ROW_OFF = 1
            self.row -= 1
        self.setLastRow()
        self.dumpLineInfo('toggleDisplayLabels({}) line={} row={} col={}'.format(self.displayLabels, line, self.row, self.col))
        if pt: 
            self.printTabs(cs=1)
            self.printh('{}: {}'.format(uicKey, self.toggleDisplayLabels.__doc__))
    
    def toggleDisplayNotes(self, uicKey=None, pt=1):
        '''Toggle (enable or disable) display of notes section [cmd line opt -n]'''
        self.displayNotes = (self.displayNotes + 1) % len(self.DISPLAY_NOTES)
        line = self.row2Line(self.row)
        if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
            self.NOTES_LEN = self.numStrings
            self.row += line * self.NOTES_LEN
        elif self.displayNotes == self.DISPLAY_NOTES['DISABLED']:
            self.row -= line * self.NOTES_LEN
            self.NOTES_LEN = 0
        self.setLastRow()
        self.dumpLineInfo('toggleDisplayNotes({}) line={} row={} col={}'.format(self.displayNotes, line, self.row, self.col))
        if pt: 
            self.printTabs(cs=1)
            self.printh('{}: {}'.format(uicKey, self.toggleDisplayNotes.__doc__))
    
    def toggleDisplayIntervals(self, uicKey=None, pt=1):
        '''Toggle (enable or disable) display of intervals section [cmd line opt -I]'''
        self.displayIntervals = (self.displayIntervals + 1) % len(self.DISPLAY_INTERVALS)
        line = self.row2Line(self.row)
        if self.displayIntervals == self.DISPLAY_INTERVALS['ENABLED']:
            self.INTERVALS_LEN = self.numStrings
            self.row += line * self.INTERVALS_LEN
        elif self.displayIntervals == self.DISPLAY_INTERVALS['DISABLED']:
            self.row -= line * self.INTERVALS_LEN
            self.INTERVALS_LEN = 0
        self.setLastRow()
        self.dumpLineInfo('toggleDisplayIntervals({} {}) line={} row={} col={}'.format(self.displayIntervals, pt, line, self.row, self.col))
        if pt: 
            self.printTabs(cs=1)
            self.printh('{}: {}'.format(uicKey, self.toggleDisplayIntervals.__doc__))
    
    def toggleDisplayChords(self, uicKey=None, pt=1):
        '''Toggle (enable or disable) display of chords section [cmd line opt -b]'''
        self.displayChords = (self.displayChords + 1) % len(self.DISPLAY_CHORDS)
        line = self.row2Line(self.row)
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            if self.chordsObj is None:
                self.chordsObj = chords.Chords(self)
            self.CHORDS_LEN = 5
            self.row += line * self.CHORDS_LEN
        elif self.displayChords == self.DISPLAY_CHORDS['DISABLED']:
            self.row -= line * self.CHORDS_LEN
            self.CHORDS_LEN = 0
        self.setLastRow()
        self.dumpLineInfo('toggleDisplayChords({}) line={} row={} col={}'.format(self.displayChords, line, self.row, self.col))
        if pt: 
            self.printTabs(cs=1)
            self.printh('{}: {}'.format(uicKey, self.toggleDisplayChords.__doc__))
    
    def toggleHarmonicNote(self, uicKey=None):
        '''Toggle between normal and harmonic note, set to closest natural harmonic note to tab fret number'''
        line = self.row2Line(self.row)
        r, c = self.rowCol2Indices(self.row, self.col)
        tab = self.tabs[r][c]
        print('toggleHarmonicNote({} {}) r={} c={} tab={}'.format(self.row, self.col, r, c, chr(tab)), file=Tabs.DBG_FILE)
        if self.htabs[r][c] == ord('0'):
            if Tabs.isFret(chr(tab)) and self.getFretNum(tab) in self.HARMONIC_FRETS:
                self.htabs[r][c] = ord('1')
                n = self.getHarmonicNote(r + 1, tab)
                self.prints(chr(tab), self.row, self.col, self.styles['H_TABS'])
                if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                    self.printNote(r + line * self.lineDelta() + self.endRow(0) + 1 , self.col, n, hn=1)
                pn = self.getNote(r + 1, tab)
                print('toggleHarmonicNote({} {}) r={} c={} tab={} pn.n={} pn.i={} norm->harm n.n={} n.i={}'.format(self.row, self.col, r, c, chr(tab), pn.name, pn.index, n.name, n.index), file=Tabs.DBG_FILE)
            else: 
                self.printe('toggleHarmonicNote() tab={} is not in HARMONIC_FRETS={}'.format(tab, self.HARMONIC_FRETS))
                return
        else:
            self.htabs[r][c] = ord('0')
            n = self.getNote(r + 1, tab)
            self.prints(chr(tab), self.row, self.col, self.styles['TABS'])
            if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                self.printNote(r + line * self.lineDelta() + self.endRow(0) + 1 , self.col, n)
            pn = self.getHarmonicNote(r + 1, tab)
            print('toggleHarmonicNote({} {}) r={} c={} tab={} pn.n={} pn.i={} harm->norm n.n={} n.i={}'.format(self.row, self.col, r, c, chr(tab), pn.name, pn.index, n.name, n.index), file=Tabs.DBG_FILE)
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.chordsObj.eraseChord(c)
            self.chordsObj.printChord(c=c)
        self.printStatus()
        self.printh('{}: {}'.format(uicKey, self.toggleHarmonicNote.__doc__))
    
    def toggleBrightness(self, uicKey=None, bi=None, pt=1):
        '''Toggle display between normal and bright colors'''
        print('toggleBrightness(bi={}) brightness={} bgn'.format(bi, self.brightness), file=Tabs.DBG_FILE)
        if bi == None: self.brightness = (self.brightness + 1) % 2
        else:          self.brightness = bi
        print('toggleBrightness(bi={}) brightness={}'.format(bi, self.brightness), file=Tabs.DBG_FILE)
        self.initBrightness()
        if pt:
            self.printTabs()
            self.printh('{}: {}'.format(uicKey, self.toggleBrightness.__doc__))
    
    def toggleColors(self, uicKey=None, ci=None, pt=1):
        '''Toggle between color schemes'''
        print('toggleColors(ci={}) colorsIndex={} bgn'.format(ci, self.colorsIndex), file=Tabs.DBG_FILE)
        if ci == None: self.colorsIndex = (self.colorsIndex + 1) % 3
        else:          self.colorsIndex = ci
        print('toggleColors(ci={}) colorsIndex={}'.format(ci, self.colorsIndex), file=Tabs.DBG_FILE)
        self.initColors()
        self._toggleCursorDir()
        if pt:
            self.printTabs()
            self.printh('{}: {}'.format(uicKey, self.toggleColors.__doc__))
    
    def printColNums(self, row):
        print('printColNums(row={})'.format(row), file=Tabs.DBG_FILE)
        for c in range(0, self.numTabsPerStringPerLine):
            self.printColNum(row, c + 1, self.brightnessA)
    
    def printColNum(self, row, c, style):
        '''Print 1 based tab col index, c, as a single decimal digit.'''
        '''123456789112345678921234567893123456789412345678951234567896123456789712345678981234567899123456789012345678911234567892123456789312345678941234567895'''
        if c % 10: style += self.styles['MIN_COL_NUM']
        else:      style += self.styles['MAJ_COL_NUM']
        self.prints('{}'.format(Tabs.getColMod(c)), row, c + self.COL_OFF - 1, style)
    
    @staticmethod
    def getColMod(c):
        if c % 10:  return c % 10
        else:
            while c >= 100: c-= 100
        return c // 10
    
    def hiliteRowColNum(self, dbg=0):
        self.hiliteCount += 1
        if dbg: print('hiliteRowColNum({}, {}) hilitePrevRowPos={} hiliteRowNum={} hiliteColNum={} hiliteCount={}'.format(self.row, self.col, self.hilitePrevRowPos, self.hiliteRowNum, self.hiliteColNum, self.hiliteCount), file=Tabs.DBG_FILE)
        for line in range(0, self.numLines):
            row = line * self.lineDelta() + 1
            if self.hiliteColNum != 0:
                self.printColNum(row, self.hiliteColNum, self.brightnessA)
        self.hiliteColNum = self.col - self.COL_OFF + 1
        for line in range(0, self.numLines):
            row = line * self.lineDelta() + 1
            if self.hiliteColNum != 0:
                self.printColNum(row, self.hiliteColNum, self.brightnessB)
                
        if self.hiliteRowNum != 0:
            self.prints(self.hiliteRowNum, self.hilitePrevRowPos, self.editModeCol, self.brightnessA + self.styles['TABS'])
        self.hiliteRowNum = self.row - self.row2Line(self.row) *  self.lineDelta() - 1
        self.hilitePrevRowPos = self.row
        if dbg: print('hiliteRowColNum({}, {}) hilitePrevRowPos={} hiliteRowNum={} hiliteColNum={} hiliteCount={}'.format(self.row, self.col, self.hilitePrevRowPos, self.hiliteRowNum, self.hiliteColNum, self.hiliteCount), file=Tabs.DBG_FILE)
        self.prints(self.hiliteRowNum, self.row, self.editModeCol, self.brightnessB + self.styles['TABS'])
        self.resetPos()
    
    def getMaxFretInfo(self, dbg=0):
        maxFN = 0
        if dbg: print('getMaxFretInfo() len(tabs)={} len(tabs[0])={}'.format(len(self.tabs), len(self.tabs[0])), file=Tabs.DBG_FILE)
        for r in range(0, len(self.tabs)):
            for c in range(0, len(self.tabs[r])):
                tab = self.tabs[r][c]
                if Tabs.isFret(chr(tab)):
                    currFN = self.getFretNum(tab)
                    if currFN > maxFN:
                        maxFN = currFN
                        self.maxFretInfo['MAX'], self.maxFretInfo['LINE'], self.maxFretInfo['STR'], self.maxFretInfo['COL'] = self.getFretByte(maxFN), self.colIndex2Line(c), self.indices2Row(r, c)-1, self.index2Col(c)
                        if dbg: print('getMaxFretInfo() r={} c={} tab={}({}) maxFN={}'.format(r, c, tab, chr(tab), maxFN), file=Tabs.DBG_FILE)
        self.dumpMaxFretInfo('getMaxFretInfo()')
    
    def dumpMaxFretInfo(self, reason):
        print('dumpMaxFretInfo() {} max={}({}) line={} string={} col={}'.format(reason, self.maxFretInfo['MAX'], chr(self.maxFretInfo['MAX']), self.maxFretInfo['LINE']+1, self.maxFretInfo['STR'], self.maxFretInfo['COL']-2), file=Tabs.DBG_FILE)
    
    def printMaxFretInfo(self, uicKey=None):
        '''Print max fret info'''
        self.printh('{}: {} max={}({}) line={} string={} col={}'.format(uicKey, self.printMaxFretInfo.__doc__, self.maxFretInfo['MAX'], chr(self.maxFretInfo['MAX']), self.maxFretInfo['LINE']+1, self.maxFretInfo['STR'], self.maxFretInfo['COL']-2))
    
    def goToCol(self, uicKey=None):
        '''Go to col given by user input of up to 3 digits terminated by space char [12 ][123]'''
        self.printh('{}: {}'.format(uicKey, self.goToCol.__doc__))
        cc, tmp = '', []
        while len(tmp) < 3:
            cc = getwch()
            if cc != ' ' and '0' <= cc <= '9': tmp.append(cc)
            else: break
        if len(tmp):
            c = int(''.join(tmp))
            col = self.index2Col(c)
            line = self.colIndex2Line(c)
            print('goToCol({} {}) c={} col={} line={}'.format(self.row, self.col, c, col, line), file=Tabs.DBG_FILE)
            row = self.bgnRow(0) + line * self.lineDelta()
            print('goToCol() row={} bgnRow(0)={} line={} lineDelta={}'.format(row, self.bgnRow(0), line, self.lineDelta()), file=Tabs.DBG_FILE)
            self.moveTo(row=row, col=col, hi=1)
    
    def goToLastTab(self, uicKey=None, cs=0, ll=0):
        '''Go to last tab pos on current line or last line ll=1, of all strings or current string, cs=1'''
        if not cs and not ll: index=2
        elif cs and not ll: index=0
        elif not cs and ll: index=3
        elif cs and ll: index=1
        rr, cc = 0, 0
        if ll: lineBgn, lineEnd = self.numLines,               0
        else:  lineBgn, lineEnd = self.row2Line(self.row) + 1, self.row2Line(self.row)
        if cs: rowBgn,  rowEnd = self.row2Index(self.row),     self.row2Index(self.row) + 1
        else:  rowBgn,  rowEnd = 0,                            self.numStrings
        print('goToLastTab({}, {}) cs={} ll={} rowBng={} rowEnd={} lineBgn={} lineEnd={}'.format(self.row, self.col, cs, ll, rowBgn, rowEnd, lineBgn, lineEnd), file=Tabs.DBG_FILE)
        for line in range(lineBgn, lineEnd, -1):
            for r in range(rowBgn, rowEnd):
                for c in range(line * self.numTabsPerStringPerLine - 1, (line - 1) * self.numTabsPerStringPerLine - 1, -1):
                    t = chr(self.tabs[r][c])
                    if t != '-' and self.isTab(t):
                        if c > cc:
                            rr, cc, ll = r, c, line
                            print('goToLastTab(updating col) t={} line={} r={} c={}'.format(t, line, r, c), file=Tabs.DBG_FILE)
                        break
        if cc > 0:
            row, col = self.indices2RowCol(rr, cc)
            print('goToLastTab() row,col=({},{})'.format(row, col), file=Tabs.DBG_FILE)
            self.moveTo(row=row, col=col, hi=1)
        self.printh('{}: {}'.format(self.rCmds[self.goToLastTab.__name__][index], self.goToLastTab.__doc__))
    
    def setCapo(self, uicKey=None, c=None):
        '''Place capo on fret specified by user input of a single character [0-9][a-o] [cmd line opt -k]'''
        self.printh('{}: {}'.format(uicKey, self.setCapo.__doc__))
        if c is None: c = getwch()
        print('setCapo({}, {}) c={}({}) prevCapo={} check isFret(c) BGN'.format(self.row, self.col, ord(c), c, self.capo), file=Tabs.DBG_FILE)
        if not Tabs.isFret(c): self.printe('[{}] not a fret num, enter the fret num as a single char [0-9][a-o]'.format(c))
        else:
            capFN = self.getFretNum(ord(c))
            maxFN = self.getFretNum(self.maxFretInfo['MAX'])
            print('setCapo() c={}({}) maxFret={}({}) check capFN:{} + maxFN:{} <= {}?'.format(ord(c), c, self.maxFretInfo['MAX'], chr(self.maxFretInfo['MAX']), capFN, maxFN, self.NUM_FRETS), file=Tabs.DBG_FILE)
            if capFN + maxFN > self.NUM_FRETS:
                info = 'setCapo() c={}({}) capo={} capFN:{} + maxFN:{} > {}!  maxFret={}({})'.format(ord(c), c, self.capo, capFN, maxFN, self.NUM_FRETS, self.maxFretInfo['MAX'], chr(self.maxFretInfo['MAX']))
                self.printe(info)
            else:
                self.capo = ord(c)
                print('setCapo() c={}({}) capo={} capFN={} maxFret={}({}) maxFN={} setting capo'.format(ord(c), c, self.capo, capFN, self.maxFretInfo['MAX'], chr(self.maxFretInfo['MAX']), maxFN), file=Tabs.DBG_FILE)
                self.printTabs()
    
    def setTab(self, tab, uicKey=None, dbg=0):
        '''Set and print tab byte at current row and col, auto move cursor'''
        row, col = self.row, self.col
        rr, cc = self.rowCol2Indices(row, col)
        s, ss = rr + 1, self.getOrdSfx(rr + 1)
        print('setTab({}, {}, {}, {}) tab={}({}), {}({}{}) string, bgn'.format(rr, cc, self.row, self.col, tab, chr(tab), self.getNote(s, 0).name, s, ss), file=Tabs.DBG_FILE)
        if self.bgnCol() > self.col > self.endCol() or self.ROW_OFF > self.row > self.ROW_OFF + self.numLines * self.lineDelta():
            return self.printe('row/col out of range setTab({} {}) row={} col={} tab={}({})'.format(rr, cc, self.row, self.col, tab, chr(tab)), x=1)
        if self.editMode == self.EDIT_MODES['INSERT']:
            print('setTab(INSERT) len={}'.format(len(self.tabs[rr])), file=Tabs.DBG_FILE)
            for c in range(len(self.tabs[rr]) - 1, cc, - 1):
                if dbg: print('setTab(INSERT) before: tab[{}]={} tab[{}]={}'.format(c-1, chr(self.tabs[rr][c - 1]), c, chr(self.tabs[rr][c])), end=' ', file=Tabs.DBG_FILE)
                self.tabs[rr][c] = self.tabs[rr][c - 1]
                self.htabs[rr][c] = self.htabs[rr][c - 1]
                if dbg: print('after: tab[{}]={} tab[{}]={}'.format(c-1, chr(self.tabs[rr][c - 1]), c, chr(self.tabs[rr][c])), file=Tabs.DBG_FILE)
            self.tabs[rr][cc] = tab
            self.printTabs()
        elif self.editMode == self.EDIT_MODES['REPLACE']:
            self.tabs[rr][cc] = tab
            self.prints(chr(tab), row, col, self.styles['TABS'])
            if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                if Tabs.isFret(chr(tab)):
                    capTab = self.getFretByte(self.getFretNum(tab) + self.getFretNum(self.capo))
                    if Tabs.isFret(chr(capTab)):
                        n = self.getNote(s, capTab)
                        print('setTab(DISPLAY_NOTES) tab={}({}) capTab={}({}) nn={}'.format(tab, chr(tab), capTab, chr(capTab), n.name), file=Tabs.DBG_FILE)
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
                        if dbg: self.dumpChordInfo(self.chordInfo, reason='setTab(DISPLAY_CHORDS) r={} cc={}'.format(r, cc))
                        noteCount += 1
                        if noteCount > 1:
                            print('setTab(DISPLAY_CHORDS) r={} increment noteCount={}'.format(r, noteCount), file=Tabs.DBG_FILE)
                            self.chordsObj.printChord(c=cc)
                            break
                        else: 
                            print('setTab(DISPLAY_CHORDS) r={} noteCount={}'.format(r, noteCount), file=Tabs.DBG_FILE)
            if self.displayIntervals == self.DISPLAY_INTERVALS['ENABLED']:
                irow = self.bgnRow(self.row2Line(row)) + self.numStrings + self.NOTES_LEN
                for r in range(self.numStrings):
                    self.printInterval(irow + r, col, '-', dbg=dbg)
                if dbg: self.dumpChordInfo(self.chordInfo, reason='setTab(DISPLAY_INTERVALS) irow={} line={} cc={}'.format(irow, self.colIndex2Line(cc), cc))
                if cc not in self.chordInfo:
                    print('setTab(DISPLAY_INTERVALS) row={} col={} ival={}'.format(row, col, 'R'), file=Tabs.DBG_FILE)
                    if Tabs.isFret(chr(tab)):
                        capTab = self.getFretByte(self.getFretNum(tab) + self.getFretNum(self.capo))
                        if Tabs.isFret(chr(capTab)):
                            self.printInterval(row + self.numStrings + self.NOTES_LEN, col, 'R', dbg=dbg)
                        else: print('setTab(DISPLAY_INTERVALS) NOT a Fret capTab={}'.format(chr(capTab)), file=Tabs.DBG_FILE)
                else:
                    for r in range(self.numStrings):
                        self.wrapPrintInterval(r, cc, dbg=dbg)
        info = 'setTab() set tab={}({}) at ({}, {})'.format(tab, chr(tab), self.rowCol2Indices(row, col)[0], self.rowCol2Indices(row, col)[1])
        self.printh('{}: {}'.format(self.rCmds['setTab'], info))
        self.moveCursor()
        self.getMaxFretInfo()
        if dbg: self.dumpTabs('setTab() end')
    
    def deleteTab(self, uicKey=None, back=0, dbg=0):
        '''Delete current tab setting it back to '-', with automatic cursor movement, wrapping across edges'''
        row, col = self.row, self.col
        print('deleteTab(row={} col={} back={}) bgn'.format(row, col, back), file=Tabs.DBG_FILE)
        if self.editMode == self.EDIT_MODES['INSERT']:
            r, c = self.rowCol2Indices(row, col)
            print('deleteTab(row={} col={} back={}) r={} c={} [INSERT]'.format(row, col, back, r, c), file=Tabs.DBG_FILE)
            for cc in range(c, len(self.tabs[r]) - 1):
                self.tabs[r][cc]  = self.tabs[r][cc + 1]
                self.htabs[r][cc] = self.htabs[r][cc + 1]
            cc = len(self.tabs[r]) - 1
            self.tabs[r][cc]  = ord('-')
            self.htabs[r][cc] = ord('0')
#            if back == 1: self.moveLeft()
            self.moveCursor(row=row, col=col, back=back)
            if back == 1: return
            self.printTabs()
        elif self.editMode == self.EDIT_MODES['REPLACE']:
            print('deleteTab(row={} col={} back={}) [REPLACE]'.format(row, col, back), file=Tabs.DBG_FILE)
            self.moveCursor(row=row, col=col, back=back)
            if back == 1: return
            self._deleteTab(row, col)
        self.getMaxFretInfo()
        self.printStatus()
        self.printh('{}: {}'.format(uicKey, self.deleteTab.__doc__))
    
    def deletePrevTab(self, uicKey=None, dbg=0):
        '''Delete previous tab (i.e. backspace) position depends on cursor mode'''
        self.deleteTab(back=1)
        row, col = self.row, self.col
        self._deleteTab(row, col)
        self.printStatus()
        self.printh('{}: {}'.format(uicKey, self.deletePrevTab.__doc__))
    
    def _deleteTab(self, row, col, rmv=1, dbg=0):
        r, c = self.rowCol2Indices(row, col)
        print('_deleteTab({} {} {} {}) rmv={} resetting tab to -/0 bgn'.format(row, col, r, c, rmv), file=Tabs.DBG_FILE)
        self.tabs[r][c] = ord('-')
        self.htabs[r][c] = ord('0')
        if rmv == 1 and c in self.chordInfo:
            if dbg: print('_deleteTab() deleting chordInfo[{}]={}'.format(c, self.chordInfo[c]), file=Tabs.DBG_FILE)
            del self.chordInfo[c]
            if dbg: self.dumpChordInfo(self.chordInfo, reason='_deleteTab()')
        self.prints(chr(self.tabs[r][c]), row, col, self.styles['TABS'])
        if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
            self.prints(chr(self.tabs[r][c]), row + self.numStrings, col, self.styles['NAT_NOTE'])
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.chordsObj.eraseChord(c, rmv=rmv)
            self.chordsObj.printChord(c=c)
        if self.displayIntervals == self.DISPLAY_INTERVALS['ENABLED']:
            self.printColumnIvals(c, dbg=dbg)
    
    def eraseTabs(self, uicKey=None):
        '''Erase all tabs and all corresponding notes, intervals, and chords (resets all tabs to '-')'''
        print('eraseTabs() deleting chordAliases={} analyzeIndices={}'.format(self.chordAliases, self.analyzeIndices), file=Tabs.DBG_FILE)
        self.chordAliases = {}
        self.analyzeIndices = {}
        print('eraseTabs() chordAliases={} analyzeIndices={} setting all tabs to - and htabs to 0'.format(self.chordAliases, self.analyzeIndices), file=Tabs.DBG_FILE)
        for r in range(0, len(self.tabs)):
            for c in range(0, len(self.tabs[r])):
                self.tabs[r][c] = ord('-')
                self.htabs[r][c] = ord('0')
                if c in self.chordInfo:
                    print('eraseTabs() deleting chordInfo[{}]={}'.format(c, self.chordInfo[c]), file=Tabs.DBG_FILE)
                    del self.chordInfo[c]
        self.maxFretInfo['MAX'] = ord('0')
        self.printTabs()
        self.printh('{}: {}'.format(uicKey, self.eraseTabs.__doc__))
    
    def resetTabs(self, uicKey=None):
        '''Reset all tabs to their initial state at start up by re-reading the data file'''
        self.init()
        self.getMaxFretInfo()
        self.printh('{}: {}'.format(uicKey, self.resetTabs.__doc__))
    
    def saveTabs(self, uicKey=None):
        '''Save tabs and ANSI codes to output file, the 'cat' cmd can be used to view the file'''
        with open(self.outName, 'w') as self.outFile:
            self.dumpLineInfo('saveTabs({}, {}) bgn writing tabs to file type={}'.format(self.row, self.col, self.outFile))
            Tabs.clearScreen(file=self.outFile, reason='saveTabs()')
            print(self.cmdLine, file=self.outFile)
            print('cmdLineArgs:', file=self.outFile)
            for k in self.argMap:
                print('    {}={}'.format(k, self.argMap[k]), file=self.outFile)
            self.printStringMap(file=self.outFile)
            self.saveOrdDict(self.chordAliases, 'StartChordAliases', q='\'')
            self.saveOrdDict(self.analyzeIndices, 'StartAnalyzeIndices')
            self.printTabs()
            self.moveTo(hi=1)
            print(Tabs.CSI + self.styles['NORMAL'] + self.styles['CONS'] + Tabs.CSI + '{};{}H'.format(self.lastRow, 1), end='', file=self.outFile) # set the file cursor to the front of the next row (NUM_STR+r+1, 0) and set the foreground and background color
            self.dumpTabs('saveTabs(h)', h=1)
            self.dumpLineInfo('saveTabs({}, {}) end writing tabs to file'.format(self.row, self.col))
        self.outFile = None
        self.printTabs()
        self.printh('{}: {}'.format(uicKey, self.saveTabs.__doc__))
    
    def saveOrdDict(self, d, reason, q=''):
        print('{}'.format(reason), file=self.outFile)
        print('{', end='', file=self.outFile)
        for k in sorted(d):
            print('{}: {}{}{}'.format(k, q, d[k], q), end=', ', file=self.outFile)
        print('}', file=self.outFile)
    
    def selectRow(self, uicKey=None, up=0):
        '''Select row, append to selected rows list, hilite current tab, and go up or down to next tab'''
        row, col, r, c, br, er = self.row, self.col, self.row2Index(self.row), self.col2Index(self.col), self.bgnRow(self.row2Line(self.row)), self.endRow(self.row2Line(self.row))
        print('selectRow(up={}) ({},{}) bgn r={} c={} selectRows={} selectCols={} br={} er={}'.format(up, row, col, r, c, self.selectRows, self.selectCols, br, er), file=Tabs.DBG_FILE)
        if len(self.selectRows) < self.numStrings:
            self.selectRows.append(r)
            self.selectCols.append(c)
            print('selectRow(up={}) ({},{}) after appending r={} c={} selectRows={} selectCols={}'.format(up, row, col, r, c, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
            self.selectStyle(c, self.styles['BRIGHT'], rList=self.selectRows)
        if up == 1 and row == br or up == 0 and row == er:
            if up: dir, pos = 'up', 'bgn'
            else:  dir, pos = 'down', 'end'
            self.printe('selectRow(up={}) ignoring cursor movement, because dir={} and row={} == {}Row'.format(up, dir, row, pos))
            return
        if up: self.moveUp()
        else:  self.moveDown()
        self.printh('{}: {}'.format(uicKey, self.selectRow.__doc__))
    
    def unselectRow(self, uicKey=None, up=0):
        '''Unselect row, remove it from selected rows list, unhilite current tab, go up or down to next tab'''
        r = self.row2Index(self.row)
        c = self.col2Index(self.col)
        if len(self.selectRows):
            print('unselectRow(up={}) ({},{}) checking if r={} c={} in selectRows={} selectCols={}'.format(up, self.row, self.col, r, c, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
            if r in self.selectRows:
                print('unselectRow(up={}) ({},{}) before removing r={} c={} from selectRows={} selectCols={}'.format(up, self.row, self.col, r, c, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
                self.selectRows.remove(r)
                print('unselectRow(up={}) ({},{}) after removing r={} c={} from selectRows={} selectCols={}'.format(up, self.row, self.col, r, c, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
                self.selectStyle(c, self.styles['NORMAL'], r=r)
                if up: self.moveUp()
                else:  self.moveDown()
            else: self.printe('unselectRow(up={}) ({},{}) nothing to unselect r={} not in selectRows={} selectCols={}'.format(up, self.row, self.col, r, self.selectRows, self.selectCols))
        else: self.printe('unselectRow(up={}) ({},{}) empty list, nothing to unselect r={} selectRows={} selectCols={}'.format(up, self.row, self.col, r, self.selectRows, self.selectCols))
        self.printh('{}: {}'.format(uicKey, self.unselectRow.__doc__))
    
    def selectCol(self, uicKey=None, left=0):
        '''Select col, append to selected cols list, hilite current tab, go left or right to next tab'''
        cc = self.col2Index(self.col)
        print('selectCol(left={}) ({},{}), cc={} selectFlag={} selectRows={} selectCols={}'.format(left, self.row, self.col, cc, self.selectFlag, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
        if len(self.selectRows) == 0:
            self.selectFlag = 1
            for r in range(0, self.numStrings):
                self.selectRows.append(r)
            print('selectCol(left={}) ({},{}) appended all rows cc={} selectFlag={} selectRows={} selectCols={}'.format(left, self.row, self.col, cc, self.selectFlag, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
        elif self.selectFlag == 0:
            self.selectFlag = 1
            for c in range(0, len(self.selectCols)):
                self.selectStyle(c, self.styles['NORMAL'], rList=self.selectRows)
            self.selectCols = []
            print('selectCol(left={}) ({},{}) removed all cols cc={} selectFlag={} selectRows={} selectCols={}'.format(left, self.row, self.col, cc, self.selectFlag, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
        self.selectCols.append(cc)
        print('selectCol(left={}) ({},{}) appended cc={} selectFlag={} selectRows={} selectCols={}'.format(left, self.row, self.col, cc, self.selectFlag, self.selectRows, self.selectCols), file=Tabs.DBG_FILE)
        self.selectStyle(cc, self.styles['BRIGHT'], rList=self.selectRows)
        if left: self.moveLeft()
        else:    self.moveRight()
        self.printh('{}: {}'.format(uicKey, self.selectCol.__doc__))
    
    def unselectCol(self, uicKey=None, left=0):
        '''Unselect col, remove it from selected cols list, unhilite tab, and go left or right to next tab'''
        c = self.col2Index(self.col)
        print('unselectCol(left={}) ({},{}) c={} checking len(selectCols)={}'.format(left, self.row, self.col, c, len(self.selectCols)), file=Tabs.DBG_FILE)
        if len(self.selectCols):
            print('unselectCol(left={}) ({},{}) checking if c={} in selectCols={}'.format(left, self.row, self.col, c, self.selectCols), file=Tabs.DBG_FILE)
            if c in self.selectCols:
                print('unselectCol(left={}) ({},{}) before removing c={} from selectCols={}'.format(left, self.row, self.col, c, self.selectCols), file=Tabs.DBG_FILE)
                self.selectCols.remove(c)
                print('unselectCol(left={}) ({},{}) after removing c={} from selectCols={}'.format(left, self.row, self.col, c, self.selectCols), file=Tabs.DBG_FILE)
                self.selectStyle(c, self.styles['NORMAL'], rList=self.selectRows)
                if left: self.moveLeft()
                else:    self.moveRight()
            else: self.printe('unselectCol(left={}) ({},{}) c={} not in selectCols={}, nothing to unselect'.format(left, self.row, self.col, c, self.selectCols))
        else: self.printe('unselectCol(left={}) ({},{}) selectCols={}, empty list, nothing to unselect'.format(left, self.row, self.col, self.selectCols))
        self.printh('{}: {}'.format(uicKey, self.unselectCol.__doc__))
    
    def unselectAll(self, uicKey=None):
        '''Unselect all rows and columns.'''
        print('unselectAll({},{}) bgn selectFlag={} selectRows={} selectCols={} selectTabs={}'.format(self.row, self.col, self.selectFlag, self.selectRows, self.selectCols, self.selectTabs), file=Tabs.DBG_FILE)
        for c in range(0, len(self.selectCols)):
            self.selectStyle(self.selectCols[c], self.styles['NORMAL'], rList=self.selectRows)
        self.selectRows, self.selectCols, self.selectTabs, self.selectHTabs, self.selectFlag = [], [], [], [], 0
        print('unselectAll({},{}) end selectFlag={} selectRows={} selectCols={} selectTabs={}'.format(self.row, self.col, self.selectFlag, self.selectRows, self.selectCols, self.selectTabs), file=Tabs.DBG_FILE)
        self.printh('{}: {}'.format(uicKey, self.unselectAll.__doc__))
    
    def selectStyle(self, c, bStyle, rList=None, r=None):
        print('selectStyle({}) c={}, rList={}, r={}'.format(bStyle, c, rList, r), file=Tabs.DBG_FILE)
        if rList is not None and r is None:
            for rr in range(0, len(rList)):
                r = rList[rr]
                self.selectRowStyle(r, c, bStyle)
        elif rList is None and r is not None:
            self.selectRowStyle(r, c, bStyle)
    
    def selectRowStyle(self, r, c, bStyle, dbg=0):
        tab = self.tabs[r][c]
        row, col = self.indices2RowCol(r, c)
        print('selectRowStyle({}) r={} c={} row={} col={} tabc={}'.format(bStyle, r, c, row, col, chr(tab)), file=Tabs.DBG_FILE)
        if self.htabs[r][c] == ord('1'):
            self.prints(chr(tab), row, col, bStyle + self.styles['H_TABS'])
        else:
            self.prints(chr(tab), row, col, bStyle + self.styles['TABS'])
        if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
            if dbg: print('selectRowStyle(DISPLAY_NOTES) bStyle={}'.format(bStyle), file=Tabs.DBG_FILE)
            if Tabs.isFret(chr(tab)):
                if self.htabs[r][c] == ord('1'):
                    n = self.getHarmonicNote(r + 1, tab)
                    self.printNote(row + self.numStrings, col, n, bStyle, hn=1)
                else:
                    n = self.getNote(r + 1, tab)
                    self.printNote(row + self.numStrings, col, n, bStyle)
            else:
                self.prints(chr(tab), row + self.numStrings, col, bStyle + self.styles['NAT_NOTE'])
        if self.displayIntervals == self.DISPLAY_INTERVALS['ENABLED']:
            if dbg: print('selectRowStyle(DISPLAY_INTERVALS) bStyle={}'.format(bStyle), file=Tabs.DBG_FILE)
            self.printInterval(row + self.numStrings + self.NOTES_LEN, col, '-', bStyle, dbg=1)
            if c in self.chordInfo:
                self.wrapPrintInterval(r, c, bStyle, dbg=0)
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.chordsObj.printChord(c, bStyle=bStyle)
    
    def shiftSelectTabs(self, uicKey=None):
        '''Shift selected tabs up or down # frets,  user input of up to 2 digits terminated by space [-10 ]'''
        self.printh('{}: {}'.format(uicKey, self.shiftSelectTabs.__doc__))
        c, tmp = '', []
        while len(tmp) <= 3:
            c = getwch()
            if c != '-' and c != ' ' and not c.isdigit():
                self.printe('shiftSelectTabs() char out of range 0-9 or \'-\' or \' \' c={}({})'.format(c, ord(c)))
                self.unselectAll()
                return
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
        self.maxFretInfo['MAX'] += shift
    
    def copySelectTabs(self, uicKey=None, arpg=None):
        '''Copy selected tabs, arpg=1 xform a chord to an arpeggio, arpg=0 xform an arpeggio to a chord'''
        self.arpeggiate, ns, nt, nsr, nsc = arpg, self.numStrings, len(self.tabs[0]), len(self.selectRows), len(self.selectCols)
        if nsr == 0 or nsc == 0:
            self.printe('copySelectTabs(arpg={}) no tabs selected nsr={} nsc={} use the CTRL ARROW keys to select rows and or columns'.format(arpg, nsr, nsc))
            return
        if arpg is None: size, nc = nsc,           nsc
        elif  arpg == 1: size, nc = nsc * nsr,     nsc
        elif  arpg == 0: size, nc = int(nsc / ns), int(nsc / ns)
        self.dumpSelectTabs(reason='copySelectTabs()', cols=1)
        for r in range(0, nsr):
            self.selectTabs.append(bytearray([ord(' ')] * size))
            self.selectHTabs.append(bytearray([ord('0')] * size))
        nst = len(self.selectTabs[0])
        print('copySelectTabs({},{}) row={} col={} ns={} nsr={} nsc={} nt={} nst={} nc={}'.format(arpg, self.cursorDir, self.row, self.col, ns, nsr, nsc, nt, nst, nc), file=Tabs.DBG_FILE)
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
                print('copySelectTabs({},{}) r={} rr={} c={} cc={} cst={} ct={} '.format(arpg, self.cursorDir, r, rr, c, cc, cst, ct), end='', file=Tabs.DBG_FILE)
                self.selectTabs[r][cst]  = self.tabs[rr][ct]
                self.selectHTabs[r][cst] = self.htabs[rr][ct]
                print('copySelectTabs() selectTabs[{}][{}]={} tabs[{}][{}]={}'.format(r, cst, chr(self.selectTabs[r][cst]), rr, ct, chr(self.tabs[rr][ct])), file=Tabs.DBG_FILE)
            self.copyColInfo(ct)
            self.dumpSelectTabs(reason='copySelectTabs()')
        self.printh('{}: {}'.format(uicKey, self.copySelectTabs.__doc__))
    
    def copyColInfo(self, c):
        self.dumpInfo('copyColInfo(c={})'.format(c))
        if c in self.chordAliases:
            print('copyColInfo() FOUND c={} in chordAliases[{}]={}'.format(c, c, self.chordAliases[c]), file=Tabs.DBG_FILE)
            self.selectChordAliases[c] = self.chordAliases[c]
            del self.chordAliases[c]
        else: self.selectChordAliases[c] = None
        if c in self.analyzeIndices:
            print('copyColInfo() FOUND c={} in analyzeIndices[{}]={}'.format(c, c, self.analyzeIndices[c]), file=Tabs.DBG_FILE)
            self.selectAnalyzeIndices[c] = self.analyzeIndices[c]
            del self.analyzeIndices[c]
        else: self.selectAnalyzeIndices[c] = None
        print('copyColInfo() selectChordAliases={} selectAnalyzeIndices={}'.format(self.selectChordAliases, self.selectAnalyzeIndices), file=Tabs.DBG_FILE)
    
    def deleteSelectTabs(self, uicKey=None, rmv=1):
        '''Delete selected tabs and all corresponding notes, intervals, and chords, resets all tabs to [-]'''
        self.dumpLineInfo('deleteSelectTabs({}, {}) rmv={} selectCols={}'.format(self.row, self.col, rmv, self.selectCols))
        self.selectCols.sort(key = int, reverse = True)
        for c in range(0, len(self.selectCols)):
            print('deleteSelectTabs() c={}'.format(c), file=Tabs.DBG_FILE)
            self.deleteTabsCol(self.selectCols[c], rmv=rmv)
        if rmv == 1:
            self.selectCols = []
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.chordsObj.printChords()
        self.getMaxFretInfo()
        self.printh('{}: {}'.format(uicKey, self.deleteSelectTabs.__doc__))
    
    def cutSelectTabs(self, uicKey=None, arpg=None):
        '''Cut selected tabs keeping in memory for a corresponding paste cmd in the future'''
        print('cutSelectTabs() arpg={}'.format(arpg), file=Tabs.DBG_FILE)
        self.copySelectTabs(arpg=arpg)
        self.deleteSelectTabs(rmv=0)
        self.printh('{}: {}'.format(uicKey, self.cutSelectTabs.__doc__))
    
    def dumpSelectTabs(self, reason='', cols=0):
        print('dumpSelectTabs(cols={}, reason={}) len(selectCols)={} len(selectTabs)={}'.format(cols, reason, len(self.selectCols), len(self.selectTabs)), file=Tabs.DBG_FILE)
        if cols:
            for c in range(0, len(self.selectCols)):
                print('    selectCols[{}]={}'.format(c, self.selectCols[c]), file=Tabs.DBG_FILE)
        for c in range(0, len(self.selectTabs)):
            print('    selectTabs[{}]={}'.format(c, self.selectTabs[c]), file=Tabs.DBG_FILE)
    
    def deleteTabsCol(self, cc, rmv=1, dbg=0):
        row, col = self.indices2RowCol(0, cc)
        print('deleteTabsCol({}) rmv={} row={} col={}'.format(cc, rmv, row, col), file=Tabs.DBG_FILE)
        if dbg: self.dumpTabs('deleteTabsCol({}, {}) row={} col={} cc={} bgn: '.format(self.row, self.col, row, col, cc))
        if self.editMode == self.EDIT_MODES['INSERT']:
            print('deleteTabsCol(INSERT)'.format(cc, row, col), file=Tabs.DBG_FILE)
            if cc in self.chordInfo:
                print('deleteTabsCol() deleting chordInfo[{}]={}'.format(cc, self.chordInfo[cc]), file=Tabs.DBG_FILE)
                del self.chordInfo[cc]
            self.dumpChordInfo(self.chordInfo, reason='deleteTabsCol()')
            for r in range(0, self.numStrings):
                for c in range(cc, len(self.tabs[r]) - 1):
                    self.tabs[r][c] = self.tabs[r][c + 1]
                    self.htabs[r][c] = self.htabs[r][c + 1]
                    if r == 0 and c+1 in self.chordInfo:
                        self.chordInfo[c] = self.chordInfo[c + 1]
                        del self.chordInfo[c + 1]
            self.printTabs()
        elif self.editMode == self.EDIT_MODES['REPLACE']:
            print('deleteTabsCol(REPLACE)'.format(cc, row, col), file=Tabs.DBG_FILE)
            for r in range(0, self.numStrings):
                self._deleteTab(row + r, col, rmv=rmv)
        if dbg: self.dumpTabs('deleteTabsCol({}, {}) col={} end: '.format(self.row, self.col, col))
        self.getMaxFretInfo()
    
    def _initPasteInfo(self):
        nc, rangeError, row, col, rr, cc = 0, 0, self.row, self.col, 0, 0
        line, ns, nt, nsr, nsc, nst = self.row2Line(self.row), self.numStrings, len(self.tabs[0]), len(self.selectRows), len(self.selectCols), len(self.selectTabs)
        if nst == 0:
            self.printe('_initPasteInfo() no tabs to paste nsr={} nsc={} nst={} use CTRL/SHIFT C or X to copy or cut selected tabs'.format(nsr, nsc, nst))
            return rangeError, nc, row, col, self.row2Index(row), cc, line, ns, nt, nsr, nsc, nst
        nst, br, er = len(self.selectTabs[0]), self.bgnRow(line), self.endRow(line)
        print('_initPasteInfo({},{}) ({},{}) bgn ns={} nt={} nsr={} nsc={} nst={} line={} br={} er={}'.format(self.arpeggiate, self.cursorDir, row, col, ns, nt, nsr, nsc, nst, line, br, er), file=Tabs.DBG_FILE)
        while row + nsr - 1 > er:
            row -= 1
            if row < br: self.printe('_initPasteInfo() tried to adjust row={} < br={}, nsr={}'.format(row, br, nsr))
            print('_initPasteInfo(--row) row={} + nsr={} - 1 <= er={}'.format(row, nsr, er), file=Tabs.DBG_FILE)
        rr, cc = self.rowCol2Indices(row, col)
        if self.arpeggiate is None: nc = nsc
        else:                       nc = nst
        print('_initPasteInfo({},{}) row={} col={} rr={} cc={} nc={}'.format(self.arpeggiate, self.cursorDir, row, col, rr, cc, nc), file=Tabs.DBG_FILE)
        if self.editMode == self.EDIT_MODES['INSERT']:
            for c in range(nt - 1, cc - 1, -1):
                for r in range(0, nsr):
                    if c >= nc + cc:
                        self.tabs[r][c] = self.tabs[r][c - nc]
                        self.htabs[r][c] = self.htabs[r][c - nc]
                        print('_initPasteInfo(INSERT) c={} >= cc={} + nc={}, tabs[{}][{}]={}'.format(c, cc, nc, r, c, chr(self.tabs[r][c])), file=Tabs.DBG_FILE)
                    elif self.arpeggiate:
                        self.tabs[r][c] = ord('-')
                        self.htabs[r][c] = ord('0')
                        print('_initPasteInfo(INSERT) c={} < cc={} + nst={}, tabs[{}][{}]={}'.format(c, cc, nst, r, c, chr(self.tabs[r][c])), file=Tabs.DBG_FILE)
        elif self.editMode == self.EDIT_MODES['REPLACE'] and self.arpeggiate and cc + nst < nt:
            for c in range(cc, cc + nst):
                for r in range(0, nsr):
                    self.tabs[r][c] = ord('-')
                    self.htabs[r][c] = ord('0')
                    print('_initPasteInfo(REPLACE) tabs[{}][{}]={}'.format(r, c, chr(self.tabs[r][c])), file=Tabs.DBG_FILE)
        for c in range(0, nsc):
            if rangeError: break
            for r in range(0, nsr):
                if self.arpeggiate == 1:
                    if   self.cursorDir == self.CURSOR_DIRS['DOWN']: ccc = c * nsr + r
                    elif self.cursorDir == self.CURSOR_DIRS['UP']:   ccc = (c + 1) * nsr - r - 1
                else: ccc = c
                print('_initPasteInfo(check) r={} rr={} c={} cc={} ccc={} nt={} nst={}'.format(r, rr, c, cc, ccc, nt, nst), end='', file=Tabs.DBG_FILE)
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
            self.pasteColInfo(c, cc, ccc)
            if not rangeError: self.selectStyle(self.selectCols[c], self.styles['NORMAL'], rList=self.selectRows)
        self.selectChordAliases, self.selectAnalyzeIndices = {}, {}
        return rangeError, nc, row, col, rr, cc, line, ns, nt, nsr, nsc, nst
    
    def pasteColInfo(self, c, cc, ccc):
        sc = self.selectCols[c]
        self.dumpInfo('pasteColInfo(c={} cc={} ccc={} sc={}) selectCols={}'.format(c, cc, ccc, sc, self.selectCols))
        if self.selectChordAliases[sc] != None:
            self.chordAliases[ccc + cc] = self.selectChordAliases[sc]
            print('pasteColInfo() chordAliases={}'.format(self.chordAliases), file=Tabs.DBG_FILE)
        if self.selectAnalyzeIndices[sc] != None:
            self.analyzeIndices[ccc + cc] = self.selectAnalyzeIndices[sc]
            print('pasteColInfo() analyzeIndices={}'.format(self.analyzeIndices), file=Tabs.DBG_FILE)
    
    def pasteSelectTabs(self, uicKey=None, dbg=0):
        '''Paste selected tabs as is or either stretched in time like arpeggio or compressed like a chord'''
        rangeError, nc, row, col, rr, cc, line, ns, nt, nsr, nsc, nst = self._initPasteInfo()
        if nst == 0: return
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.chordsObj.printChords()
        if self.editMode == self.EDIT_MODES['INSERT']:
            self.printTabs()
        elif self.editMode == self.EDIT_MODES['REPLACE']:
            print('pasteSelectTabs(REPLACE) cc={} nc={}'.format(cc, nc), file=Tabs.DBG_FILE)
            for c in range(cc, cc + nc):
                if c >= len(self.tabs[0]):
                    self.printe('pasteSelectTabs() c={} + nc={} >= len(tabs[0])={} skip remaining columns'.format(c, nc, len(self.tabs[0])))
                    break
                col = self.index2Col(c)
                if c % self.numTabsPerStringPerLine == 0:
                    row += self.lineDelta()
                    if dbg: print('pasteSelectTabs(wrap) row={} col={} c={}'.format(row, col, c), file=Tabs.DBG_FILE)
                for r in range(rr, rr + nsr):
                    row = self.indices2Row(r, c)
                    tab = self.tabs[r][c]
                    if dbg: print('pasteSelectTabs(loop2) row={} col={} r={} c={} tabc[{}][{}]={}'.format(row, col, r, c, r, c, chr(tab)), file=Tabs.DBG_FILE)
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
                        if dbg: print('pasteSelectTabs(INTERVALS) row={} col={} r={} c={} cc={} tab={} selectCols={}'.format(row, col, r, c, cc, chr(tab), self.selectCols), file=Tabs.DBG_FILE)
                        self.printInterval(row + self.numStrings + self.NOTES_LEN, col, '-', dbg=0)
                        if c in self.chordInfo:
                            self.wrapPrintInterval(r, c, dbg=dbg)
            self.printStatus()
        if not rangeError:
            self.selectTabs, self.selectHTabs, self.selectCols, self.selectRows = [], [], [], []
        self.arpeggiate, self.selectFlag = 0, 0
        self.dumpTabs('pasteSelectTabs({},{}) end row={} col={}'.format(self.arpeggiate, self.cursorDir, row, col))
        self.getMaxFretInfo()
        self.printh('{}: {}'.format(uicKey, self.pasteSelectTabs.__doc__))
    
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
    
    def dumpLineInfo(self, reason):
        print('{} maxFN={}({}) numStrings={} numLines={} lineDelta={}'.format(reason, self.maxFretInfo['MAX'], chr(self.maxFretInfo['MAX']), self.numStrings, self.numLines, self.lineDelta()), end='', file=Tabs.DBG_FILE)
        for line in range(0, self.numLines):
            print(' bgnRow{}={} endRow{}={}'.format(line, self.bgnRow(line), line, self.endRow(line)), end='', file=Tabs.DBG_FILE)
        print(' ROW_OFF={} lastRow={} bgnCol={} endCol={} line={}'.format(self.ROW_OFF, self.lastRow, self.bgnCol(), self.endCol(), self.row2Line(self.row)), file=Tabs.DBG_FILE)
    
    def printTabs(self, uicKey=None, cs=0):
        '''Print all labels, tabs, notes, intervals, and chords for every string on every line'''
        self.dumpLineInfo('printTabs(cs={}) bgn outFile={}'.format(cs, self.outFile))
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
                        self.prints(chr(self.capo), row, self.cursorModeCol, self.cursorDirStyle)
                    self.prints(chr(tab), row, c + self.COL_OFF, style)
                print(file=self.outFile)
            print()
        self.printFileMark('<END_TABS_SECTION>')
        if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
            self.printNotes()
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.chordsObj.printChords()
        if self.displayIntervals == self.DISPLAY_INTERVALS['ENABLED']:
            self.printIntervals(dbg=1)
        if self.displayLabels == self.DISPLAY_LABELS['ENABLED']:
            self.printLabels()
        if self.row > 0 and self.col > 0:
            print(Tabs.CSI + self.styles['NORMAL'] + self.styles['CONS'] + Tabs.CSI + '{};{}H'.format(self.row, self.col), end='') # restore the console cursor to the given position (row, col) and set the foreground and background color
        self.printStatus()
        self.dumpLineInfo('printTabs(cs={}) end outFile={}'.format(cs, self.outFile))
        self.printh('{}: {}'.format(uicKey, self.printTabs.__doc__))
    
    def printFileMark(self, mark):
        if self.outFile != None:
            if mark == '<BGN_TABS_SECTION>' or mark == '<END_TABS_SECTION>':
                print('{}'.format(mark), file=self.outFile)
            else:
                print(Tabs.CSI + self.styles['NORMAL'] + self.styles['CONS'] + Tabs.CSI + '{};{}H{}'.format(1, 1, mark), file=self.outFile)
    
    def printNotes(self, dbg=0):
        self.printFileMark('<BGN_NOTES_SECTION>')
        for line in range(0, self.numLines):
            for r in range(0, self.numStrings):
                row = r + line * self.lineDelta() + self.endRow(0) + 1
                for c in range (0, self.numTabsPerStringPerLine):
                    cc = c + line * self.numTabsPerStringPerLine
                    capTab = tab = self.tabs[r][cc]
                    if dbg and line == 0 and c == 0: print('printNotes() r={} tab={}({}) captab={}({}) bgn'.format(r, tab, chr(tab), capTab, chr(capTab)), file=Tabs.DBG_FILE)
                    if Tabs.isFret(chr(tab)):
                        capTab = self.getFretByte(self.getFretNum(tab) + self.getFretNum(self.capo))
                    if c == 0:
                        n = self.getNote(r + 1, ord('0'))
                        self.printNote(row, self.editModeCol, n)
                        self.prints(chr(self.capo), row, self.cursorModeCol, self.cursorDirStyle)
                    if Tabs.isFret(chr(capTab)):
                        if chr(self.htabs[r][cc]) == '1':
                            print('printNotes() r={} tab={}({}) captab={}({}) tabFN={} capFN={}'.format(r, tab, chr(tab), capTab, chr(capTab), self.getFretNum(tab), self.getFretNum(capTab)), file=Tabs.DBG_FILE)
                            n = self.getHarmonicNote(r + 1, capTab)
                            self.printNote(row, c + self.COL_OFF, n, hn=1)
                        else:
                            n = self.getNote(r + 1, capTab)
                            self.printNote(row, c + self.COL_OFF, n)
                    else: self.prints(chr(capTab), row, c + self.COL_OFF, self.styles['NAT_NOTE'])
                print(file=self.outFile)
            print()
        self.printFileMark('<END_NOTES_SECTION>')
    
    def printNote(self, row, col, n, bStyle='', hn=None, dbg=0):
        if dbg: print('printNote() row={},col={}, nn={}'.format(row, col, n.name), file=Tabs.DBG_FILE)
        style = self.getNoteStyle(n, bStyle, hn)
        self.prints(n.name[0], row, col, style)
    
    def getNoteStyle(self, n, bStyle, hn=None):
        if hn is None:
            natStyle = bStyle + self.styles['NAT_NOTE']
            fltStyle = bStyle + self.styles['FLT_NOTE']
            shpStyle = bStyle + self.styles['SHP_NOTE']
        else:
            natStyle = bStyle + self.styles['NAT_H_NOTE']
            fltStyle = bStyle + self.styles['FLT_H_NOTE']
            shpStyle = bStyle + self.styles['SHP_H_NOTE']
        return self.getEnharmonicStyle(n.name, natStyle, fltStyle, shpStyle)
    
    def getEnharmonicStyle(self, name, defStyle, flatStyle, sharpStyle):
        if len(name) > 1:
            if name[1] == 'b':
                if self.enharmonic == self.ENHARMONICS['FLAT']:  return flatStyle
                else:                                            return sharpStyle
            elif name[1] == '#':
                if self.enharmonic == self.ENHARMONICS['SHARP']: return sharpStyle
                else:                                            return flatStyle
        return defStyle
    
    def printIntervals(self, dbg=1):
        self.printFileMark('<BGN_INTERVALS_SECTION>')
        for line in range(0, self.numLines):
            for r in range(0, self.numStrings):
                row = r + self.bgnRow(line) + self.numStrings + self.NOTES_LEN
                self.prints(self.IVAL_LABEL[r], row, 1, self.styles['IVAL_LABEL'])
                self.prints(chr(self.capo), row, self.cursorModeCol, self.cursorDirStyle)
                for c in range(self.COL_OFF, self.COL_OFF):
                    self.prints(' ', row, c, self.styles['IVAL_LABEL'])
            for c in range (0, self.numTabsPerStringPerLine):
                cc = c + line * self.numTabsPerStringPerLine
                self.printColumnIvals(cc, dbg=0)
        self.printFileMark('<END_INTERVALS_SECTION>')
    
    def printColumnIvals(self, c, dbg=0):
        line = self.colIndex2Line(c)
        if dbg and c==0: print('printColumnIvals({}) bgn line={} selectChords={}'.format(c, line, self.selectChords), file=Tabs.DBG_FILE)
        for r in range(0, self.numStrings):
            row = r + self.bgnRow(line) + self.numStrings + self.NOTES_LEN
            cc = c % self.numTabsPerStringPerLine
            self.prints('-', row, cc + self.COL_OFF, self.styles['NAT_IVAL'])
            if dbg and r == 0 and c == 0:
                self.dumpChordInfo(self.chordInfo, reason='printColumnIvals({} {}) line={} r={} row={}'.format(c, cc, line, r, row))
                if c in self.chordInfo: self.dumpLimap(self.chordInfo[c]['LIMAP'], reason='printColumnIvals() c={}'.format(c))
            if c in self.chordInfo: 
                self.wrapPrintInterval(r, c, dbg=0)
    
    def wrapPrintInterval(self, r, c, bStyle='', dbg=0):
        if c in self.analyzeIndices: index = self.analyzeIndices[c]
        else:                        index = 0
        if dbg: print('wrapPrintInterval({:>3} {}) bgn'.format(c, index), file=Tabs.DBG_FILE)
        imap = self.chordInfo[c]['LIMAP'][index]
        imapstr = self.map2String(imap)
        if dbg: print('wrapPrintInterval({:>3} {}) imap={} CHECKING IF imapstr={} IN selectImaps={}'.format(c, index, imap, imapstr, self.selectImaps), file=Tabs.DBG_FILE)
        if imapstr in self.selectImaps:
            imap = self.selectImaps[imapstr]
            if dbg and r == 0:
                print('wrapPrintInterval({:>3} {}) imap={}        FOUND imapstr={} in'.format(c, index, imap, imapstr), end=' ', file=Tabs.DBG_FILE)
                self.dumpSelectImaps()
                print('wrapPrintInterval({:>3} {}) imap={} SWAP MAP K&V imapstr={}'.format(c, index, imap, self.map2String(imap)), file=Tabs.DBG_FILE)
        im = {imap[k]:k for k in imap}
        tab = self.tabs[r][c]
        if dbg: print('wrapPrintInterval({:>3} {}) imap={} tab={} im={} selectImaps={}'.format(c, index, imap, chr(tab), im, self.selectImaps), file=Tabs.DBG_FILE)
        if Tabs.isFret(chr(tab)):
            capTab = self.getFretByte(self.getFretNum(tab) + self.getFretNum(self.capo))
            if Tabs.isFret(chr(capTab)):
                row, col = self.indices2RowCol(r, c)
                if chr(self.htabs[r][c]) == '1':
                    n = self.getHarmonicNote(r + 1, capTab)
                else:
                    n = self.getNote(r + 1, capTab)
                nn = n.name
                if dbg: print('wrapPrintInterval({:>3} {}) imap={} capTab={} note={}'.format(c, index, imap, chr(capTab), nn), file=Tabs.DBG_FILE)
                if nn in im:
                    self.printInterval(row + self.numStrings + self.NOTES_LEN, col, im[nn], bStyle, dbg=dbg)
    
    def printInterval(self, row, col, ival, bStyle='', dbg=1):
        cStyle = bStyle + self.styles['NAT_IVAL']
        if dbg: print('printInterval(c={}) row={} col={} ival={} bStyle={} cStyle={}'.format(col - self.COL_OFF, row, col, ival, bStyle, cStyle), file=Tabs.DBG_FILE)
        if len(ival) > 1:
            if ival == 'm2' or ival == 'm3' or ival == 'b5' or ival == 'b7': cStyle = bStyle + self.styles['FLT_IVAL']
            elif ival == 'a5':                                               cStyle = bStyle + self.styles['SHP_IVAL']
            ival = ival[1]
        self.prints(ival, row, col, cStyle)
    
    def printLabels(self):
        self.printFileMark('<BGN_LABELS_SECTION>')
        print('printLabels()'.format(), file=Tabs.DBG_FILE)
        for line in range(0, self.numLines):
            row = line * self.lineDelta() + 1
            if self.outFile == None:
                self.printCursorAndEditModes(row)
            else: 
                self.printPageAndLine(row, line)
                if self.outFile != None: print(file=self.outFile)
            self.printColNums(row)
            if self.outFile != None: print(file=self.outFile)
        self.printFileMark('<END_LABELS_SECTION>') # this was an issue with cat?
    
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
    
    def dumpInfo(self, reason, dbg=0):
        print('dumpInfo() {}'.format(reason), file=Tabs.DBG_FILE)
        print('dumpInfo() selectImaps={}'.format(self.selectImaps), file=Tabs.DBG_FILE)
        print('dumpInfo() selectChords={}'.format(self.selectChords), file=Tabs.DBG_FILE)
        print('dumpInfo() chordAliases={}'.format(self.chordAliases), file=Tabs.DBG_FILE)
        print('dumpInfo() analyzeIndices={}'.format(self.analyzeIndices), file=Tabs.DBG_FILE)
        print('dumpInfo() selectChordAliases={}'.format(self.selectChordAliases), file=Tabs.DBG_FILE)
        print('dumpInfo() selectAnalyzeIndices={}'.format(self.selectAnalyzeIndices), file=Tabs.DBG_FILE)
        if dbg: self.dumpChordInfo(self.chordInfo, reason='dumpInfo()')
    
    def dumpColInfo(self, c, reason):
        print('dumpColInfo(c={}) {}'.format(c, reason), file=Tabs.DBG_FILE)
        if c in self.selectImaps: print('dumpColInfo(c={}) selectImaps={}'.format(c, self.selectImaps[c]), file=Tabs.DBG_FILE)
        if c in self.selectChords: print('dumpColInfo(c={}) selectChords={}'.format(c, self.selectChords[c]), file=Tabs.DBG_FILE)
        if c in self.chordAliases: print('dumpColInfo(c={}) chordAliases={}'.format(c, self.chordAliases[c]), file=Tabs.DBG_FILE)
        if c in self.analyzeIndices: print('dumpColInfo(c={}) analyzeIndices={}'.format(c, self.analyzeIndices[c]), file=Tabs.DBG_FILE)
        self.dumpChordInfoCol(self.chordInfo[c], reason='dumpColInfo()')
    
    def dumpChordInfo(self, m, reason=None):
        print('dumpChordInfo() {} chordInfo(len={})={{'.format(reason, len(m)), file=Tabs.DBG_FILE)
        for k in m:
            self.dumpChordInfoCol(m[k], reason='{:>3}:'.format(k))
        print('}', file=Tabs.DBG_FILE)
    
    def dumpChordInfoCol(self, m, reason=None):
        print('{}'.format(reason), end=' ', file=Tabs.DBG_FILE)
        index = m['INDEX']
        chords = m['CHORDS']
        limap = m['LIMAP']
        self.dumpLimap(limap, reason='{} {}'.format(index, chords))
    
    def dumpLimap(self, limap, reason=None):
        print('{} {{'.format(reason), end=' ', file=Tabs.DBG_FILE)
        for m in limap:
            imap = self.map2String(m)
            print('[{}]'.format(imap), end=', ', file=Tabs.DBG_FILE)
        print('}', file=Tabs.DBG_FILE)
    
    @staticmethod
    def map2String(m):
        s = ''
        for k in m: s += '{} '.format(m[k])
        s += '\\ '
        for k in m: s += '{} '.format(k)
        return s.strip()
    
    def printStatus(self, uicKey=None, hinfo=0, dbg=0):
        '''Display the status line info with intervals and chords on the right and notes on the left'''
        r, c = self.rowCol2Indices(self.row, self.col)
        print('printStatus() row={} col={} r={} c={} bgn'.format(self.row, self.col, r, c), file=Tabs.DBG_FILE)
        tab = chr(self.tabs[r][c])
        if dbg: print('printStatus() row={} col={} r={} c={} tab={}({})'.format(self.row, self.col, r, c, self.tabs[r][c], tab), file=Tabs.DBG_FILE)
        if   Tabs.isFret(tab): cnt = self.printFretStatus(tab, r, c)
        elif tab in self.mods: cnt = self.printModStatus(tab, r, c)
        else:                  cnt = self.printDefaultStatus(tab, r, c)
        self.clearRow(self.lastRow, arg=0, col=cnt, file=self.outFile)
        self.printChordStatus(r, c)
        print('printStatus() row={} col={} r={} c={} cnt={} tab={}({}) end'.format(self.row, self.col, r, c, cnt, self.tabs[r][c], tab), file=Tabs.DBG_FILE)
        if hinfo: self.printh('{}: {}'.format(uicKey, self.printStatus.__doc__))
        else:     self.resetPos()
    
    def printFretStatus(self, tab, r, c, dbg=0):
        s, ss = r + 1, self.getOrdSfx(r + 1)
        f, fs = self.getFretNum(ord(tab)), self.getOrdSfx(self.getFretNum(ord(tab)))
        statStyle, fretStyle = Tabs.CSI + self.bStyle + self.styles['STATUS'], Tabs.CSI + self.bStyle + self.styles['TABS']
        typeStyle, noteStyle = Tabs.CSI + self.bStyle + self.styles['TABS'], Tabs.CSI + self.bStyle + self.styles['TABS']
        if self.htabs[r][c] == ord('1'): n, noteType, tabStyle = self.getHarmonicNote(s, ord(tab)), 'harmonic', Tabs.CSI + self.bStyle + self.styles['H_TABS']
        else:                            n, noteType, tabStyle = self.getNote(s, ord(tab)), None, Tabs.CSI + self.bStyle + self.styles['TABS']
        if len(n.name) > 1:
            if n.name[1] == '#': noteStyle = Tabs.CSI + self.bStyle + self.styles['SHP_NOTE']
            else:                noteStyle = Tabs.CSI + self.bStyle + self.styles['FLT_NOTE']
        if dbg: print('printFretStatus({}) r={}, c={}, tab={}, n.n={}, n.o={}, n.i={}, {}'.format(noteType, r, c, tab, n.name, n.getOctaveNum(), n.index, n.getPhysProps()), file=Tabs.DBG_FILE)
        print(tabStyle + Tabs.CSI + '{};{}H{} '.format(self.lastRow, 1, tab), end='', file=self.outFile)
        txt = tab + ' '
        if f != 0:
            print(fretStyle + '{}{}'.format(s, ss) + statStyle + ' string ' + fretStyle + '{}{}'.format(f, fs) + statStyle + ' fret ', end='', file=self.outFile)
            txt += '{}{}'.format(s, ss) + ' string ' + '{}{}'.format(f, fs) + ' fret '
        else:
            print(fretStyle + '{}{}'.format(s, ss) + statStyle + ' string ' + fretStyle + 'open' + statStyle + ' fret ', end='', file=self.outFile)
            txt += '{}{}'.format(s, ss) + ' string ' + 'open' + ' fret '
        if noteType:
            print(typeStyle + '{} '.format(noteType), end='', file=self.outFile)
            txt += '{} '.format(noteType)
        print(noteStyle + '{}{}'.format(n.name, n.getOctaveNum()), end='', file=self.outFile)
        print(statStyle + ' index=' + fretStyle + '{}'.format(n.index), end='', file=self.outFile)
        print(statStyle + ' freq=' + fretStyle + '{:03.1f}'.format(n.getFreq()) + statStyle + 'Hz', end='', file=self.outFile)
        print(statStyle + ' wvln=' + fretStyle + '{:04.3f}'.format(n.getWaveLen()) + statStyle + 'm', end='', file=self.outFile)
        txt += '{}{}'.format(n.name, n.getOctaveNum())
        txt += ' index=' + '{}'.format(n.index)
        txt += ' freq=' + '{:03.1f}'.format(n.getFreq()) + 'Hz'
        txt += ' wvln=' + '{:04.3f}'.format(n.getWaveLen()) + 'm'
        print('printFretStatus() txt[len={}]={}'.format(len(txt), txt), file=Tabs.DBG_FILE)
        return len(txt)+1
    
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
        print('printModStatus({}, {}) tab={} pfn={} nfn={}'.format(r, c, tab, prevFN, nextFN), file=Tabs.DBG_FILE)
        self.modsObj.setMods(dir1=dir1, dir2=dir2, prevFN=prevFN, nextFN=nextFN, prevNote=prevNote, nextNote=nextNote, ph=ph, nh=nh)
        print(Tabs.CSI + self.bStyle + self.styles['TABS'] + Tabs.CSI + '{};{}H{} '.format(self.lastRow, 1, tab), end='', file=self.outFile)
        print(Tabs.CSI + self.bStyle + self.styles['TABS'] + '{}{}'.format(s, ss) + Tabs.CSI + self.bStyle + self.styles['STATUS'] + ' string {}'.format(self.mods[tab]), end='', file=self.outFile)
        txt = tab + ' '
        txt += '{}{}'.format(s, ss) + ' string {}'.format(self.txts[tab])
        print('printModStatus() txt[len={}]={}'.format(len(txt), txt), file=Tabs.DBG_FILE)
        return len(txt)+1
    
    def printDefaultStatus(self, tab, r, c, dbg=0):
        s, ss, tabStyle, statStyle = r + 1, self.getOrdSfx(r + 1), Tabs.CSI + self.bStyle + self.styles['TABS'], Tabs.CSI + self.bStyle + self.styles['STATUS']
        if dbg: print('printDefaultStatus({}, {}) tab={}'.format(r, c, tab), file=Tabs.DBG_FILE)
        print(tabStyle + Tabs.CSI + '{};{}H{} '.format(self.lastRow, 1, tab), end='', file=self.outFile)
        print(tabStyle + '{}{}'.format(s, ss) + statStyle + ' string ' + tabStyle + 'muted' + statStyle + ' not played', end='', file=self.outFile)
        txt = tab + ' '
        txt += '{}{}'.format(s, ss) + ' string ' + 'muted' + ' not played'
        print('printDefaultStatus() txt[len={}]={}'.format(len(txt), txt), file=Tabs.DBG_FILE)
        return len(txt)+1
    
    def printChordStatus(self, r, c, dbg=0):
        if dbg: self.dumpChordInfo(self.chordInfo, reason='printChordStatus() CHECKING IF c={} IN chordInfo'.format(c))
        if c in self.chordInfo:
            if dbg: self.dumpChordInfo(self.chordInfo, reason='printChordStatus()'.format(c))
            print('printChordStatus() c={} chordNames={} chordAliases={} selectChords={}'.format(c, self.chordsObj.chordNames, self.chordAliases, self.selectChords), file=Tabs.DBG_FILE)
            print('printChordStatus() c={} analyzeIndices={}'.format(c, self.analyzeIndices), file=Tabs.DBG_FILE)
            if c in self.analyzeIndices: index = self.analyzeIndices[c]
            else:                        index = 0
            self.printChordInfo(r, c, index, reason='printChordStatus()')
    
    def analyzeChord(self, uicKey=None, dbg=0):
        '''Visit each chordInfo index one at a time updating only information on status line'''
        r, c = self.rowCol2Indices(self.row, self.col)
        print('analyzeChord() row={} col={} r={} c={}'.format(self.row, self.col, r, c), file=Tabs.DBG_FILE)
        if c in self.chordInfo:
            if c in self.analyzeIndices:
                index = self.analyzeIndices[c] + 1
            else:
                index = 1
            self.analyzeIndices[c] = index % len(self.chordInfo[c]['LIMAP'])
            print('analyzeChord() index={} len(chordInfo[{}])={} analyzeIndices[c]={}'.format(index, c, len(self.chordInfo[c]['LIMAP']), self.analyzeIndices[c]), file=Tabs.DBG_FILE)
            self.printChordInfo(r, c, self.analyzeIndices[c], reason='analyzeChord()')
        self.printh('{}: {}'.format(uicKey, self.analyzeChord.__doc__))
    
    def selectChord(self, uicKey=None, pt=1, dbg=0):
        '''Select chordInfo index for chord names and intervals and info on the Status line'''
        r, c = self.rowCol2Indices(self.row, self.col)
        self.dumpInfo(reason='selectChord(pt={} c={}) row={} col={} r={}'.format(pt, c, self.row, self.col, r))
        if c in self.chordInfo and c in self.analyzeIndices:
            index = self.analyzeIndices[c]
            self.chordInfo[c]['INDEX'] = index
            self.dumpChordInfoCol(self.chordInfo[c], reason='selectChord(c={})'.format(c))
            name, imap = self.printChordInfo(r, c, index, reason='selectChord()')
            if dbg: print('selectChord(c={}) index={} analyzeIndices[c]={} chordAliases={}'.format(c, index, self.analyzeIndices[c], self.chordAliases), file=Tabs.DBG_FILE)
            if c in self.chordAliases:
                if dbg: print('selectChord(c={}) found c in chordAliases={}'.format(c, self.chordAliases), file=Tabs.DBG_FILE)
                n = self.chordAliases[c]
                if dbg: print('selectChord(c={}) checking if alias={} in selectChords={}'.format(c, n, self.selectChords), file=Tabs.DBG_FILE)
                if n in self.selectChords:
                    if dbg: print('selectChord(c={}) removing alias={} from selectChords={}'.format(c, n, self.selectChords), file=Tabs.DBG_FILE)
                    del self.selectChords[n]
            if dbg: print('selectChord(c={}) adding key={} val={} to selectChords={}'.format(c, name, imap, self.selectChords), file=Tabs.DBG_FILE)
            self.selectChords[name] = imap
            if dbg: print('selectChord(c={}) selectChords={}'.format(c, self.selectChords), file=Tabs.DBG_FILE)
            if dbg: print('selectChord(c={}) adding alias={} to chordAliases={}'.format(c, name, self.chordAliases), file=Tabs.DBG_FILE)
            self.chordAliases[c] = name
            if dbg: print('selectChord(c={}) chordAliases={}'.format(c, self.chordAliases), file=Tabs.DBG_FILE)
            if dbg: print('selectChord(c={}) index={} selectChords[{}]={}'.format(c, index, name, self.selectChords[name]), file=Tabs.DBG_FILE)
            im = self.chordInfo[c]['LIMAP'][index]
            if dbg: print('selectChord(c={}) adding key={} : val={} to '.format(c, self.map2String(im), imap), end='', file=Tabs.DBG_FILE)
            if dbg: self.dumpSelectImaps()
            self.selectImaps[self.map2String(im)] = imap
            if dbg: self.dumpSelectImaps()
            if pt:
                self.printTabs()
                self.printh('{}: {}'.format(uicKey, self.selectChord.__doc__))
        else: self.printe('selectChord() nothing to select use \'Ctrl A\' analyzeChord() first')
    
    def dumpSelectImaps(self):
        print('selectImaps={{'.format(), end=' ', file=Tabs.DBG_FILE)
        for k in self.selectImaps:
            print('{} : {}'.format(k, self.selectImaps[k]), end=', ', file=Tabs.DBG_FILE)
        print('}', file=Tabs.DBG_FILE)
    
    def printChordInfo(self, r, c, m, reason=None, dbg=0):
        tab = chr(self.tabs[r][c])
        if dbg: print('printChordInfo(r={} c={} m={} tab={}) bgn reason={}'.format(r, c, m, tab, reason), file=Tabs.DBG_FILE)
        if dbg: self.dumpInfo('printChordInfo()')
        if m < len(self.chordInfo[c]['LIMAP']): print('printChordInfo() m={} < len(self.chordInfo[c][LIMAP])={}'.format(m, len(self.chordInfo[c]['LIMAP'])), file=Tabs.DBG_FILE)
        else: print('printChordInfo(?) m={} >= len(self.chordInfo[c][LIMAP])={}'.format(r, c, m, tab, len(self.chordInfo[c]['LIMAP'])), file=Tabs.DBG_FILE)
        imap = self.chordInfo[c]['LIMAP'][m]
        imapKeys = sorted(imap, key=self.chordsObj.imapKeyFunc, reverse=False)
        if dbg: 
            print('printChordInfo(r={} c={} m={} tab={}) imap[{}]= [ '.format(r, c, m, tab, m), end='', file=Tabs.DBG_FILE)
            for k in imapKeys: print('{}:{} '.format(k, imap[k]), end='', file=Tabs.DBG_FILE)
            print(']', file=Tabs.DBG_FILE)
        info, infoLen, i, n, hk, chordKey, chordName, chordDelim = [], 0, 0, None, '', '', '', ' [{}] '.format(m)
        if Tabs.isFret(tab):
            if self.htabs[r][c] == ord('1'): n = self.getHarmonicNote(r + 1, ord(tab)).name
            else:                            n = self.getNote(r + 1, ord(tab)).name
        for k in imapKeys:
            chordKey += imap[k] + ' '
            info.append('{}:{} '.format(k, imap[k]))
            infoLen += len(info[-1])
            if imap[k] == n: hk = k
            if dbg: print('printChordInfo({}) infoLen={} info={} imap[{}]={} n={} hk={} chordKey={}'.format(len(info)-1, infoLen, info, k, imap[k], n, hk, chordKey), file=Tabs.DBG_FILE)
        infoCol = self.numTabsPerStringPerLine + self.COL_OFF - infoLen + 1
        if dbg: print('printChordInfo() infoCol={} ll={} COL_OFF={} infoLen={}'.format(infoCol, self.numTabsPerStringPerLine, self.COL_OFF, infoLen), file=Tabs.DBG_FILE)
        if info: info[-1] = info[-1][:-1]
        if chordKey: chordKey = chordKey[:-1]
        if chordKey in self.chordsObj.chords:
            chordName = self.chordsObj.chords[chordKey]
        infoCol -= (len(chordName) + len(chordDelim))
        if self.chordStatusCol is not None:
            if infoCol < self.chordStatusCol: self.chordStatusCol = infoCol
        else: self.chordStatusCol = infoCol
        if dbg: print('printChordInfo() infoCol={} len(chordName)={} len(chordDelim)={} chordStatusCol={}'.format(infoCol, len(chordName), len(chordDelim), self.chordStatusCol), file=Tabs.DBG_FILE)
        print('printChordInfo(r={} c={} m={} tab={}) chordName={} info={} infoCol={} chordStatusCol={}'.format(r, c, m, tab, chordName, info, infoCol, self.chordStatusCol), file=Tabs.DBG_FILE)
        style = Tabs.CSI + self.bStyle + self.styles['HLT_STUS']
        if len(chordName) > 0:
            style = Tabs.CSI + self.bStyle + self.getEnharmonicStyle(chordName, self.styles['NAT_NOTE'], self.styles['FLT_NOTE'], self.styles['SHP_NOTE'])
        print(style + Tabs.CSI + '{};{}H{}'.format(self.lastRow, infoCol, chordName), end='', file=self.outFile)
        print(Tabs.CSI + self.bStyle + self.styles['MOD_DELIM'] + '{}'.format(chordDelim), end='', file=self.outFile)
        for k in imapKeys:
            if k == hk: style = Tabs.CSI + self.bStyle + self.styles['HLT_STUS']
            else:       style = Tabs.CSI + self.bStyle + self.styles['STATUS']
            print(style + '{}'.format(info[i]), end='', file=self.outFile)
            i += 1
        return chordName, imap
    
    def printErrorHistory(self, uicKey=None, back=1, dbg=1):
        '''Display error history'''
        if back == 1: iBgn, iEnd, iDelta, dir = len(self.errors)-1, -1, -1, 'BACKWARD'
        else:         iBgn, iEnd, iDelta, dir = 0, len(self.errors), 1, 'FORWARD'
        if self.errorsIndex == None:
            self.printh('{}: {} {} No error history to display - Press ? for help'.format(uicKey, self.printErrorHistory.__doc__, dir), col=1, hist=1)
            return
        if dbg:
            print('printErrorHistory({} {} {}) back={} errorsIndex={} errors[len={}]=['.format(iBgn, iEnd, iDelta, back, self.errorsIndex, len(self.errors)), file=Tabs.DBG_FILE)
            for i in range(iBgn, iEnd, iDelta):
                print('    [{}] {}'.format(i, self.errors[i]), file=Tabs.DBG_FILE)
            print(']', file=Tabs.DBG_FILE)
        self.printh('{}: {} {} [{}] {}'.format(uicKey, self.printErrorHistory.__doc__, dir, self.errorsIndex, self.errors[self.errorsIndex]), col=1, hist=1)
        if back == 1:
            self.errorsIndex -= 1
            if self.errorsIndex == -1:               self.errorsIndex = len(self.errors) - 1
        else:
            self.errorsIndex += 1
            if self.errorsIndex == len(self.errors): self.errorsIndex = 0
    
    def printCmdHistory(self, uicKey='', back=1, dbg=1):
        '''Display command history'''
        if back == 1: iBgn, iEnd, iDelta, dir = len(self.cmds)-1, -1, -1, 'BACKWARD'
        else:         iBgn, iEnd, iDelta, dir = 0, len(self.cmds), 1, 'FORWARD'
        print('printCmdHistory() type(uicKey)={} type(dir)={}'.format(type(uicKey), type(dir)), file=Tabs.DBG_FILE)
        if self.cmdsIndex == None:
            self.printh('{}: {} {} No command history to display - Press ? for help'.format(uicKey, self.printCmdHistory.__doc__, dir), col=1, hist=1)
            return
        if dbg:
            print('printCmdHistory({} {} {}) back={} cmdsIndex={} cmds[len={}]=['.format(iBgn, iEnd, iDelta, back, self.cmdsIndex, len(self.cmds)), file=Tabs.DBG_FILE)
            for i in range(iBgn, iEnd, iDelta):
                key = self.cmds[i][0 : self.cmds[i].find(':') + 1]
                self.cmds[i] = self.cmds[i].replace(key, '')
                self.cmds[i] = self.cmds[i].lstrip()
                name = self.cmds[i][0 : self.cmds[i].find(' ') + 1]
                self.cmds[i] = self.cmds[i].replace(name, '')
                print(' {:>4} {:>17} {:<20} {}'.format(i, key, name, self.cmds[i]), file=Tabs.DBG_FILE)
            print(']', file=Tabs.DBG_FILE)
        self.printh('{}: {} {} [{}] {}'.format(uicKey, self.printCmdHistory.__doc__, dir, self.cmdsIndex, self.cmds[self.cmdsIndex]), col=1, hist=1)
        if back == 1:
            self.cmdsIndex -= 1
            if self.cmdsIndex == -1:             self.cmdsIndex = len(self.cmds) - 1
        else:
            self.cmdsIndex += 1
            if self.cmdsIndex == len(self.cmds): self.cmdsIndex = 0
    
    def printe(self, reason, row=None, col=None, style=None, x=0):
        if row is None:     row = self.row
        if col is None:     col = self.col
        if style is None: style = self.styles['ERROR']
        self.errors.append(reason)
        self.errorsIndex = len(self.errors) - 1
        print('ERROR! printe({}, {}) r={} c={} {}'.format(row, col, self.row2Index(row), self.col2Index(col), reason), file=Tabs.DBG_FILE)
        print(Tabs.CSI + style + Tabs.CSI + '{};{}H{}'.format(self.lastRow, 1, reason), end='')
        self.resetPos()
        if x: self.quit(reason='printe() {}'.format(reason), code=3)
    
    def printh(self, reason, col=61, style=None, hist=0, dbg=0):
        if col is None:     col = self.col
        if style is None: style = self.styles['HLT_STUS']
        if hist == 0:
            if not self.filterCmds or reason.find(self.cmdFilterStr, 0, len(self.cmdFilterStr)) == -1:
                self.cmds.append(reason)
                self.cmdsIndex = len(self.cmds) - 1
            else:
                print('printh() filtered cmd={}'.format(reason), file=Tabs.DBG_FILE)
        print('printh(col={}) hist={} reason={}'.format(col, hist, reason), file=Tabs.DBG_FILE)
        self.prints(reason, self.lastRow, col, style)
        self.resetPos()
    
    def prints(self, s, row, col, style):
        print(Tabs.CSI + self.bStyle + style + Tabs.CSI + '{};{}H{}'.format(row, col, str(s)), end='', file=self.outFile)
    
    def getNote(self, str, tab):
        '''Return note object given string number and tab fret number byte'''
        cfret = self.getFretNum(tab)
#        cfret = fret + self.getFretNum(self.capo)
        return notes.Note(self.getNoteIndex(str, cfret), self.enharmonic)
    
    def getHarmonicNote(self, str, tab):
        '''Return harmonic note object given string number and tab fret number byte'''
        fret = self.getFretNum(tab)
        chfret = self.HARMONIC_FRETS[fret]
#        chfret = hfret + self.getFretNum(self.capo)
        n = notes.Note(self.getNoteIndex(str, chfret), self.enharmonic)
        print('getHarmonicNote({}, {}) f={} hf={} chf={} n.i={} n.n={} n.o={})'.format(str, tab, fret, hfret, chfret, n.index, n.name, n.getOctaveNum()), file=Tabs.DBG_FILE)
        return n
    
    def getNoteIndex(self, str, f):
        '''Convert string # from 1 based for high E first string and str=numStrings low E sixth string'''
        s = self.numStrings - str                     # Reverse and zero base the string numbering: str[1 ... numStrings] => s[(numStrings - 1) ... 0]
        i = self.stringMap[self.stringKeys[s]] + f    # calculate the fretted note index using the sorted map
#        print('getNoteIndex() str={}, s={}, f={}, i={}, sk={}, sm={}'.format(str, s, f, i, self.stringKeys[s], self.stringMap[self.stringKeys[s]]), file=Tabs.DBG_FILE)
        return i
    
    def printChord(self, uicKey=None, c=None, dbg=0):
        '''Analyze notes at given column and if they form a chord print the chord in chords section'''
        self.chordsObj.printChord(c, dbg=dbg)
        self.printh('{}: {}'.format(uicKey, self.printChord.__doc__))
    
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
    
    def clearRow(self, row, col=1, arg=2, file=None, dbg=0): # arg=0: col to end of line, arg=1: begin of line to col, arg=2: entire line
        cBgn = 1
        cEnd = self.endCol() + 1
        if   arg == 0: cBgn = col
        elif arg == 1: cEnd = col + 1
        elif arg == 2: pass
        if row is None: self.printe('clearRow(arg={} col={}) invalid row={}'.format(arg, col, row))
        else:
            blank = ''
            for c in range(cBgn, cEnd): blank += ' '
            print(Tabs.CSI + self.styles['SHP_NOTE'] + Tabs.CSI + '{};{}H{}'.format(row, cBgn, blank), end='', file=file)
            if dbg: print('clearRow({} {}) arg={} row={} col={} cBgn={} cEnd={} blank=\n{}'.format(self.row, self.col, arg, row, col, cBgn, cEnd, blank), file=Tabs.DBG_FILE)
    
    def clearRow_OLD(self, row, col=1, arg=2, file=None, dbg=1):
        if dbg: print('clearRow() arg={} row={} col={}'.format(arg, row, col), file=Tabs.DBG_FILE)
        print(Tabs.CSI + '{};{}H'.format(row, col), end='', file=file)
        print(Tabs.CSI + '{}K'.format(arg), end='', file=file)
    
    @staticmethod
    def clearScreen(arg=2, file=None, reason=None, dbg=0):
        if dbg: print('clearScreen() arg={} file={} reason={}'.format(arg, file, reason), file=Tabs.DBG_FILE)
        print(Tabs.CSI + '{}J'.format(arg), file=file)
    
    def hiliteText(self, text):
        return Tabs.CSI + self.styles['ERROR'] + text + Tabs.CSI + self.styles['CONS']
    
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
The command line arg --help enables display of this help info.  
The command line arg -? enables display of this help info.  

Tabs are displayed in the tabs section with an optional row to label and highlight the selected tab column.  
An optional notes section and an optional chords section can also be displayed below the tabs section.  
A number of lines can be displayed where each line has its own tabs, notes, intervals, and chords sections.  
''' + self.hiliteText('Tabs section:') + ''' 
Tabs are displayed using rows and columns of ASCII characters, essentially one character per tab.  
Tabs are represented by the single digits [0-9] and the letters [a-o], rather than [10-24].  
The value '0' represents the open string.  The minus character '-' is used for padding and represents an unplayed string.  
The value '2' represents playing the string 1 full step above the nut, 'c' represents 12 half steps above the nut or an octave higher.  

Optional tab modification characters are used to denote tonal expression such as bending, sliding, hammer on/off, vibrato etc...  
Tab modifications are implemented as a customizable dictionary in the ''' + self.hiliteText('mods.py') + ''' module.  
You can change or add tab modifications by simply editing the ''' + self.hiliteText('mods.py') + ''' file. 
The dictionary keys are the modification characters and the values describe how to interpret the characters.  
When the cursor occupies the same row and column as a tab modifier the dictionary value is printed on the last row.  

Each row has a number of columns that represent the tab characters for a particular string as they are played sequentially in time from left to right.  
Rows are labelled using 1 based string numbers (increasing in the downward direction) in the first display column.  
The nut and capo are displayed in the 2nd column with the string label to the left and all the tabs to the right.  
The capo can have values corresponding to the fret numbers [0-9], [a-o], where 0 denotes no capo.  
To enter a tab simply navigate to the desired row and column using the arrow, Home, End, PageUp, or PageDown keys and then enter the character.  
Note the cursor will automatically advance to the right, up, down, up and right, or down and right depending on the cursor mode.  
Also note the tabs section is the only section that is editable.  The navigation keys will automatically skip over the notes and or chords sections.  
''' + self.hiliteText('Notes section:  \'Ctrl N\'') + ''' 
The notes section has the same number of rows and columns as the tabs section and displays the note names corresponding to the tabs in the tabs section.  
The notes section uses the color red to indicate a sharp note and blue to represent a flat note.  
Note any optional tab modification characters present in the tabs section are also displayed in the notes section.  
''' + self.hiliteText('Intervals section:  \'Ctrl B\'') + ''' 
The intervals section has the same number of rows and columns as the tabs section and displays the note intervals corresponding to the chord in the chords section.  
The intervals section uses the color red to indicate a sharp interval and blue to represent a flat interval.  
''' + self.hiliteText('Chords section:  \'Ctrl B\'') + ''' 
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
