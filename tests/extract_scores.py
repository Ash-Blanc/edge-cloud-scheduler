import glob,re
for f in glob.glob('*.cpp'):
    s=open(f,encoding='utf-8',errors='ignore').read()
    vals=[float(x) for x in re.findall(r'normalized_score=([0-9.]+)',s)]
    if len(vals)>=20:
        print(f, len(vals), sum(vals)*1000)
