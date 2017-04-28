**tabs.py**

Developed and tested on Windows 7 Professional with Service Pack 1. 

The **tabs.py** module is the entry point for the tabs application.  The tabs application is essentially an old school 
console based tabs editor.  The notation used is intentionally compact using a single character for each tab, note, and tab 
modification.  

A tab character represents the finger position or fret number being played on a particular string.  The value '-' denotes an 
unplayed or completely muted string.  The [0-9] and [a-o] characters are used to represent the tabs or frets.  The value '0' 
denotes the open string being played, the value '1' the first fret, and the value 'c' the 12'th fret.  Currently, the maximum 
tab value is 'o' representing the 24'th fret.  This is probably enough tabs/frets for most instruments, however, in the future 
this might be extended to support high order harmonic notes.

The number of strings and the string tuning is customizable and specified in the **strings.py** module.  The user is encouraged 
to modify **strings.py** to customize the string tuning spellings (and the number of strings) via the aliases dictionary.

The tabs console display consists of a number of lines, each line has a tabs section, an optional notes section, an optional 
chords section, and an optional modes and labels section.  There is also a status row after the last data row for the last 
line.  The first column of each line is used essentially as row labels.  The tabs section rows are labelled with the string 
numbers, the notes section rows are labelled with the open string note names, and the chords section rows are not labelled 
(blank).  The second column of each section is used to represent the nut and optional capo fret position [0-9],[a-o] of the 
musical instrument.  The capo fret number is displayed for each string, the value 0 indicates no capo.  The color of the capo 
fret character indicates the direction of the automatic cursor advancement, red = up, blue = down.

The tabs section is not optional and is the only user editable area in the console display.  The optional sections are 
automatically populated based on the data in the tabs sections.  

The optional notes section displays the musical note characters corresponding to the tab characters.  Sharp and flat notes are 
displayed using the color red or blue respectively, while natural notes are displayed in green.

The optional chords section displays calculated chord names for tabs within the same column and the same line that form a 
musical chord.  Note 5 rows are reserved for this section on each line regardless if any chords are discovered.  Chords are 
spelled vertically so that they line up with the tabs and notes and potentially every column can display a chord.  The chord 
calculation is attempted every time there is more than one tab in a give column on a given line.  A dictionary is used to 
registered discovered chord spellings so the subsequent identical chords can be displayed without additional calculations.  
This functionality is in the separate **chords.py** module to encourage user customization.

The optional modes and labels section is a single row before the tabs section for each line.  It consists of a single row 
containing column number labels, the edit mode, and the cursor mode.  These optional column number label rows are also used 
to highlight the current cursor horizontal position.  The row number label column similarly highlights the cursor vertical 
position.

Status info is displayed in the last row of the last line, after the optional notes section and or optional chords section.  
The status row is used to display error messages and or extra information about the tab character at the current cursor 
position.  e.g. if the cursor is on a tab character that is a fret, then extra information about the note is displayed.  
Similarly, extra info is displayed when the cursor is on a tab modification character.

e.g. The fifth fret on the first standard guitar string:
```
A4, index=57, frequency=440.00 Hz, wavelength=2.56 inches
```
e.g. A tab modification, slide up, between the second and 4th frets 2/4:
```
/ slide up from 2 to 4
```

Tab modifications are optional characters that are appended to a tab character or inserted in between successive tab 
characters denoting a specific playing technique that modifies the note tone (e.g. vibrato, string bending, sliding etc...) 
of the previous tab or the transition from the previous tab to the next tab.

Tab modifications are handled in the **mods.py** module.  The user is encouraged to edit **mods.py** to customize the tab mods 
dictionary key -> value mapping.  The tab mod keys are the characters that are displayed in the tabs and optional notes 
sections.  The tab mod dictionary values are displayed, in the status row, with optional contextual data when the cursor is 
on one of the dictionary keys.

Navigation in the tabs section is via the left, right, up, and down arrow keys, the page up key, the page down key, the home 
key, and the end key.  Also, the cursor automatically advances (right, up, down, right and up, or, right and down) after a 
valid tab character is entered.  The space key also advances the cursor in the current direction as if a valid tab character 
was entered, but without changing the tab character at that position.  The navigation keys should wrap back to the same line 
if there is only one line, or jump to the next or previous line or wrap to the first or last line if there is more than one 
line.

The automatic cursor advance direction is controlled by the current cursor mode.  Melody mode advances the cursor to the 
right.  Chord mode advances the cursor up or down depending on the current cursor direction.  Arpeggio mode advances the 
cursor to the right and up or down depending on the current cursor direction.  Also both the Chord mode and arpeggio modes 
automatically advance the cursor to the right and wrap the cursor vertically to the bottom or top of the current line when 
they reach the top or bottom of the current line.

See the help page in the **tabs.py** application for documentation on all the command line arguments and user interactive 
commands.  Use the '-h' command line option or the 'Shift + H' user interactive command to display the help page.
