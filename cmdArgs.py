'''cmdArgs.py module.  class list: [].'''

import sys
import os.path

def parseCmdLine(options):
    if options is None: raise Exception('Error! cmdArgs.parseCmdLine() options arg is required - raising Exception!')
    dbg = None
    argc = len(sys.argv)
    if dbg: print(this, "argc = %s, arv = %s" % (argc, sys.argv))
    idx = 1
    key = ''
    vals = []
    while idx < argc:
        argv = sys.argv[idx]
        if len(argv) > 2 and argv[0] == '-' and argv[1] == '-':
            if argv[2].isalpha():
                vals = []
                key = argv[2:]
                options[key] = vals
                if dbg: print(this, "[%d] long [%s] [%s] [%s]: " % (idx, argv, key, vals), end='')
            else:
                print(this, "[%d] ERROR long [%s] [%s] [%s]: " % (idx, argv, key, vals), end='')
        elif len(argv) > 1 and argv[0] == '-':
            if argv[1].isalpha():
                vals = []
                if len(argv) == 2:
                    key = argv[1:]
                    if dbg: print(this, "[%d] short [%s] [%s] [%s]: " % (idx, argv, key, vals), end='')
                    options[key] = vals
                elif len(argv) > 2:
                    for i in range(1, len(argv)):
                        key = argv[i]
                        if dbg: print(this, "[%d] short [%s] [%s] [%s]: " % (idx, argv, key, vals), end='')
                        options[key] = vals
            elif argv[1].isdigit():
                vals.append(argv)
                options[key] = vals
                if dbg: print(this, "[%d] neg arg [%s] [%s] [%s]: " % (idx, argv, key, vals), end='')
            else:
                vals.append(argv)
                options[key] = vals
                if dbg: print(this, "[%d] ??? arg [%s] [%s] [%s]: " % (idx, argv, key, vals), end='')
        else:
            vals.append(argv)
            options[key] = vals
            if dbg: print(this, "[%d] arg [%s] [%s] [%s]: " % (idx, argv, key, vals), end='')
        idx += 1
        if dbg: print()
    if dbg:
        print('{} options={}'.format(this, options))
        print('exiting dbg cmdArgs')
        exit(0)

this = os.path.basename(sys.argv[0]) + ': ' + 'cmdArgs:'

#options = {}
#parse_cmd_line(options)
#print("options:", options)
#print("sorted:")
#for key in sorted(options):
#    print("    ", key, options[key])
