'''notes.py module.  class list: [Note].'''
            
class Note(object):
    '''Model a musical note played on a stringed instrument.'''
    
    NUM_SEMI_TONES = 12
    S_TONES = { 0:'C', 1:'C#', 2:'D', 3:'D#', 4:'E', 5:'F', 6:'F#', 7:'G', 8:'G#', 9:'A', 10:'A#', 11:'B' }
    F_TONES = { 0:'C', 1:'Db', 2:'D', 3:'Eb', 4:'E', 5:'F', 6:'Gb', 7:'G', 8:'Ab', 9:'A', 10:'Bb', 11:'B' }
    
    INDICES = { 'C0': 0, 'C#0': 1, 'Db0': 1, 'D0': 2, 'D#0': 3, 'Eb0': 3, 'E0': 4, 'F0': 5, 'F#0': 6, 'Gb0': 6, 'G0': 7, 'G#0': 8, 'Ab0': 8, 'A0': 9, 'A#0':10, 'Bb0':10, 'B0':11,
                'C1':12, 'C#1':13, 'Db1':13, 'D1':14, 'D#1':15, 'Eb1':15, 'E1':16, 'F1':17, 'F#1':18, 'Gb1':18, 'G1':19, 'G#1':20, 'Ab1':20, 'A1':21, 'A#1':22, 'Bb1':22, 'B1':23,
                'C2':24, 'C#2':25, 'Db2':25, 'D2':26, 'D#2':27, 'Eb2':27, 'E2':28, 'F2':29, 'F#2':30, 'Gb2':30, 'G2':31, 'G#2':32, 'Ab2':32, 'A2':33, 'A#2':34, 'Bb2':34, 'B2':35,
                'C3':36, 'C#3':37, 'Db3':37, 'D3':38, 'D#3':39, 'Eb3':39, 'E3':40, 'F3':41, 'F#3':42, 'Gb3':42, 'G3':43, 'G#3':44, 'Ab3':44, 'A3':45, 'A#3':46, 'Bb3':46, 'B3':47,
                'C4':48, 'C#4':49, 'Db4':49, 'D4':50, 'D#4':51, 'Eb4':51, 'E4':52, 'F4':53, 'F#4':54, 'Gb4':54, 'G4':55, 'G#4':56, 'Ab4':56, 'A4':57, 'A#4':58, 'Bb4':58, 'B4':59,
                'C5':60, 'C#5':61, 'Db5':61, 'D5':62, 'D#5':63, 'Eb5':63, 'E5':64, 'F5':65, 'F#5':66, 'Gb5':66, 'G5':67, 'G#5':68, 'Ab5':68, 'A5':69, 'A#5':70, 'Bb5':70, 'B5':71,
                'C6':72, 'C#6':73, 'Db6':73, 'D6':74, 'D#6':75, 'Eb6':75, 'E6':76, 'F6':77, 'F#6':78, 'Gb6':78, 'G6':79, 'G#6':80, 'Ab6':80, 'A6':81, 'A#6':82, 'Bb6':82, 'B6':83,
                'C7':84, 'C#7':85, 'Db7':85, 'D7':86, 'D#7':87, 'Eb7':87, 'E7':88, 'F7':89, 'F#7':90, 'Gb7':90, 'G7':91, 'G#7':92, 'Ab7':92, 'A7':93, 'A#7':94, 'Bb7':94, 'B7':95, 
                'C8':96 } # For simplicity omit double flats and double sharps and other redundant enharmonic note names e.g. Abb, C##, Cb, B#, Fb, E#

    def __init__(self, index, sharps=None):
        '''The index identifies the note value, the name is looked up using the TONES dictionary.'''
        self._index = index
        if sharps is None or sharps is 0:
            self._name = self.F_TONES[index % len(self.F_TONES)]
        else:
            self._name = self.S_TONES[index % len(self.S_TONES)]
   
    @property
    def index(self):
        return self._index
    
    @property
    def name(self):
        return self._name
        
    @index.setter
    def index(self, index):
        self._index = index

    @name.setter
    def name(self, name):
        self._name = name
        
    def getOctaveNum(self):
        return int(self.index / len(self.S_TONES)) # Essentially the same as the piano octave number

    def getPhysProps(self):
        freq, freqUnit = self.getFreqInfo()
        waveLen, waveLenUnit = self.getWaveLenInfo(freq)
        return 'freq={:03.2f} {}, waveLen={:04.3f} {}'.format(freq, freqUnit, waveLen, waveLenUnit)
        
    def getFreqInfo(self):
        return self.getFreq(), 'Hz'

    def getFreq(self):
        return 440.0 * pow(pow(2, 1/self.NUM_SEMI_TONES), self.index - self.INDICES['A4'])
    
    def getWaveLenInfo(self, freq=None):
        if freq is None: return 343 / self.getFreq(), 'm'
        else:            return 343 / freq, 'm'
            
    def getWaveLen(self, freq=None):
        if freq is None: return 343 / self.getFreq()
        else:            return 343 / freq

#    def getPianoIndex(self):
#        return self.index - 8                      # The lowest piano key is 'A0', INDICES['A0'] = 9, so subtract 8 from our index to yield the 1 based piano index
        
#NAMES = { 0:'C0',  1:'C#0',  2:'D0',  3:'D#0',  4:'E0',  5:'F0',  6:'F#0',  7:'G0',  8:'G#0',  9:'A0', 10:'A#0', 11:'B0',
#         12:'C1', 13:'C#1', 14:'D1', 15:'D#1', 16:'E1', 17:'F1', 18:'F#1', 19:'G1', 20:'G#1', 21:'A1', 22:'A#1', 23:'B1', 
#         24:'C2', 25:'C#2', 26:'D2', 27:'D#2', 28:'E2', 29:'F2', 30:'F#2', 31:'G2', 32:'G#2', 33:'A2', 34:'A#2', 35:'B2', 
#         36:'C3', 37:'C#3', 38:'D3', 39:'D#3', 40:'E3', 41:'F3', 42:'F#3', 43:'G3', 44:'G#3', 45:'A3', 46:'A#3', 47:'B3', 
#         48:'C4', 49:'C#4', 50:'D4', 51:'D#4', 52:'E4', 53:'F4', 54:'F#4', 55:'G4', 56:'G#4', 57:'A4', 58:'A#4', 59:'B4', 
#         60:'C5', 61:'C#5', 62:'D5', 63:'D#5', 64:'E5', 65:'F5', 66:'F#5', 67:'G5', 68:'G#5', 69:'A5', 70:'A#5', 71:'B5', 
#         72:'C6', 73:'C#6', 74:'D6', 75:'D#6', 76:'E6', 77:'F6', 78:'F#6', 79:'G6', 80:'G#6', 81:'A6', 82:'A#6', 83:'B6', 
#         84:'C7', 85:'C#7', 86:'D7', 87:'D#7', 88:'E7', 89:'F7', 90:'F#7', 91:'G7', 92:'G#7', 93:'A7', 94:'A#7', 95:'B6', 
#         96:'C8' } # Probably not needed - just use the getOvactaveNum() method and TONES dictionary.
        