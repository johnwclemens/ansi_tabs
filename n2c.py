import os, sys
import msvcrt
getwch = msvcrt.getwch
import chords

S_TONES = { 0:'C', 1:'C#', 2:'D', 3:'D#', 4:'E', 5:'F', 6:'F#', 7:'G', 8:'G#', 9:'A', 10:'A#', 11:'B' }
F_TONES = { 0:'C', 1:'Db', 2:'D', 3:'Eb', 4:'E', 5:'F', 6:'Gb', 7:'G', 8:'Ab', 9:'A', 10:'Bb', 11:'B' }

INDICES = { 'E#':5, 'Fb':4, 'B#':0, 'Cb': 11, 'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#':10, 'Bb':10, 'B':11}
INTERVALS =     { 0:'R', 1:'b2', 2:'2', 3:'m3', 4:'M3', 5:'4', 6:'b5', 7:'5', 8:'a5', 9:'6', 10:'b7', 11:'7' }
INTERVAL_RANK = { 'R':0, 'b2':1, '2':2, 'm3':3, 'M3':4, '4':5, 'b5':6, '5':7, 'a5':8, '6':9, 'b7':10, '7':11, }

class N2C(object):
    def __init__(self):
        self.chordsObj = chords.Chords(self)
    
    def run(self, dbg=0):
        print('BGN run')
        b, c, s = 0, '', []
        index, indices, intervals = -1, [], []
        print('Notes:', end='', flush=True)
        while True:
            c = getwch()
            b = ord(c)
            if b == 13: break
            if c in INDICES:
                index = INDICES[c]
                indices.append(index)
                if dbg: print('index={} indices={}'.format(index, indices))
                s += c
                print(' {}'.format(c), end='', flush=True)
            elif c == 'b' or c == '#':
                if len(s) >= 1: c = s[-1] + c
                else: continue
                index = INDICES[c]
                indices[-1] = index
                if dbg: print('index={} indices={} c={}'.format(index, indices, c))
                s[-1] = c
                print('\b{}'.format(s[-1]), end='', flush=True)
        print()
        for i in range(len(indices)):
            intervals = self.chordsObj.getIntervals(i, indices)
            imap = {}
            for j in range(len(indices)):
                imap[intervals[j]] = s[j]
            if dbg: print('i={} intervals={} notes={}'.format(i, intervals, notes))
            self.printDict(imap)
            chordName = self.chordsObj.getChordName(imap)
            print(' {}'.format(chordName))
        print('END run')
    
    def printDict(self, d, reason=''):
        print('{}{{'.format(reason), end='')
        ks = sorted(d, key=self.chordsObj.imapKeyFunc, reverse=False)
        for k in ks:
            print('{}'.format(k), end=' ')
        print(':', end=' ')
        for k in ks:
            print('{}'.format(d[k]), end=' ')
        print('}', end=' ')

def main():
    n2c = N2C()
    n2c.run()
    
if __name__ == "__main__":
    main()
