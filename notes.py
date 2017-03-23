'''notes.py module.  class list: [Note].'''

TONES = { 0:'C', 1:'C#', 2:'D', 3:'D#', 4:'E', 5:'F', 6:'F#', 7:'G', 8:'G#', 9:'A', 10:'A#', 11:'B' } # For simplicity omit the enharmonic flat notes

INDICES = { 'C0': 0, 'C#0': 1, 'Db0': 1, 'D0': 2, 'D#0': 3, 'Eb0': 3, 'E0': 4, 'F0': 5, 'F#0': 6, 'Gb0': 6, 'G0': 7, 'G#0': 8, 'Ab0': 8, 'A0': 9, 'A#0':10, 'Bb0':10, 'B0':11,
            'C1':12, 'C#1':13, 'Db1':13, 'D1':14, 'D#1':15, 'Eb1':15, 'E1':16, 'F1':17, 'F#1':18, 'Gb1':18, 'G1':19, 'G#1':20, 'Ab1':20, 'A1':21, 'A#1':22, 'Bb1':22, 'B1':23,
            'C2':24, 'C#2':25, 'Db2':25, 'D2':26, 'D#2':27, 'Eb2':27, 'E2':28, 'F2':29, 'F#2':30, 'Gb2':30, 'G2':31, 'G#2':32, 'Ab2':32, 'A2':33, 'A#2':34, 'Bb2':34, 'B2':35,
            'C3':36, 'C#3':37, 'Db3':37, 'D3':38, 'D#3':39, 'Eb3':39, 'E3':40, 'F3':41, 'F#3':42, 'Gb3':42, 'G3':43, 'G#3':44, 'Ab3':44, 'A3':45, 'A#3':46, 'Bb3':46, 'B3':47,
            'C4':48, 'C#4':49, 'Db4':49, 'D4':50, 'D#4':51, 'Eb4':51, 'E4':52, 'F4':53, 'F#4':54, 'Gb4':54, 'G4':55, 'G#4':56, 'Ab4':56, 'A4':57, 'A#4':58, 'Bb4':58, 'B4':59,
            'C5':60, 'C#5':61, 'Db5':61, 'D5':62, 'D#5':63, 'Eb5':63, 'E5':64, 'F5':65, 'F#5':66, 'Gb5':66, 'G5':67, 'G#5':68, 'Ab5':68, 'A5':69, 'A#5':70, 'Bb5':70, 'B5':71,
            'C6':72, 'C#6':73, 'Db6':73, 'D6':74, 'D#6':75, 'Eb6':75, 'E6':76, 'F6':77, 'F#6':78, 'Gb6':78, 'G6':79, 'G#6':80, 'Ab6':80, 'A6':81, 'A#6':82, 'Bb6':82, 'B6':83,
            'C7':84, 'C#7':85, 'Db7':85, 'D7':86, 'D#7':87, 'Eb7':87, 'E7':88, 'F7':89, 'F#7':90, 'Gb7':90, 'G7':91, 'G#7':92, 'Ab7':92, 'A7':93, 'A#7':94, 'Bb7':94, 'B7':95, 
            'C8':96 } # For simplicity omit double flats and double sharps and other redundant enharmonic note names e.g. Abb, C##, Cb, B#, Fb, E#

# Not currently used.  May want to use float instead of integer
#FREQS = {                                'C0':16,  'C#0':17,  'D0':18,  'D#0':19,  'E0':21,  'F0':22,  'F#0':23,  'G0':24,  'G#0':26,
#          'A0':28,  'A#0':29,  'B0':31,  'C1':33,  'C#1':35,  'D1':37,  'D#1':39,  'E1':41,  'F1':44,  'F#1':46,  'G1':49,  'G#1':52,
#          'A1':55,  'A#1':58,  'B1':62,  'C2':65,  'C#2':69,  'D2':73,  'D#2':78,  'E2':82,  'F2':87,  'F#2':92,  'G2':98,  'G#2':104,
#          'A2':110, 'A#2':117, 'B2':123, 'C3':131, 'C#3':139, 'D3':147, 'D#3':156, 'E3':165, 'F3':175, 'F#3':185, 'G3':196, 'G#3':208,
#          'A3':220, 'A#3':233, 'B3':247, 'C4':262, 'C#4':277, 'D4':294, 'D#4':311, 'E4':330, 'F4':349, 'F#4':370, 'G4':392, 'G#4':415, 'A4':440 }

class Note(object):
    '''Model a musical note played on a stringed instrument.'''
    
    def __init__(self, index):
        '''The index identifies the note value, the name is looked up using the TONES dictionary.'''
        self._indexLen = len(TONES)            # calculate once and store for efficiency
        self._index = index
        self._name = TONES[index % self._indexLen]  # Go ahead and calculate once now, even though the client may not every use this value
        
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
        
    def getPianoIndex(self):
        return self.index - 8                  # The lowest piano key is 'A0', INDICES['A0'] = 9, thus subtract 8 from our index to yield the 1 based piano index
        
    def getOctv(self):
        return int(self.index / self._indexLen)     # Essentially the same as the piano octave number
