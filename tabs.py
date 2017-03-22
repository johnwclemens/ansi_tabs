import os, inspect, sys

try:
    import tty, termios
except ImportError:
    print("ERROR 'import tty, termios' failed, so 'try: import msvcrt'")
    try:
        import msvcrt
    except ImportError:
        raise ImportError('getch not available')
    else:
        getch   = msvcrt.getch
        getche  = msvcrt.getche
        kbhit   = msvcrt.kbhit
        getwch  = msvcrt.getwch
        getwche = msvcrt.getwche
else:
    print("import tty, termios OK, define getch()")
    def getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

import colorama
import notes
import mods
import strings

class Tabs(object):
    '''Represent musical tab notation and implement associated functionality.'''
    ESC = '\033'
    CSI = '\033\133'
    QUIT_STR = 'Received Quit Cmd: Exiting'
    
    def __init__(self, inName='tabs.tab', outName='tabs.tab', dbgName='dbg.tab'):
        '''Initialize the Tabs object and start the interactive loop method.  The inName and outName can be the same or different.'''
        self.init(inName, outName, dbgName)
        self.loop()

    def init(self, inName='tabs.tab', outName='tabs.tab', dbgName='dbg.tab'):
        '''Initialize colorama, enabling automatic reset of console after each call via print(colorama.Style.RESET_ALL).'''
        colorama.init(autoreset=True)
        self.clearScreen()

        self.initFiles(inName, outName, dbgName)
        self.initConsts()
        self.uiCmds = {}
        self.uiKeys = []
        self.registerUiCmds()
        self.mods = {}
        self.lastRowDirty = 0
        self.dbgMove = True
        
        self.harmonicNotes = []
        self.tabCount = 0
        self.tabs = []                                                    # list of bytearrays, one for each string
        self.selectTabs = []
        self.selectCols = []
        self.numSelectCols = 0
        self.chords = {}
        self.stringMap = {}
        self.stringKeys = []

        self.numLines = 1
        self.numTabsPerStringPerLine = 10
        self.numTabsPerString = self.numLines * self.numTabsPerStringPerLine
        
        self.ROW_OFF = 1
        self.COL_OFF = 3
        self.CHORD_LEN = 0
        self.NOTE_LEN = 0
      
        self.hiliteCount = 0
        self.colNum = 0
        self.rowNum = 0
        self.rowNumPos = 0
        self.row = self.ROW_OFF
        self.col = self.COL_OFF
        self.editModeCol = 1
        self.cursorModeCol = 2
        self.numStrings = 1
        self.lastRow = self.ROW_OFF + self.numLines * self.lineDelta() - 1
        
        self.displayStatus = self.DISPLAY_STATUS['DISABLED']
        self.displayNotes = self.DISPLAY_NOTES['DISABLED']
        self.displayChords = self.DISPLAY_CHORDS['DISABLED']
        self.cursorDir = self.CURSOR_DIRS['DOWN']
        self.enharmonic = self.ENHARMONIC['SHARP']
        self.editMode = self.EDIT_MODES['REPLACE']
        self.cursorMode = self.CURSOR_MODES['MELODY']
        
        argMap = {}
        self.initMyLib()
        import jwc_cmdArgs
        jwc_cmdArgs.parse_cmd_line(argMap)
        print('tabs.py args={}'.format(argMap), file=self.dbgFile)
        if 'f' in argMap and len(argMap['f']) > 0:
            self.inName = argMap['f'][0]
            self.outName = argMap['f'][0]
        if 't' in argMap and len(argMap['t']) > 0:
            self.initTabLen(argMap['t'])
        if 's' in argMap and len(argMap['s']) > 0:
            self.initStrings(spelling=argMap['s'])
        elif 'S' in argMap and len(argMap['S']) > 0:
            self.initStrings(alias=argMap['S'])
        else:
            self.initStrings()
        self.setLastRow()
        self.numTabs = self.numStrings * self.numTabsPerString

#        self.testAnsi()
        try:
            with open(self.inName, 'rb') as self.inFile:
                self.initTabs(readSize=500)
        except FileNotFoundError as e:
            print('init() Exception: FileNotFoundError: {}'.format(e), file=self.dbgFile)
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
#                print('init({}, {}) len(tabs)={}, len(HN)={}'.format(r, c, len(self.tabs), len(self.harmonicNotes)), file=self.dbgFile)
                self.tabs.append(bytearray([ord(t), ord('0') for t in tabs] * mult))
                self.harmonicNotes.append(bytearray([ord('0') for t in tabs] * mult))
        finally:
            self.modsObj = mods.Mods(file=self.dbgFile)
            self.mods = self.modsObj.getMods()
            print('init() mods=\{ ', file=self.dbgFile)
            for k in self.mods:
                print('{}:{}, '.format(k, self.mods[k]), file=self.dbgFile)
            if 'F' in argMap and len(argMap['F']) == 0:
                self.toggleEnharmonic()
            if 'i' in argMap and len(argMap['i']) == 0:
                self.toggleCursorDir(dbg=1)
            if 'a' in argMap and len(argMap['a']) == 0:
                self.toggleDisplayStatus(printTabs=False)
            if 'b' in argMap and len(argMap['b']) == 0:
                self.toggleDisplayChords(printTabs=False)
            if 'n' in argMap and len(argMap['n']) == 0:
                self.toggleDisplayNotes(printTabs=False)
            if 'z' in argMap and len(argMap['z']) == 0:
                self.goToLastTab(lastLine=False)
            if 'Z' in argMap and len(argMap['z']) == 0:
                self.goToLastTab()
            if 'h' in argMap and len(argMap['h']) == 0:
                self.printHelpInfo()
            self.printTabs()
            self.hiliteRowColNum()
 
    def initMyLib(self):
        file = inspect.getfile(inspect.currentframe())
        filePath = os.path.abspath(file)
        splitFilePath = os.path.split(filePath)[0]
        myLibPath = splitFilePath.replace('tabs', 'lib')
        print('file={}\nfilePath={}\nsplitFilePath={}\nmyLibPath={}'.format(file, filePath, splitFilePath, myLibPath), file=self.dbgFile)
        if myLibPath not in sys.path:
            sys.path.insert(0, myLibPath)

    def testAnsi(self):
        file = open('testAnsi.tab', 'w')
        self.clearScreen(file=file)
        styles = {'NORMAL':'22;', 'CONS':'37;40m', 'TABS':'32;40m'}
        print(colorama.Style.NORMAL + self.styles['CONS'] + '{}{};{}H{}'.format(self.CSI, 1, 1, 'a'), file=file)
        print(self.CSI + styles['NORMAL'] + styles['TABS'] + '{}{};{}H{}'.format(self.CSI, 2, 1, 'b'), file=file)
        print(self.CSI + styles['NORMAL'] + styles['CONS'] + self.CSI + '{};{}H{}'.format(3, 1, 'c'), file=file)
        self.quit('testAnsi()')
     
    def initFiles(self, inName, outName, dbgName):
        self.dbgFile = open(dbgName, "w")
        self.inName = inName
        self.inFile = None
        self.outName = outName
        self.outFile = None
        
    def initConsts(self): #        self.INTERVAL_RANK = { v:k for k,v in self.INTERVALS.items() }
        self.styles = { 'NAT_NOTE':'32;47m', 'NAT_CHORD':'37;46m', 'MIN_COL_NUM':'36;40m',  'TABS':'32;40m', 'NORMAL':'22;', 
                        'FLT_NOTE':'34;47m', 'FLT_CHORD':'34;46m', 'MAJ_COL_NUM':'32;40m',  'CONS':'37;40m', 'BRIGHT':'1;', 
                        'SHP_NOTE':'31;47m', 'SHP_CHORD':'31;46m',       'ERROR':'31;42m', 'MODES':'34;47m',  }
        self.SHARPS_2_FLATS = { 'C#':'Db', 'D#':'Eb', 'F#':'Gb', 'G#':'Ab', 'A#':'Bb' }
        self.FLATS_2_SHARPS = { 'Bb':'A#', 'Ab':'G#', 'Gb':'F#', 'Eb':'D#', 'Db':'C#' }
        self.INTERVALS = { 0:'R',  1:'b2',  2:'2',  3:'m3',  4:'M3',  5:'4',   6:'b5',  7:'5',  8:'a5',  9:'6',  10:'b7', 11:'7', 
                          12:'R', 13:'b9', 14:'9', 15:'m3', 16:'M3', 17:'11', 18:'b5', 19:'5', 20:'a5', 21:'13', 22:'b7', 23:'7',
                          24:'R', 25:'b9', 26:'9', 27:'m3', 28:'M3', 29:'11', 30:'b5', 31:'5', 32:'a5', 33:'13', 34:'b7', 35:'7', 
                          36:'R', 37:'b9', 38:'9', 39:'m3', 40:'M3', 41:'11', 42:'b5', 43:'5', 44:'a5', 45:'13', 46:'b7', 47:'7', 48:'R' }
        self.INTERVAL_RANK = { 'R':0, 'b2':1, '2':2, 'm3':3, 'M3':4, '4':5, 'b5':6, '5':7, 'a5':8, '6':9, 'b7':10, '7':11, 'b9':12, '9':13, '11':14, '13':15 }
        self.HARMONIC_FRETS = { 12:12, 7:19, 19:19, 5:24, 24:24, 4:28, 9:28, 16:48, 28:28 }
#        self.FRET_INDICES = { 0:0, 1:1, 2:2, 3:3, 4:4, 5:5, 6:6, 7:7, 8:8, 9:9, 10:'a' }  # for moving along the fretboard?
#        self.MAJ_INDICES = [ 0, 2, 4, 5, 7, 9, 11, 12 ]                                   # for key signatures and or chords?
#        self.MIN_INDICES = [ 0, 2, 3, 5, 7, 9, 10, 12 ]                                   # for key signatures and or chords?
        self.CURSOR_DIRS = { 'DOWN':0, 'UP':1 }
        self.CURSOR_DIR_INDS = { 0:'|', 1:'^' }
        self.CURSOR_MODES = { 'MELODY':0, 'CHORD':1, 'ARPEGGIO':2 }
        self.EDIT_MODES = { 'REPLACE':0, 'INSERT':1 }
        self.ENHARMONIC = { 'FLAT':0, 'SHARP':1 }
        self.DISPLAY_STATUS = { 'DISABLED':0, 'ENABLED':1 }
        self.DISPLAY_NOTES = { 'DISABLED':0, 'ENABLED':1 }
        self.DISPLAY_CHORDS = { 'DISABLED':0, 'ENABLED':1 }
    
    def initStrings(self, alias=None, spelling=None):
        print('initStrings( alias={}, spelling={})'.format(alias, spelling), file=self.dbgFile)
        try:
            self.strings = strings.Strings(self.dbgFile,  alias=alias, spelling=spelling)
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

    def initTabs(self, readSize=600):
        dbg = 1
        if self.inFile != None:
            fileSize = self.initInFile()
            tmp = []
            cnt, bytesRead, endOfTabs, hasFrag, rowStr = 0, 0, None, False, '{}'.format(self.ROW_OFF)
            data = self.inFile.read(readSize)
            print('initTabs({}) fileSize {:,} bytes, reading first {:,} bytes:\'\n{}\''.format(rowStr, fileSize, readSize, ''.join([chr(data[p]) for p in range(0, readSize)])), file=self.dbgFile)
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
                        if dbg: print('initTabs({}) detected fragment, len={} \'{}\' ii={}, p1={}, p2={}, i={}, bgn={}'.format(rowStr, len(fragment), ''.join([chr(fragment[p]) for p in range(0, len(fragment))]), ii, p1, p2, i, bgn), file=self.dbgFile)
                    else:
                        p2 = data.rfind(ord(';'), i - 6, i)
                        p1 = data.rfind(ord('['), i - 6, i) + 1
                        row = ''.join([chr(data[p]) for p in range(p1, p2)])
                        col = ''.join([chr(data[p]) for p in range(p2+1, i)])
                        tab = chr(data[i+1])
                        tmp.append(data[i + 1])
                        if hasFrag:
                            print('initTabs({}) {} {} [{},{}], ii={}, p1={}, p2={}, i={}, bgn={} {} \'{}\' data=\'{}\' tmp=\'{}\''.format(rowStr, cnt, len(fragment), row, col, ii, p1, p2, i, bgn, hasFrag, tab, ''.join([chr(data[p]) for p in range(ii, i+2)]), ''.join([chr(tmp[p]) for p in range(0, len(tmp))])), file=self.dbgFile)
                            hasFrag = False
                        elif dbg:
                            print('initTabs({}) {} {} [{},{}], ii={}, p1={}, p2={}, i={}, bgn={} {} \'{}\' data=\'{}\' tmp=\'{}\''.format(rowStr, cnt, len(fragment), row, col, ii, p1, p2, i, bgn, hasFrag, tab, ''.join([chr(data[p]) for p in range(ii+2, i+2)]), ''.join([chr(tmp[p]) for p in range(0, len(tmp))])), file=self.dbgFile)
                        z1 = data.find(ord('<'), bgn, p1)
                        z2 = data.find(ord('>'), z1, p1)
                        if z1 != -1 and z2 != -1 and data[z1+1:z2] == b'END_TABS_SECTION':
                            endOfTabs = data[z1+1:z2]
                            print('initTabs() found \'{}\' mark at z1,z2={},{}'.format(data[z1+1:z2], z1, z2), file=self.dbgFile)
                            break
                        elif self.numTabsPerStringPerLine == 0 and int(row) == self.ROW_OFF + 1:
                            self.numTabsPerStringPerLine = cnt - self.COL_OFF
                            self.numTabsPerString = self.numLines * self.numTabsPerStringPerLine
                            tmp, rowStr = self.appendTabs(tmp, rowStr)
                            tmp.append(data[i + 1])
                            if dbg: print('initTabs({}) {} [{},{}] \'{}\' setting numTabsPerStringPerLine={} tmp=\'{}\''.format(rowStr, cnt, row, col, tab, self.numTabsPerStringPerLine, ''.join([chr(tmp[p]) for p in range(0, len(tmp))])), file=self.dbgFile)
                        elif self.isTab(tab) and self.numTabsPerStringPerLine != 0 and int(col) == self.COL_OFF - 1 + self.numTabsPerStringPerLine:# and len(tmp) > 1 and tmp[1] == '|':
                            tmp, rowStr = self.appendTabs(tmp, rowStr)
#                            self.dumpTabs('after appendTabs()')
#                        else: tmp = []
                    bgn = i + 2
                if endOfTabs: break
                data = self.inFile.read(readSize)
                dataLen = len(data)
                if dataLen == 0:
                    print('initTabs() No more data to read from inFile, fragment: \'{}\''.format(''.join([chr(fragment[p]) for p in range(0, len(fragment))])), file=self.dbgFile)
                    break
                data = fragment + data
                if dbg: print('initTabs() bytes read {:,}, reading next {:,} bytes and appending to fragment of len {} bytes ({:,} bytes):\n{}'.format(bytesRead, dataLen, len(fragment), dataLen + len(fragment), ''.join([chr(data[p]) for p in range(0, len(data))])), file=self.dbgFile)
            print('initTabs() numStrings:{} =?= len(tabs):{}, numTabsPerString:{} =?= numLines:{} * numTabsPerStringPerLine:{}, totTabs:{}'.format(
                self.numStrings, len(self.tabs), self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, len(self.tabs) * len(self.tabs[0])), file=self.dbgFile)
            self.dumpTabs('initTabs()')
        else:
            for r in range(0, self.numStrings):
                print('initTabs({}, {}) len(tabs)={}, len(HN)={}'.format(r, c, len(self.tabs), len(self.harmonicNotes)), file=self.dbgFile)
                self.tabs.append(bytearray([ord('-'), ord('0')] * self.numTabsPerString))
                self.harmonicNotes.append(bytearray([ord('0')] * self.numTabsPerString))
            self.quit('', code=1)

    def appendTabs(self, tmp, rowStr):
        rowStr = '{}'.format(int(rowStr) + 1)
        tabDataRow = tmp[2: 2 + self.numTabsPerStringPerLine]
        self.tabCount += len(tabDataRow)
        print('appendTabs({}) checking  \'{}\' , numTabsPerString={}, numLines={}, numTabsPerStringPerLine={}, tabCount={}'.format(rowStr, ''.join([chr(t) for t in tabDataRow]), self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.tabCount), file=self.dbgFile)
        if self.tabCount > self.numStrings * self.numTabsPerStringPerLine:
            if self.tabCount == (self.numStrings + 1) * self.numTabsPerStringPerLine or self.tabCount == (2 * self.numStrings + 1) * self.numTabsPerStringPerLine:
                self.appendLine(printTabs=False)
            if int(rowStr) - (self.numLines - 1) * self.numStrings - self.ROW_OFF <= self.numStrings:
                r = (int(rowStr) - self.ROW_OFF - 1) % self.numStrings
                for c in range(0, len(tabDataRow)):
#                    print('appendTabs({}, {}) len(tabs)={}, len(HN)={}'.format(r, c, len(self.tabs), len(self.harmonicNotes)), file=self.dbgFile)
                    self.tabs[r][c + (self.numLines - 1) * self.numTabsPerStringPerLine] = tabDataRow[c]
                    self.harmonicNotes[r][c + (self.numLines - 1) * self.numTabsPerStringPerLine] = ord('0')
                print('appendTabs({},{}) appending \'{}\' to tabs[line={}, string={}], numTabsPerString={}, numLines={}, numTabsPerStringPerLine={}, tabCount={}'.format(rowStr, r, ''.join([chr(t) for t in tabDataRow]), self.numLines, '{}'.format(int(rowStr) - (self.numLines-1)*self.numStrings - self.ROW_OFF), self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.tabCount), file=self.dbgFile)
        else:
            self.tabs.append(tabDataRow)
            self.harmonicNotes.append(bytearray([ord('0')] * self.numTabsPerString))
            print('appendTabs({}) appending \'{}\' to tabs[line={}, string={}], numTabsPerString={}, numLines={}, numTabsPerStringPerLine={}, tabCount={}'.format(rowStr, ''.join([chr(t) for t in tabDataRow]), self.numLines, '{}'.format(int(rowStr) - self.ROW_OFF), self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.tabCount), file=self.dbgFile)
        tmp = []
        return [tmp, rowStr]
        
    def appendLine(self, printTabs=True):
        '''Append another line of tabs to the display.'''
        tabs = []
        HN = []
        print('appendLine(old) numTabsPerString:{} = numLines:{} * numTabsPerStringPerLine:{}, numTabs:{} = numStrings:{} * len(tabs[0]):{}'.format(self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.numTabs, self.numStrings, len(self.tabs[0])), file=self.dbgFile)
        self.numLines += 1
        self.numTabsPerString = self.numLines * self.numTabsPerStringPerLine
        for r in range(0, self.numStrings):
            tabs.append(bytearray([ord('-')] * self.numTabsPerString))
            HN.append(bytearray([0] * self.numTabsPerString))
            for c in range(0, len(self.tabs[r])):
                tabs[r][c] = self.tabs[r][c]
                HN[r][c] = self.harmonicNotes[r][c]
        self.harmonicNotes = HN
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
        tabs = []
        print('removeLine(old) numTabsPerString:{} = numLines:{} * numTabsPerStringPerLine:{}, numTabs:{} = numStrings:{} * len(tabs[0]):{}'.format(self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine, self.numTabs, self.numStrings, len(self.tabs[0])), file=self.dbgFile)
        self.numLines -= 1
        self.numTabsPerString = self.numLines * self.numTabsPerStringPerLine
        for r in range(0, self.numStrings):
            tabs.append(bytearray([ord('-')] * self.numTabsPerString))
            for c in range(0, self.numTabsPerString):
                tabs[r][c] = self.tabs[r][c]
        self.tabs = tabs
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
        print(self.CSI + self.styles['CONS'] + self.CSI + '{};{}HExitCode={}, reason=\'{}\''.format(self.lastRow + 1, 1, code, reason))
        self.dbgFile.close()
        exit(code)
     
    def printHelpInfo(self, ui=None):
        '''Print help info.  If ui: explicitly call printTabs(), else: assume printTabs() will be called by the invoker.  [cmd line opt -h]'''
        self.clearScreen()
        self.printHelpSummary()
        self.printHelpUiCmds()
        print('{}'.format('Press any key'))
        b = ord(getwch())
        if ui:
            self.printTabs()

    def printHelpSummary(self):
        summary = '''
Note the console window should be at least as wide as the number of tabs + 2.  Window resizing is not supported.  
The command line arg -t is used so specify the number of tabs per string per line.  
The command line arg -f is used so specify the file name to read from and write to.  
The command line arg -s is used so specify the spelling of the string names e.g. -s 'E2A2D3G3B3E4' is 6 string standard guitar tuning.  

Tabs are displayed in the tabs section with an optional row to label and highlight the selected tab column.  
An optional notes section and an optional chords section can also be displayed below the tabs section.  
A number of lines can be displayed where each line has its own tabs, notes, and chords sections.  
''' + self.hilite('Tabs section:') + ''' 
Tabs are displayed using rows and columns of ASCII characters, essentially one character per tab.  
Tabs are represented by the single digits 0,1,2,3,4,5,6,7,8,9 and the letters a,b,c,d,e,f,g,h,i,j,k,l,m,n,o (rather than 10,11,12,..,24).  
The value '0' represents the open string.  The minus character '-' is used for padding and represents an unplayed string.  
The value '2' represents playing the string 1 full step above the nut, 'c' represents 12 half steps above the nut or an octave higher.  

Optional tab modification characters are used to denote tonal expression such as bending, sliding, hammer on/off, vibrato etc...  
Tab modifications are implemented as a customizable dictionary in the ''' + self.hilite('mods.py') + ''' module.  
You can change or add tab modifications by simply editing the ''' + self.hilite('mods.py') + ''' file. 
The dictionary keys are the modification characters and the values describe how to interpret the characters.  
When the cursor occupies the same row and column as a tab modifier the dictionary value is printed on the last row.  

Each row has a number of columns that represent the tab characters for a particular string as they are played sequentially in time from left to right.  
Rows are labelled using 1 based string numbers (increasing in the downward direction) in the first display column.  
The vertical pipe character '|' is used to represent the nut in the 2nd column with the string label to the left and all the tabs to the right.  
To enter a tab simply navigate to the desired row and column using the arrow, Home, End, PageUp, or PageDown keys and then enter the character.  
Note the cursor will automatically advance to the right, up, down, up and right, or down and right depending on the cursor mode.  
Also note the tabs section is the only section that is editable.  The navigation keys will automatically skip over the notes and or chords sections.  
''' + self.hilite('Notes section:  \'Ctrl N\'') + ''' 
The notes section has the same number of rows and columns as the tabs section and displays the note names corresponding to the tabs in the tabs section.  
The notes section uses the color red to indicate a sharp note and blue to represent a flat note.  
Note any optional tab modification characters present in the tabs section are also displayed in the notes section.  
''' + self.hilite('Chords section:  \'Ctrl N\'') + ''' 
Chords are spelled vertically so that they line up with the tabs and notes and potentially every column can display a chord.  
Chord names are automatically calculated and recalculated whenever the number of tabs in a given column is greater than one.  
The maximum chord name length is set to 5 and is not currently configurable.
The chords section also uses red to indicate a sharp chord and blue to represent a flat chord, but only on the first character, the root note.  
Minor and diminished chords use the color blue for the 'm' or the 'dim' characters.  

Note the tabs, notes, and chords can be saved to a file and if you 'cat' the file you can see the ANSI colors.  
        '''
        print(summary, file=self.dbgFile)
        print(summary)
        
    def printHelpUiCmds(self):
        print('{:>20} : {}'.format('User Interactive Cmd', 'Description'))
        print('{:>20} : {}'.format('User Interactive Cmd', 'Description'), file=self.dbgFile)
        print('--------------------------------------------------------------------------------')
        print('--------------------------------------------------------------------------------', file=self.dbgFile)
        for k in self.uiKeys:
            print('{:>20} : {}'.format(k, self.uiCmds[k].__doc__))
            print('{:>20} : {}'.format(k, self.uiCmds[k].__doc__), file=self.dbgFile)
    
    def registerUiCmds(self):
        self.registerUiCmd('Tablature',           self.setTab)
        self.registerUiCmd('Ctrl A',              self.toggleDisplayStatus)
        self.registerUiCmd('Ctrl B',              self.toggleDisplayChords)
        self.registerUiCmd('Ctrl C',              self.copySelectTabs)
        self.registerUiCmd('Ctrl D',              self.deleteSelectTabs)
        self.registerUiCmd('Ctrl E',              self.eraseTabs)
        self.registerUiCmd('Ctrl F',              self.toggleEnharmonic)
        self.registerUiCmd('Ctrl G',              self.goTo)
        self.registerUiCmd('Ctrl H or Backspace', self.deletePrevTab)
        self.registerUiCmd('Ctrl I or Tab',       self.toggleCursorDir)
        self.registerUiCmd('Ctrl J',              self.shiftSelectTabs)
        self.registerUiCmd('Ctrl K',              self.printChord)
        self.registerUiCmd('Ctrl M or Enter',     self.toggleCursorMode)
        self.registerUiCmd('Ctrl N',              self.toggleDisplayNotes)
        self.registerUiCmd('Ctrl Q',              self.quit)
        self.registerUiCmd('Ctrl R',              self.resetTabs)
        self.registerUiCmd('Ctrl S',              self.saveTabs)
        self.registerUiCmd('Ctrl T',              self.appendLine)
        self.registerUiCmd('Ctrl V',              self.pasteTabs)
        self.registerUiCmd('Ctrl X',              self.cutSelectTabs)
        self.registerUiCmd('Ctrl Z',              self.goToLastTab)
        self.registerUiCmd('Shift Z',             self.goToLastTab)
        self.registerUiCmd('Shift T',             self.removeLine)
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
        self.registerUiCmd('Ctrl Arrow Down',     self.harmonicNote)
        
    def registerUiCmd(self, key, method):
        if key not in self.uiKeys:
            self.uiCmds[key] = method
        self.uiKeys = sorted(self.uiCmds)
            
    def loop(self):
        while True:
            b = ord(getwch())
            if self.isTab(chr(b)):  self.uiCmds['Tablature'](b)   # setTab()               # N/A
            elif b == 1:   self.uiCmds['Ctrl A']()                # toggleDisplayStatus()  # cmd line opt  -a
            elif b == 2:   self.uiCmds['Ctrl B']()                # toggleDisplayChords()  # cmd line opt  -b
            elif b == 3:   self.uiCmds['Ctrl C']()                # copySelectTabs()       # N/A
            elif b == 4:   self.uiCmds['Ctrl D']()                # deleteSelectTabs()     # N/A
            elif b == 5:   self.uiCmds['Ctrl E']()                # eraseTabs()            #?cmd line opt?
            elif b == 6:   self.uiCmds['Ctrl F']()                # toggleEnharmonic()     # cmd line opt  -F?
            elif b == 7:   self.uiCmds['Ctrl G']()                # goTo()                 #?cmd line opt? -g
            elif b == 8:   self.uiCmds['Ctrl H or Backspace']()   # deletePrevTab()        # N/A
            elif b == 9:   self.uiCmds['Ctrl I or Tab']()         # toggleCursorDir()      # cmd line opt  -i
            elif b == 10:  self.uiCmds['Ctrl J']()                # shiftSelectTabs()      # N/A
            elif b == 11:  self.uiCmds['Ctrl K'](dbg=True)        # printChord()           # N/A
            elif b == 13:  self.uiCmds['Ctrl M or Enter']()       # toggleCursorMode()     # cmd line opt  -m
            elif b == 14:  self.uiCmds['Ctrl N']()                # toggleDisplayNotes()   # cmd line opt  -n
            elif b == 17:  self.uiCmds['Ctrl Q'](self.QUIT_STR)   # quit()                 # DBG?
            elif b == 18:  self.uiCmds['Ctrl R']()                # resetTabs()            # DBG?
            elif b == 19:  self.uiCmds['Ctrl S']()                # saveTabs()             # DBG?
            elif b == 20:  self.uiCmds['Ctrl T']()                # appendLine()           # DBG?
            elif b == 22:  self.uiCmds['Ctrl V']()                # pasteTabs()            # N/A
            elif b == 24:  self.uiCmds['Ctrl X']()                # cutSelectTabs()        # N/A
            elif b == 26:  self.uiCmds['Ctrl Z']()                # goToLastTab()          # cmd line opt -z
            elif b == 90:  self.uiCmds['Shift Z'](lastLine=False) # goToLastTab()          # cmd line opt -Z
            elif b == 84:  self.uiCmds['Shift T']()               # removeLine()           # DBG?
            elif b == 72:  self.uiCmds['Shift H'](ui=1)           # printHelpInfo()        # cmd line opt -h
            elif b == 32:  self.uiCmds['Space']()                 # moveCursor()           # N/A
            elif b == 224:                                        # Escape Sequence        # N/A
                b = ord(getwch())                                    # Read the escaped character
                if   b == 75:  self.uiCmds['Arrow Left']()           # moveLeft()             # N/A
                elif b == 77:  self.uiCmds['Arrow Right']()          # moveRight()            # N/A
                elif b == 72:  self.uiCmds['Arrow Up']()             # moveUp()               # N/A
                elif b == 80:  self.uiCmds['Arrow Down']()           # moveDown()             # N/A
                elif b == 71:  self.uiCmds['Home']()                 # moveHome()             #?cmd line opt?
                elif b == 79:  self.uiCmds['End']()                  # moveEnd()              #?cmd line opt?
                elif b == 73:  self.uiCmds['Page Up']()              # movePageUp()           #?cmd line opt?
                elif b == 81:  self.uiCmds['Page Down']()            # movePageDown()         #?cmd line opt?
                elif b == 82:  self.uiCmds['Insert']()               # toggleEditMode()       # cmd line opt
                elif b == 83:  self.uiCmds['Delete']()               # deleteTab()            # N/A
                elif b == 115: self.uiCmds['Ctrl Arrow Left'](False) # selectCol()            # N/A
                elif b == 116: self.uiCmds['Ctrl Arrow Right']()     # selectCol()            # N/A
                elif b == 145: self.uiCmds['Ctrl Arrow Down']()      # harmonicNote()         # N/A
                else:          self.unknown(b, 'Unknown Escape')
            else:              self.unknown(b, 'Unknown Key')
        
    def unknown(self, b, reason):
        if b == 0:            return
        elif b < 128:                                                self.printe('{:<17}:{}:{}'.format(reason, chr(b), b), self.row, self.col)
        elif b == 141:        self.unselectAllCols()               # self.printe('Ctrl Up Arrow  :{}:{}'.format(c, ord(c)), self.row, self.col) # 145
        elif b == 155:        self.unselectCol(False)              # self.printe('Alt Left Arrow   :{}:{}'.format(c, ord(c)), self.row, self.col) # 155
        elif b == 157:        self.unselectCol()                   # self.printe('Alt Right Arrow  :{}:{}'.format(c, ord(c)), self.row, self.col) # 157
        else: # down = 160, up = 152
            self.printe('{:<17}: :{}'.format(reason, b), self.row, self.col)

    def moveTo(self, row=None, col=None, hi=0):
        '''Move to given row and col (optionally hilite col num).'''
        dbg = 1
        if row is None: row = self.row
        else: self.row = row
        if col is None: col = self.col
        else: self.col = col
        if dbg: print('moveTo({}, {}, {}) old: row={}, col={}, line={}'.format(row, col, hi, self.row, self.col, self.row2Line(self.row)), file=self.dbgFile)
        print('{}{};{}H'.format(self.CSI, self.row, self.col), end='')
        self.printTabMod()
        if self.displayStatus == self.DISPLAY_STATUS['ENABLED'] and hi == 1:
            self.hiliteRowColNum()
   
    def moveLeft(self, dbg=None):
        '''Move cursor left one column on current line, wrapping to end of row on previous line or last line.'''
        if dbg or self.dbgMove: print('moveLeft({}, {})'.format(self.row, self.col), file=self.dbgFile)
        if self.col == self.bgnCol():
            line = self.row2Line(self.row)
            if line == 0:
                self.moveTo(row=self.row + self.lineDelta() * (self.numLines - 1), col=self.endCol(), hi=1)
            else:
                self.moveTo(row=self.row - self.lineDelta(), col=self.endCol(), hi=1)
        else:
            self.moveTo(col=self.col - 1, hi=1)

    def moveRight(self, dbg=None):
        '''Move cursor right one column on current line, wrapping to beginning of row on next line or first line.'''
        if dbg or self.dbgMove: print('moveRight({}, {})'.format(self.row, self.col), file=self.dbgFile)
        if self.col == self.endCol():
            line = self.row2Line(self.row)
            if line == self.numLines - 1:
                self.moveTo(row=self.row - self.lineDelta() * (self.numLines - 1), col=self.bgnCol(), hi=1)
            else:
                self.moveTo(row=self.row + self.lineDelta(), col=self.bgnCol(), hi=1)
        else:
            self.moveTo(col=self.col + 1, hi=1)
        
    def moveUp(self, dbg=None):
        '''Move cursor up one row on current line, wrapping to last row on previous line or last line.'''
        if dbg or self.dbgMove: print('moveUp({}, {})'.format(self.row, self.col), file=self.dbgFile)
        line = self.row2Line(self.row)
        if self.row == self.bgnRow(line):
            if line == 0:
                self.moveTo(row=self.endRow(self.numLines - 1), hi=1)
            else:
                self.moveTo(row=self.endRow(line - 1), hi=1)
        else:
            self.moveTo(row=self.row - 1, hi=1)
    
    def moveDown(self, dbg=None):
        '''Move cursor down one row on current line, wrapping to first row on next line or first line.'''
        if dbg or self.dbgMove: print('moveDown({}, {})'.format(self.row, self.col), file=self.dbgFile)
        line = self.row2Line(self.row)
        if self.row == self.endRow(line):
            if line == self.numLines - 1:
                self.moveTo(row=self.bgnRow(0), hi=1)
            else:
                self.moveTo(row=self.bgnRow(line + 1), hi=1)
        else:
            self.moveTo(row=self.row + 1, hi=1)
    
    def moveHome(self, dbg=None):
        '''Move cursor to beginning of row on current line, wrapping to end of row on previous line or last line.'''
        if dbg or self.dbgMove: print('moveHome({}, {})'.format(self.row, self.col), file=self.dbgFile)
        if self.col == self.bgnCol():
            line = self.row2Line(self.row)
            if line == 0:
                self.moveTo(row=self.row + self.lineDelta() * (self.numLines - 1), col=self.endCol(), hi=1)
            else:
                self.moveTo(row=self.row - self.lineDelta(), col=self.endCol(), hi=1)
        else:
            self.moveTo(col=self.bgnCol(), hi=1)
            
    def moveEnd(self, dbg=None):
        '''Move cursor to end of row on current line, wrapping to beginning of row on next line or first line.'''
        if dbg or self.dbgMove: print('moveEnd({}, {})'.format(self.row, self.col), file=self.dbgFile)
        if self.col == self.endCol():
            line = self.row2Line(self.row)
            if line == self.numLines - 1:
                self.moveTo(row=self.row - self.lineDelta() * (self.numLines - 1), col=self.bgnCol(), hi=1)
            else:
                self.moveTo(row=self.row + self.lineDelta(), col=self.bgnCol(), hi=1)
        else:
            self.moveTo(col=self.endCol(), hi=1)

    def movePageUp(self, dbg=None):
        '''Move cursor to first row on current line, wrapping to last row on previous line or last line.'''
        if dbg or self.dbgMove: self.printLineInfo('movePageUp({}, {})'.format(self.row, self.col))
        line = self.row2Line(self.row)
        if self.row == self.bgnRow(line):
            if line == 0:
                self.moveTo(row=self.endRow(self.numLines - 1), hi=1)
            else:
                self.moveTo(row=self.endRow(line - 1), hi=1)
        else:
            self.moveTo(row=self.bgnRow(line), hi=1)

    def movePageDown(self, dbg=None):
        '''Move cursor to last row on current line, wrapping to first row on next line or first line.'''
        if dbg or self.dbgMove: self.printLineInfo('movePageDown({}, {})'.format(self.row, self.col))
        line = self.row2Line(self.row)
        if self.row == self.endRow(line):
            if line == self.numLines - 1:
                self.moveTo(row=self.bgnRow(0), hi=1)
            else:
                self.moveTo(row=self.bgnRow(line + 1), hi=1)
        else:
            self.moveTo(row=self.endRow(line), hi=1)

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
    
    def indices2RowCol(self, r, c):
        row = r + self.ROW_OFF
        col = c + self.COL_OFF
        row += self.colIndex2Line(c) * self.lineDelta()
        col -= self.colIndex2Line(c) * self.numTabsPerStringPerLine
        return row, col
    
#    def foldRow(self, row):
#        line = self.row2Line(row)
#        print('foldRow({}) line={}'.format(row, line), file=self.dbgFile)
#        row += (line - 1) * self.lineDelta()
#        return row
        
    def foldColIndex(self, c):
        c -= self.colIndex2Line(c) * self.numTabsPerStringPerLine
        return c
        
    def bgnCol(self):
        return self.COL_OFF
        
    def endCol(self):
        return self.COL_OFF + self.numTabsPerStringPerLine - 1
        
    def lineDelta(self):
        return self.numStrings + self.NOTE_LEN + self.CHORD_LEN + 1
        
    def bgnRow(self, line):
        return self.ROW_OFF + line * self.lineDelta()
            
    def endRow(self, line):
        return self.ROW_OFF + line * self.lineDelta() + self.numStrings - 1
        
    def setLastRow(self):
        self.lastRow = self.ROW_OFF + self.numLines * self.lineDelta() - 1
    
    def toggleEditMode(self, dbg=None):
        '''Toggle cursor movement modes (insert or replace).'''
        self.editMode = (self.editMode + 1) % len(self.EDIT_MODES)
        if self.displayStatus == self.DISPLAY_STATUS['ENABLED']:
            for line in range(0, self.numLines):
                r = line * self.lineDelta() + 1
                if self.editMode == self.EDIT_MODES['INSERT']:
                    self.prints('I', r, self.editModeCol, self.styles['MODES'])
                elif self.editMode == self.EDIT_MODES['REPLACE']:
                    self.prints('R', r, self.editModeCol, self.styles['MODES'])
            if dbg: self.printLineInfo('toggleEditMode({}, {})'.format(self.row, self.col))
            self.moveTo()
    
    def toggleCursorMode(self, dbg=None):
        '''Toggle cursor movement modes (melody, chord, or arpeggio).'''
        self.cursorMode = (self.cursorMode + 1) % len(self.CURSOR_MODES)
        if self.displayStatus == self.DISPLAY_STATUS['ENABLED']:
            for line in range(0, self.numLines):
                r = line * self.lineDelta() + 1
                if self.cursorMode == self.CURSOR_MODES['MELODY']:
                    self.prints('M', r, self.cursorModeCol, self.styles['MODES'])
                elif self.cursorMode == self.CURSOR_MODES['CHORD']:
                    self.prints('C', r, self.cursorModeCol, self.styles['MODES'])
                elif self.cursorMode == self.CURSOR_MODES['ARPEGGIO']:
                    self.prints('A', r, self.cursorModeCol, self.styles['MODES'])
            if dbg: self.printLineInfo('toggleCursorMode({}, {})'.format(self.row, self.col))
            self.moveTo()

    def toggleCursorDir(self, dbg=None):
        '''Toggle direction (up or down) of cursor vertical movement.  [cmd line opt -i]'''
        self.cursorDir = (self.cursorDir + 1) % len(self.CURSOR_DIRS)
        for line in range(0, self.numLines):
            for r in range(0, self.numStrings):
                self.prints(self.CURSOR_DIR_INDS[self.cursorDir], r + self.bgnRow(line), self.COL_OFF - 1, self.styles['TABS'])
        if dbg: self.printLineInfo('toggleCursorDir({}, {}, {}, {})'.format(self.row, self.col, self.cursorDir, self.CURSOR_DIR_INDS[self.cursorDir]))
        self.moveTo()

    def toggleEnharmonic(self):
        '''Toggle display of enharmonic (sharp or flat) notes.  [cmd line opt -F]'''
        self.enharmonic = (self.enharmonic + 1) % len(self.ENHARMONIC)
        self.printTabs()
  
    def toggleDisplayStatus(self, printTabs=True):
        '''Toggle (enable or disable) display of status row.  [cmd line opt -a]'''
        self.displayStatus = (self.displayStatus + 1) % len(self.DISPLAY_STATUS)
        line = self.row2Line(self.row)
        if self.displayStatus == self.DISPLAY_STATUS['ENABLED']:
            self.ROW_OFF = 2
            self.row += 1
        elif self.displayStatus == self.DISPLAY_STATUS['DISABLED']:
            self.ROW_OFF = 1
            self.row -= 1
        self.setLastRow()
        self.printLineInfo('toggleDisplayStatus({}) row,col=({}, {}), line={},'.format(self.displayStatus, self.row, self.col, line))
        if printTabs:
            self.printTabs()
        
    def toggleDisplayNotes(self, printTabs=True):
        '''Toggle (enable or disable) display of notes section.  [cmd line opt -n]'''
        self.displayNotes = (self.displayNotes + 1) % len(self.DISPLAY_NOTES)
        line = self.row2Line(self.row)
        if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
            self.NOTE_LEN = self.numStrings
            self.row += line * self.NOTE_LEN
        elif self.displayNotes == self.DISPLAY_NOTES['DISABLED']:
            self.row -= line * self.NOTE_LEN
            self.NOTE_LEN = 0
        self.setLastRow()
        self.printLineInfo('toggleDisplayNotes({}) row,col=({}, {}), line={}'.format(self.displayNotes, self.row, self.col, line))
        if printTabs:
            self.printTabs()
    
    def toggleDisplayChords(self, printTabs=True):
        '''Toggle (enable or disable) display of chords section.  [cmd line opt -b]'''
        self.displayChords = (self.displayChords + 1) % len(self.DISPLAY_CHORDS)
        line = self.row2Line(self.row)
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.CHORD_LEN = 5
            self.row += line * self.CHORD_LEN
        elif self.displayChords == self.DISPLAY_CHORDS['DISABLED']:
            self.row -= line * self.CHORD_LEN
            self.CHORD_LEN = 0
        self.setLastRow()
        self.printLineInfo('toggleDisplayChords({}) row,col=({}, {}), line={}'.format(self.displayChords, self.row, self.col, line))
        if printTabs:
            self.printTabs()

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
#        self.moveTo()

    def printPageAndLine(self, r, line):
        self.prints('1', r, self.editModeCol, self.styles['MODES'])
        self.prints('{}'.format(line + 1), r, self.cursorModeCol, self.styles['MODES'])
    
    def printColNums(self, row):
        print('printColNums({})'.format(row), file=self.dbgFile)
        for c in range(0, self.numTabsPerStringPerLine):
            self.printColNum(row, c + 1, self.styles['NORMAL'])
#        self.moveTo()

    def printColNum(self, row, c, style):
        '''Print 1 based tab col index c as a single decimal digit.  
          123456789112345678921234567893123456789412345678951234567896123456789712345678981234567899123456789012345678911234567892123456789312345678941234567895
        '''
#        c += 1
#        print('printColNum({}, {}, {})'.format(row, c, style), file=self.dbgFile)
        if c % 10: 
            self.prints('{}'.format(c % 10), row, c + self.COL_OFF - 1, style + self.styles['MIN_COL_NUM'])
        elif c < 100: 
            self.prints('{}'.format(c // 10), row, c + self.COL_OFF - 1, style + self.styles['MAJ_COL_NUM'])
        else: 
            self.prints('{}'.format((c - 100) // 10), row, c + self.COL_OFF - 1, style + self.styles['MAJ_COL_NUM'])
    
    def selectCol(self, right=True):
        '''Select columns and hilite tabs with bright colors.  Columns need not be adjacent and the order is preserved.'''
        c = self.col2Index(self.col)
        self.selectCols.append(c)
        print('selectCol({}) (row,col)=({},{})'.format(c, self.row, self.col), file=self.dbgFile)
        self.setColStyle(c, self.styles['BRIGHT'])
        if right: self.moveRight()
        else: self.moveLeft()

    def unselectCol(self, right=True):
        if len(self.selectCols):
            c = self.col2Index(self.col)
            self.printLineInfo('unselectCol({}) (row,col)=({},{})'.format(c, self.row, self.col))
            print('unselectCol({}) selectCols = {}'.format(c, self.selectCols), file=self.dbgFile)
            if c in self.selectCols:
                self.selectCols.remove(c)
                self.setColStyle(c, self.styles['NORMAL'])
                print('unselectCol({}) after removing {} selectCols = {}'.format(c, c, self.selectCols), file=self.dbgFile)
                if right: self.moveRight()
                else: self.moveLeft()

    def unselectAllCols(self):
        self.printLineInfo('unselectAllCols({}, {})'.format(self.row, self.col))
        for c in range(0, len(self.selectCols)):
            self.setColStyle(self.selectCols[c], self.styles['NORMAL'])
        self.selectCols = []
        self.selectTabs = []
        self.numSelectCols = 0
        self.moveTo()
            
    def setColStyle(self, c, style):
        col = c
        for r in range(0, self.numStrings):
            tab = self.tabs[r][c]
            line = self.colIndex2Line(c)
            row = r + line * self.lineDelta()
            if r == 0:
                col -= line * self.numTabsPerStringPerLine
                print('setColStyle({}) c={}, col={}'.format(style, c, col), file=self.dbgFile)
            self.prints(chr(tab), row + self.ROW_OFF, col + self.COL_OFF, style + self.styles['TABS'])
            if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                if self.isFret(chr(tab)):
                    n = self.getNote(r + 1, tab)
                    self.printNote(row + self.ROW_OFF + self.numStrings, col + self.COL_OFF, n, style)
                else:
                    self.prints('{}'.format(chr(tab)), row + self.ROW_OFF + self.numStrings, col + self.COL_OFF, style + self.styles['NAT_NOTE'])

    def harmonicNote(self):
        '''Modify note making it a harmonic note - note these modifications are not currently saved to the data file.'''
        line = self.row2Line(self.row)
        r, c = self.rowCol2Indices(self.row, self.col)
#        c = self.col - self.COL_OFF + line * self.numTabsPerStringPerLine
#        r = self.row - self.ROW_OFF - line * self.lineDelta()
        tab = self.tabs[r][c]
        if self.isFret(chr(tab)) and self.getFretNum(tab) in self.HARMONIC_FRETS:
            self.harmonicNotes[r][c] = ord('1')
            print('harmonicNote({}, {}), r={}, c={}, tab={}'.format(self.row, self.col, r, c, chr(tab)), file=self.dbgFile)
            n = self.getHarmonicNote(r + 1, tab)
            self.prints('{}'.format(chr(tab)), self.row, self.col, self.styles['BRIGHT'] + self.styles['TABS'])
            if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                self.printNote(r + line * self.lineDelta() + self.endRow(0) + 1 , self.col, n, self.styles['BRIGHT'])
                self.moveTo()
            self.moveCursor()
        
    def setTab(self, tab):
        '''Set given tab character at the current row and col then move cursor according to the cursor mode.'''
        if self.bgnCol() <= self.col <= self.endCol() and ( self.ROW_OFF <= self.row <= self.endRow(1) or self.ROW_OFF <= self.row < self.ROW_OFF + self.numLines * self.lineDelta() ):
            row, col = self.row, self.col
            rr, cc = self.rowCol2Indices(row, col)
            print('setTab({}) (rr,cc)=({},{})'.format(chr(tab), rr, cc), file=self.dbgFile)
            if self.editMode == self.EDIT_MODES['INSERT']:
                for c in range(len(self.tabs[rr]) - 1, cc, - 1):
                    self.tabs[rr][c] = self.tabs[rr][c - 1]
            self.tabs[rr][cc] = tab
            if self.editMode == self.EDIT_MODES['INSERT']:
                self.printTabs()
            elif self.editMode == self.EDIT_MODES['REPLACE']:
                if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                    if self.isFret(chr(tab)):
                        note = self.getNote(rr + 1, tab)
                        self.printNote(row + self.numStrings, col, note)
                        print('setTab({}) note={}'.format(chr(tab), note.name), file=self.dbgFile)
                    else:
                        self.prints('{}'.format(chr(tab)), row + self.numStrings, col, self.styles['NAT_NOTE'])
                self.prints('{}'.format(chr(tab)), row, col, self.styles['TABS'])
                if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
                    noteCount = 0
                    for r in range(0, self.numStrings):
                        if self.isFret(chr(self.tabs[r][cc])):
                            noteCount += 1
                            if noteCount > 1:
                                self.printChord(c=cc)
                                break
            self.moveCursor(hi=1)
        else:
            info = 'row/col Exception in setTab({:d},{:d},{:c})'.format(self.row, self.col, tab)
            self.printe(info, self.row, self.col)

    def goTo(self):
        '''Go to tab location specified by user numeric input of up to 3 characters terminated by space char.'''
        cc, tmp = '', []
        while len(tmp) <= 3:
            cc = getwch()
            if cc != ' ' and '0' <= cc <= '9' : tmp.append(cc)
            else: break
        if len(tmp):
            c = int(''.join(tmp))
            self.moveTo(col=c + self.COL_OFF - 1, hi=1)
        
    def goToLastTab(self, lastLine=True):
        '''Go to last tab location (on the current line or the last line).'''
        rr, cc = 0, 0
        if lastLine:
            lineBgn = self.numLines
            lineEnd = 0
        else:
            lineBgn = self.row2Line(self.row) + 1
            lineEnd = lineBgn - 1
        print('goToLastTab({}, {}) lastLine={}, lineBgn={}, lineEnd={}'.format(self.row, self.col, lastLine, lineBgn, lineEnd), file=self.dbgFile)
        for line in range(lineBgn, lineEnd, -1):
            for r in range(0, self.numStrings):
                for c in range(line * self.numTabsPerStringPerLine - 1, (line - 1) * self.numTabsPerStringPerLine - 1, -1):
                    t = chr(self.tabs[r][c])
                    if t != '-' and self.isTab(t):
                        if c > cc:
                            rr = r
                            cc = c
                            ll = line
                            print('goToLastTab(updating col) t={}, line={}, r={}, c={}'.format(t, line, r, c), file=self.dbgFile)
                        break
        if cc > 0:
            row, col = self.indices2RowCol(rr, cc)
            print('goToLastTab() row,col=({},{})'.format(row, col), file=self.dbgFile)
            self.moveTo(row=row, col=col, hi=1)

    def moveCursor(self, row=None, col=None, hi=0):
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
        print('hiliteRowColNum({}, {}) rowNum={}, colNum={}, hiliteCount={}'.format(self.row, self.col, self.rowNum, self.colNum, self.hiliteCount), file=self.dbgFile)
        for line in range(0, self.numLines):
            row = line * self.lineDelta() + 1
            if self.colNum != 0:
                self.printColNum(row, self.colNum, self.styles['NORMAL'])
        self.colNum = self.col - self.COL_OFF + 1
        for line in range(0, self.numLines):
            row = line * self.lineDelta() + 1
            if self.colNum != 0:
                self.printColNum(row, self.colNum, self.styles['BRIGHT'])
                
        if self.rowNum != 0:
            self.prints(self.rowNum, self.rowNumPos, 1, self.styles['NORMAL'] + self.styles['TABS'])
        self.rowNum = self.row - self.row2Line(self.row) *  self.lineDelta() - 1
        self.rowNumPos = self.row
        print('hiliteRowColNum({}, {}) rowNum={}, colNum={}, hiliteCount={}'.format(self.row, self.col, self.rowNum, self.colNum, self.hiliteCount), file=self.dbgFile)
        self.prints(self.rowNum, self.row, 1, self.styles['BRIGHT'] + self.styles['TABS'])
        print(self.CSI + '{};{}H'.format(self.row, self.col), end='')

    def deleteTab(self, row=None, col=None):
        '''Delete current tab.'''
        if row is None: row = self.row
        if col is None: col = self.col
        r, c = self.rowCol2Indices(row, col)
        print('deleteTab() adjusted: row={}, col={}, r={}, c={}'.format(row, col, r, c), file=self.dbgFile)
        if self.editMode == self.EDIT_MODES['INSERT']:
            for cc in range(c, len(self.tabs[r])):
                if len(self.tabs[r]) > cc + 1:
                    self.tabs[r][cc] = self.tabs[r][cc + 1]
            self.printTabs()
        elif self.editMode == self.EDIT_MODES['REPLACE']:
            self.tabs[r][c] = ord('-')
            self.prints('{}'.format(chr(self.tabs[r][c])), row, col, self.styles['TABS'])
            if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                self.prints('{}'.format(chr(self.tabs[r][c])), row + self.numStrings, col, self.styles['NAT_NOTE'])
            if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
                self.eraseChord(c)
                self.printChord(c=c)
            self.moveTo(row=row, col=col)

    def deletePrevTab(self):
        '''Delete previous tab (backspace).'''
        self.moveTo(col=self.col - 1)
        self.deleteTab()
    
    def eraseChord(self, cc):
        row, col = self.indices2RowCol(self.numStrings + self.NOTE_LEN, cc)
#        print('eraseChord({}) (row,col)=({},{}) bgn: '.format(cc, row, col), file=self.dbgFile)
        for r in range(0, self.CHORD_LEN):
            self.prints(' ', r + row, col, self.styles['NAT_CHORD'])
        
    def eraseTabs(self):
        '''Erase all tabs (resets all tabs to '-').'''
        for r in range(0, len(self.tabs)):
            for c in range(0, len(self.tabs[r])):
                self.tabs[r][c] = ord('-')
        self.printTabs()

    def resetTabs(self):
        '''Reset all tabs to their initial state at start up.'''
        self.init()

    def saveTabs(self):
        '''Save all tabs (with ANSI codes) to the configured output file.  Use cat to display the file'''
        with open(self.outName, 'w') as self.outFile:
            print("saveTabs() bgn writing tabs to file: row=%d, col=%d" % (self.row, self.col), file=self.dbgFile)
#            print('numStrings:{}, NUM_TABS:{}, numLines:{}, NUM_TABS_PER_LINE:{}'.format(self.NUM_STR, self.NUM_TABS, self.numLines, self.NUM_TABS_PER_LINE), end='', file=self.outFile)
            self.clearScreen(2, file=self.outFile)
            self.printTabs()
            self.moveTo(hi=1)
            print(self.CSI + self.styles['NORMAL'] + self.styles['CONS'] + self.CSI + '{};{}H'.format(self.lastRow, 1), end='', file=self.outFile) # set the file cursor to the front of the next row (NUM_STR+r+1, 0) and set the foreground and background color
            print("saveTabs() end writing tabs to file: row=%d, col=%d" % (self.row, self.col), file=self.dbgFile)
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
                    else: self.printe('Error! shiftSelectTabs() Lower than open string! r,c,tab=({},{},{})'.format(self.row, self.col, chr(self.tabs[r][c])), self.row, self.col)
        if shifted:
            self.printTabs()
            
    def copySelectTabs(self):
        '''Copy selected tabs.'''
        for r in range(0, self.numStrings):
            self.selectTabs.append(bytearray([ord('+')] * len(self.selectCols)))
        for c in range(0, len(self.selectCols)):
            self.copyTabs(self.selectCols[c])
        
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
            del self.selectCols
            self.selectCols = []
        if self.displayChords == self.DISPLAY_NOTES['ENABLED']:
            self.printChords()
        self.moveTo()

    def cutSelectTabs(self):
        '''Cut selected tabs.'''
        self.copySelectTabs()
        self.deleteSelectTabs(delSel=False)
    
    def printSelectTabs(self):
        print('printSelectTabs()', file=self.dbgFile)
        for c in range(0, self.numSelectCols):
            print('col {}: '.format(c), end='', file=self.dbgFile)
            for r in range(0, self.numStrings):
                print('{}'.format(chr(self.selectTabs[r][c])), end='', file=self.dbgFile)
            print(file=self.dbgFile)
#        c = self.numSelectCols
#        if c >= 0:
#            print('printSelectTabs() col={}: {}'.format(c, [chr(self.selectTabs[r][c]) for r in range(0, self.numStrings)]), file=self.dbgFile)
    
    def copyTabs(self, col):
        for r in range(0, self.numStrings):
            self.selectTabs[r][self.numSelectCols] = self.tabs[r][col]
        self.numSelectCols += 1
        print('copyTabs({}), {}, {}'.format(col, self.numSelectCols, len(self.selectTabs)), file=self.dbgFile)
        self.printSelectTabs()

    def deleteTabs(self, cc):
        row, col = self.indices2RowCol(0, cc)
#        self.dumpTabs('deleteTabs({}, {}) (row,col)=({},{}), cc={} bgn: '.format(self.row, self.col, row, col, cc))
        if self.editMode == self.EDIT_MODES['INSERT']:
            for r in range(0, self.numStrings):
                for c in range(cc, len(self.tabs[r]) - 1):
                    self.tabs[r][c] = self.tabs[r][c + 1]
            self.printTabs()
        elif self.editMode == self.EDIT_MODES['REPLACE']:
            for r in range(0, self.numStrings):
                tab = ord('-')
                self.tabs[r][cc] = tab
                if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                    if self.isFret(chr(tab)):
                        self.printNote(r + row + self.numStrings, col, self.getNote(r + 1, tab))
                    else:
                        self.prints('{}'.format(chr(tab)), r + row + self.numStrings, col, self.styles['NAT_NOTE'])
                self.prints('{}'.format(chr(tab)), r + row, col, self.styles['TABS'])
#        self.dumpTabs('deleteTabs({}, {}) col={} end: '.format(self.row, self.col, col))
    
    def pasteTabs(self):
        '''Paste tabs.'''
        self.dumpTabs('pasteTabs({}, {}) bgn: '.format(self.row, self.col))
#        cc = self.col - self.COL_OFF
#        row, col = self.indices2RowCol(0, cc)
        row = self.ROW_OFF
        cc = self.col - self.COL_OFF
        col = self.col
        line = self.row2Line(self.row)
        row += line * self.lineDelta()
        cc += line * self.numTabsPerStringPerLine
        print('pasteTabs({}, {}, {}) (row,col,cc)=({},{},{})'.format(line, self.row, self.col, row, col, cc), file=self.dbgFile)
        if self.editMode == self.EDIT_MODES['INSERT']:
            for r in range(0, self.numStrings):
                for c in range(len(self.tabs[r]) - 1, cc, -1):
                    self.tabs[r][c] = self.tabs[r][c - self.numSelectCols]
        for c in range(0, self.numSelectCols):
            self.setColStyle(self.selectCols[c], self.styles['NORMAL'])
            for r in range(0, self.numStrings):
                if c + cc < self.numLines * self.numTabsPerStringPerLine:
                    self.tabs[r][c + cc] = self.selectTabs[r][c]
                    print('{}'.format(chr(self.tabs[r][c + cc])), end='', file=self.dbgFile)
            print(file=self.dbgFile)
#        self.dumpTabs('pasteTabs({}, {}) A: '.format(self.row, self.col))
        if self.editMode == self.EDIT_MODES['INSERT']:
            self.printTabs()
        elif self.editMode == self.EDIT_MODES['REPLACE']:
            for r in range(0, self.numStrings):
                for c in range(0, self.numSelectCols):
                    if c + cc < self.numLines * self.numTabsPerStringPerLine:
                        tab = self.tabs[r][c + cc]
                        if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
                            if self.isFret(chr(tab)):
                                self.printNote(row + self.numStrings + r, col + c, self.getNote(r + 1, tab))
                            else:
                                self.prints('{}'.format(chr(tab)), row + self.numStrings + r, col + c, self.styles['NAT_NOTE'])
                        self.prints('{}'.format(chr(tab)), row + r, col + c, self.styles['TABS'])
            self.moveTo() #self.row, self.col
        self.numSelectCols = 0
        del self.selectTabs
        self.selectTabs = []
        del self.selectCols
        self.selectCols = []
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.printChords()
        self.moveTo()
#        self.dumpTabs('pasteTabs({}, {}) end: '.format(self.row, self.col))
        
    def dumpTabs(self, reason=''):
        print('dumpTabs({}) [ Line 0:'.format(reason), file=self.dbgFile)
        for line in range(0, self.numLines):
            for r in range(0, self.numStrings): #len(self.tabs)):
                for c in range(0, self.numTabsPerStringPerLine):
                    print(chr(self.tabs[r][c + line * self.numTabsPerStringPerLine]), end='', file=self.dbgFile)
#                    print(chr(self.harmonicNotes[r][c + line * self.numTabsPerStringPerLine]), end='', file=self.dbgFile)
                print('', file=self.dbgFile)
            if line < self.numLines - 1:
                print('] [ Line {}:'.format(line + 1), file=self.dbgFile)
        print(']', file=self.dbgFile)
    
    def printLineInfo(self, reason):
        print('{} numStrings={}, numLines={}, lineDelta={},'.format(reason, self.numStrings, self.numLines, self.lineDelta()), end='', file=self.dbgFile)
        for line in range(0, self.numLines):
            print(' bgnRow{}={}, endRow{}={},'.format(line, self.bgnRow(line), line, self.endRow(line)), end='', file=self.dbgFile)
        print(' lastRow={}, bgnCol={}, endCol={}'.format(self.lastRow, self.bgnCol(), self.endCol()), file=self.dbgFile)
    
    def printTabs(self):
        '''Print tabs using ANSI escape sequences supported by Colorama to control the cursor x and y position, foreground and background color, and brightness'''
        self.printLineInfo('printTabs({}, {}) bgn'.format(self.row, self.col))
        if self.outFile == None: self.clearScreen()
        self.printFileMark('<BGN_TABS_SECTION>')
#        rowLabel = 0
        for line in range(0, self.numLines):
            for r in range(0, self.numStrings):
#                rowLabel += 1
                row = r + line * self.lineDelta() + self.ROW_OFF
                for c in range(0, self.numTabsPerStringPerLine):
                    tab = self.tabs[r][c + line * self.numTabsPerStringPerLine]
                    style = self.styles['TABS']
                    if chr(self.harmonicNotes[r][c + line * self.numTabsPerStringPerLine]) == '1': style += colorama.Style.BRIGHT
                    if c == 0:
#                        self.prints('{}'.format(rowLabel),    row, 1, self.styles['TABS'])
                        self.prints('{}'.format(r + 1), row, 1, style)
                        self.prints(self.CURSOR_DIR_INDS[self.cursorDir], row, 2, style)
                    self.prints('{}'.format(chr(tab)), row, c + self.COL_OFF, style)
                print(file=self.outFile)
            print()
        self.printFileMark('<END_TABS_SECTION>')
        if self.displayNotes == self.DISPLAY_NOTES['ENABLED']:
            self.printFileMark('<BGN_NOTES_SECTION>')
            for line in range(0, self.numLines):
                for r in range(0, self.numStrings):
                    row = r + line * self.lineDelta() + self.endRow(0) + 1
                    for c in range (0, self.numTabsPerStringPerLine):
                        tab = self.tabs[r][c + line * self.numTabsPerStringPerLine]
                        if c == 0:
                            n = self.getNote(r + 1, ord('0'))
                            self.printNote(row, 1, n)
                            self.prints(self.CURSOR_DIR_INDS[self.cursorDir], row, 2, self.styles['NAT_NOTE'])
                        if self.isFret(chr(tab)):
                            if chr(self.harmonicNotes[r][c + line * self.numTabsPerStringPerLine]) == '1':
                                n = self.getHarmonicNote(r + 1, tab)
                                self.printNote(row, c + self.COL_OFF, n, self.styles['BRIGHT'])
                            else:
                                n = self.getNote(r + 1, tab)
                                self.printNote(row, c + self.COL_OFF, n)
                        else:
                            self.prints('{}'.format(chr(tab)), row, c + self.COL_OFF, self.styles['NAT_NOTE'])
                    print(file=self.outFile)
                print()
            self.printFileMark('<END_NOTES_SECTION>')
        if self.displayChords == self.DISPLAY_CHORDS['ENABLED']:
            self.printFileMark('<BGN_CHORDS_SECTION>')
            self.printChords()
            self.printFileMark('<END_CHORDS_SECTION>')
        if self.displayStatus == self.DISPLAY_STATUS['ENABLED']:
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
            print(self.CSI + self.styles['NORMAL'] + self.styles['CONS'] + self.CSI + '{};{}H'.format(self.row, self.col), end='')           # restore the console cursor to the given position (row, col) and set the foreground and background color
        self.printLineInfo('printTabs({}, {}) end'.format(self.row, self.col))

    def printFileMark(self, mark):
        if self.outFile != None:
            if mark == '<BGN_TABS_SECTION>' or mark == '<END_TABS_SECTION>':
                print('{}'.format(mark), file=self.outFile)
            else:
                print(self.CSI + self.styles['NORMAL'] + self.styles['CONS'] + self.CSI + '{};{}H{}'.format(1, 1, mark), file=self.outFile)
    
    def printNote(self, row, col, note, style=''):
        try:
            if len(note.name) > 1:
                if note.name[1] == '#':
                    if self.enharmonic == self.ENHARMONIC['FLAT']:
                        note.name = self.SHARPS_2_FLATS[note.name]
                        self.prints(note.name[0], row, col, style + self.styles['FLT_NOTE'])
                    else:
                        self.prints(note.name[0], row, col, style + self.styles['SHP_NOTE'])
                elif note.name[1] == 'b':
                    if self.enharmonic == self.ENHARMONIC['SHARP']:
                        note.name = self.FLATS_2_SHARPS[note.name]
                        self.prints(note.name[0], row, col, style + self.styles['SHP_NOTE'])
                    else:
                        self.prints(note.name[0], row, col, style + self.styles['FLT_NOTE'])
            else:
                self.prints(note.name[0], row, col, style + self.styles['NAT_NOTE'])
        except:
            e = sys.exc_info()[0]
            info = 'Exception {:s} in printNote({:d},{:d},{:c})'.format(str(e), row, col, note)
            self.printe(info, row, col)

    def printTabMod(self):
        r, c = self.rowCol2Indices(self.row, self.col)
        key = chr(self.tabs[r][c])
        if key in self.mods:
            print('printTabMod({}, {}) r={}, c={}'.format(self.row, self.col, r, c), file=self.dbgFile)
            prev = chr(self.tabs[r][c-1])
            next = chr(self.tabs[r][c+1])
            dir, dir2 = None, None
            if prev < next:
                dir = 'up'
                dir2 = 'on'
            elif prev > next:
                dir = 'down'
                dir2 = 'off'
            self.modsObj.setMods(dir, prev, next, dir2)
            print('printTabMod() \'{}\' = {}'.format(key, self.mods[key]), file=self.dbgFile)
            style = self.styles['ERROR']
            print(self.CSI + style + self.CSI + '{};{}H{} {}'.format(self.lastRow, 1, key, self.mods[key]), end='')
            self.lastRowDirty = 1
        elif self.lastRowDirty:
            print(self.CSI + '{};{}H'.format(self.lastRow, 1), end='')
            print('printTabMod() clearing dirty last row={}'.format(self.lastRow), file=self.dbgFile)
            self.clearRow()
            self.lastRowDirty = 0
        print(self.CSI + '{};{}H'.format(self.row, self.col), end='')
 
    def prints(self, c, row, col, style):
        if self.outFile:
            print(self.CSI + style + self.CSI + '{};{}H{}'.format(row, col, str(c)), end='', file=self.outFile)
        else:
            print(self.CSI + style + self.CSI + '{};{}H{}'.format(row, col, str(c)), end='')

    def printe(self, c, row, col, colors=None):
        if colors == None: colors = self.styles['ERROR']
        print(colors +  '{}{};{}H{}'.format(self.CSI, self.lastRow, self.COL_OFF, repr(c)), end='')
#        if self.outFile:
#            print(colors +  '{}{};{}H{}'.format(self.CSI, self.lastRow, self.COL_OFF, repr(c)), end='', file=self.dbgFile)
        self.printLineInfo('printe({}, {}) ERROR: "{}"'.format(self.row, self.col, c))
        if self.ROW_OFF <= row <= self.endRow(1) and self.bgnCol() <= col <= self.endCol() or self.bgnRow(2) <= row <= self.endRow(2) and self.bgnCol() <= col <= self.endCol():
            self.moveTo(row=row, col=col)
        self.lastRow += 1
            
    def getNote(self, str, tab):
        fret = self.getFretNum(tab)
        return notes.Note(self.getNoteIndex(str, fret))

    def getHarmonicNote(self, str, tab):
        fret = self.getFretNum(tab)
        delta = self.HARMONIC_FRETS[fret]
        note = notes.Note(self.getNoteIndex(str, delta))
        print('getHarmonicNote() f={}, d={}, ni={}, nn={}, no={})'.format(fret, delta, note.index, note.name, note.getOctv()), file=self.dbgFile)
        return note
        
    def getNoteIndex(self, str, f):
        '''Converts string numbering from 1 based with str=1 denoting the high E first string and str=numStrings the low E sixth string.'''
        s = self.numStrings - str                     # Reverse and zero base the string numbering: str[1 ... numStrings] => s[(numStrings - 1) ... 0]
        i = self.stringMap[self.stringKeys[s]] + f    # calculate the fretted note index using the sorted map
#        print('getNoteIndex() str={}, s={}, f={}, i={}, sk={}, sm={}'.format(str, s, f, i, self.stringKeys[s], self.stringMap[self.stringKeys[s]]), file=self.dbgFile)
        return i
        
    def printChords(self):
        print('printChords({}, {}) bgn {} =?= {} * {}'.format(self.row, self.col, self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine), file=self.dbgFile)
        for c in range(0, self.numTabsPerString):
            noteCount = 0
            self.eraseChord(c)
            for r in range(0, self.numStrings):
                if self.isFret(chr(self.tabs[r][c])):
                    if noteCount > 0:
                        self.printChord(c=c)
                        break
                    noteCount += 1
            print(file=self.outFile)
        print('printChords({}, {}) end {} =?= {} * {}'.format(self.row, self.col, self.numTabsPerString, self.numLines, self.numTabsPerStringPerLine), file=self.dbgFile)
        
    def printChord(self, c=None, dbg=True):
        '''Analyse and if a valid chord is discovered then print it in the appropriate chords section.'''
        if c is None:
            c = self.col - self.COL_OFF
        self.eraseChord(c)
        row, col = self.indices2RowCol(self.numStrings + self.NOTE_LEN, c)
        if dbg:
            print('printChord({}) (row,col)=({},{}) end: '.format(c, row, col), file=self.dbgFile)
            print('Strings     [', end='', file=self.dbgFile)
            for r in range(self.numStrings - 1, -1, -1):
                if self.isFret(chr(self.tabs[r][c])):
                    note = self.getNote(r + 1, 0)
                    print('{:>3}/{:<1}'.format(r+1, note.name[0]), end=' ', file=self.dbgFile)
        
        tbs = []
        for r in range(0, self.numStrings): 
            if self.isFret(chr(self.tabs[r][c])):
                tbs.append(chr(self.tabs[r][c]))
        tbs.reverse()
        if dbg:
            print(']\ntabs        [', end='', file=self.dbgFile)
            for t in range(len(tbs)):
                print('{:>5}'.format(tbs[t]), end=' ', file=self.dbgFile)
        notes = []
        for r in range(0, self.numStrings):
            if self.isFret(chr(self.tabs[r][c])):
                if chr(self.harmonicNotes[r][c]) == '1':
                    note = self.getHarmonicNote(r + 1, self.tabs[r][c])
                else:
                    note = self.getNote(r + 1, self.tabs[r][c])
                if len(note.name) > 1 and note.name[1] == '#' and self.enharmonic == self.ENHARMONIC['FLAT']:
                    note.name = self.SHARPS_2_FLATS[note.name]
                elif len(note.name) > 1 and note.name[1] == 'b' and self.enharmonic == self.ENHARMONIC['SHARP']:
                    note.name = self.FLATS_2_SHARPS[note.name]
                notes.append(note.name)
        notes.reverse()
        if dbg:
            print(']\nnotes       [', end='', file=self.dbgFile)
            for t in range(len(tbs)):
                print('{:>5}'.format(notes[t]), end=' ', file=self.dbgFile)
        indices = []
        for r in range(0, self.numStrings):
            if self.isFret(chr(self.tabs[r][c])):
                if chr(self.harmonicNotes[r][c]) == '1':
                    note = self.getHarmonicNote(r + 1, self.tabs[r][c])
                    indices.append(note.index)
                else:
                    note = self.getNote(r + 1, self.tabs[r][c])
                    indices.append(note.index)
        indices.reverse()
        if dbg:
            print(']\nindices     [', end='', file=self.dbgFile)
            for t in range(len(tbs)):
                print('{:>5}'.format(indices[t]), end=' ', file=self.dbgFile)
            print(']', file=self.dbgFile)
        
        for j in range(len(indices)):
            deltas = []
            for i in range(0, len(indices)):
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
                print('deltas      [', end='', file=self.dbgFile)
                for t in range(len(tbs)):
                    print('{:>5}'.format(deltas[t]), end=' ', file=self.dbgFile)
            intervals = []
            for i in range(0, len(deltas)):
                intervals.append(self.INTERVALS[deltas[i]])
            if dbg:
                print(']\nintervals   [', end='', file=self.dbgFile)
                for t in range(len(tbs)):
                    print('{:>5}'.format(intervals[t]), end=' ', file=self.dbgFile)
            
            imap = dict(zip(intervals, notes))
            imapKeys = sorted(imap, key=self.imapKeyFunc, reverse=False)
            chordKeys = [ imap[k] for k in imapKeys ]
            chordKey = self.getChordKey(chordKeys)
            if dbg:
                print(']\niMap        [', end='', file=self.dbgFile)
                for k in imap:
                    print('{:>2}:{:<2}'.format(k, imap[k]), end=' ', file=self.dbgFile)
                print(']\nimapKeys    [', end='', file=self.dbgFile)
                for k in imapKeys:
                    print('{:>5}'.format(k), end=' ', file=self.dbgFile)
                print(']\nchordKeys   [', end='', file=self.dbgFile)
                for k in chordKeys:
                    print('{:>5}'.format(k), end=' ', file=self.dbgFile)
                print(']\nchords      [', end=' ', file=self.dbgFile)
                for k in self.chords:
                    print('{:>5}:{:<5}'.format(k, self.chords[k]), end=' ', file=self.dbgFile)
                print(']', file=self.dbgFile)
#                print(']\nprintChord({}) [{}]'.format(c, chordName), file=self.dbgFile)
            
            chordName = None
            if chordKey not in self.chords:
                if dbg: print('printChord() Key = \'{}\' not found in chords - calculating value'.format(chordKey), file=self.dbgFile)
                chordName = self.getChordName(imap)
                if chordName and len(chordName) > 0:
                    self.chords[chordKey] = chordName
                    if dbg:
                        print('printChord() Adding Key = \'{}\', value = \'{}\' to chords'.format(chordKey, self.chords[chordKey]), file=self.dbgFile)
                        print('chords      [', end=' ', file=self.dbgFile)
                        for k in self.chords:
                            print('{:>5}:{:<5}'.format(k, self.chords[k]), end=' ', file=self.dbgFile)
                        print(']', file=self.dbgFile)
            else: 
                if dbg: print('printChord() Found key = \'{}\', value = \'{}\' in chords'.format(chordKey, self.chords[chordKey]), file=self.dbgFile)
                chordName = self.chords[chordKey]
            if chordName != None:
                for i in range(len(chordName)):
                    style = self.styles['NAT_CHORD']
                    if i == 0:
                        if len(imap['R']) > 1:
                            if imap['R'][1] == '#':
                                if self.enharmonic == self.ENHARMONIC['FLAT']:
                                    style = self.styles['FLT_CHORD']
                                else:
                                    style = self.styles['SHP_CHORD']
                            elif imap['R'][1] == 'b':
                                if self.enharmonic == self.ENHARMONIC['SHARP']:
                                    style = self.styles['SHP_CHORD']
                                else:
                                    style = self.styles['FLT_CHORD']
                    if chordName[i] == 'm' or 'dim' in chordName and chordName[i] == 'd' or chordName[i] == 'i':
                        style = self.styles['FLT_CHORD']
                    self.prints(chordName[i], i + row, col, style)
#                    self.moveTo()
                break

    def imapKeyFunc(self, inKey):
        return self.INTERVAL_RANK[inKey]
        
    def getChordKey(self, keys):
        return '-'.join(keys)
        
    def getChordName(self, imap):
        '''Calculate chord name.'''
        r = imap['R'][0]
        if 'R' in imap:
            if '5' in imap: 
                if len(imap) == 2:                            return '{}5'.format(r)
                elif 'M3' in imap:
                    if len(imap) == 3:                        return '{}'.format(r)
                    elif len(imap) == 4:
                        if   'b7' in imap:                    return '{}7'.format(r)
                        elif  '7' in imap:                    return '{}M7'.format(r)
                        elif  '6' in imap or '13' in imap:    return '{}6'.format(r)
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
        return None
        
    def isTab(self, c):
        if c == '-' or self.isFret(c) or self.isMod(c):
            return True
        return False

    @classmethod
    def isFret(cls, c):
        if '0' <= c <= '9' or 'a' <= c <= 'o':
            return True
        return False

    def isMod(self, c):
        if c in self.mods: return True
        return False

    @staticmethod
    def getFretNum(fretByte):
        fretNum = fretByte - ord('0')
        if fretByte >= ord('a'): fretNum = fretByte - (ord('a') - 10)
        return fretNum
        
    @staticmethod
    def clearScreen(arg=2, file=None):
        if not file: print('{}{}J'.format(Tabs.CSI, arg))
        else:        print('{}{}J'.format(Tabs.CSI, arg), file=file)

    @staticmethod
    def clearRow(arg=2, file=None):
        if not file: print('{}{}K'.format(Tabs.CSI, arg), end='')
        else:        print('{}{}K'.format(Tabs.CSI, arg), end='', file=file)
        
    @staticmethod
    def hilite(text):
        return colorama.Back.GREEN + colorama.Fore.RED + text + colorama.Back.BLACK + colorama.Fore.WHITE
        
def main():
    Tabs()

if __name__ == "__main__":
    main()

# NOTE to fix the console display from a bad run try the color cmd, 'Color ?' or 'Color 07' restores white on black.
'''
e.g. Here is a C Major chord played on a six string guitar in standard tuning 'E2A2D3G3B3E4'
1|0
2|1
3|0
4|2
5|3
6|-
E|E
B|C
G|G
D|E
A|C
E|-

e.g. Carlos Santana, Black Magic Woman, on 6 string guitar with standard tuning 'E2A2D3G3B3E4':
  1234567891123456789212345678931234567894123456789512345678961234567897123456789812345678991234567890123456789112345678921234567893123456789412345678951234567896
1|----------------------------------5=-------------------5=---------------------a--a------------------------------------------------------------------------------
2|6+8+6==----------6+8+6==------------8=6/5==-8=6=5/3==----8=6/5==-8=6=5/3==---a-----d-f\d\f----------------------------------------------------------------------
3|--------7\9\7==----------7\9\7==--------------------------------------------a-----------------------------------------------------------------------------------
4|----------------------------------------------------------------------------------------------------------------------------------------------------------------
5|----------------------------------------------------------------------------------------------------------------------------------------------------------------
6|----------------------------------------------------------------------------------------------------------------------------------------------------------------

Desired features list:
X    Usage guide
X    Cut and paste column of tabs
?    Add row number labels and hilite them
    Save harmonic note info?
    Compress arpeggio -> chord, expand chord -> arpeggio?
    Print arpeggio chord names?
    Analysis for key signature calculation
    Improve file I/O and usage
    Scroll through pages and lines
    Handle window resizing
    Undo/redo functionality
    Unicode chars
    Indicate rhythmic info like note duration and rests etc
    Display sheet music notation
    Unit tests and or regression tests
'''
