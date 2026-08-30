import difflib,sys
a=[x.lstrip() for x in open(sys.argv[1]).read().splitlines()]; b=[x.lstrip() for x in open(sys.argv[2]).read().splitlines()]
print('lens',len(a),len(b))
print('\n'.join(list(difflib.unified_diff(a,b,fromfile=sys.argv[1],tofile=sys.argv[2],n=1))[:600]))
