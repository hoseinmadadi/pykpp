import re
import sys

def counteri():
    i = 0
    while True:
        i += 1
        if i == 133:
            i+=1
        yield i
counter = counteri()

scinot = r'[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?'
change_ord = re.compile(r'^(?P<type>[AD])\s+(?P<ORD>\d+)', re.M)
geos_spec_pattern = r'^(?P<active>[AD])\s+(?P<ORD>\d+)\s+(?P<AR0>' + scinot + r')\s+(?P<BR0>' + scinot + r')\s+(?P<CR0>' + scinot + r') [012] (?P<type>[ A-Z])\s+(?P<FC>' + scinot + r')\s+(?P<FCT1>' + scinot + r')\.\s+(?P<FCT2>' + scinot + r')\.\s+(\n\s+(?P<AR1>' + scinot + r')\s+(?P<BR1>' + scinot + r')\s+(?P<CR1>' + scinot + r')\s+0( [A-Z])?\s+0\.00\s+0\.\s+0\.\s+(\n\s+(?P<AR2>' + scinot + r')\s+(?P<BR2>' + scinot + r')\s+(?P<CR2>' + scinot + r')\s+0( [A-Z])?\s+0\.00\s+0\.\s+0\.\s+)?)?(?=\n )'
geos_spec = re.compile(geos_spec_pattern, re.M)
M_RCT = re.compile(' (\+ )?M =')
geos_e_pattern = r'(?<=: )(?P<static>(?P<prate>GEOS_P\(%(scinot)s, %(scinot)s, %(scinot)s, %(scinot)s, %(scinot)s, %(scinot)s, %(scinot)s, %(scinot)s, %(scinot)s\));\n)(?P<key>{\s*(-)?\d+}) (?P<rate>GEOS_E\(%(scinot)s, %(scinot)s, %(scinot)s, )lastrate\)\n\s+(?P<rxn>[^\n]+)\n' % globals()
geos_e_reorder = re.compile(geos_e_pattern, re.M)
rxn_continued = re.compile(r'\n(?=[+=])', re.M)
superfluous = re.compile(r'\+[ ]*([\n+=])', re.M)
geos_std_reorder_pattern = r'(?P<key>{\s*(-)?\d+})[ ]+(?P<rate>(0\.00E\+00|GEOS_[A-Z]{1,3}\((' + scinot + ', ){2,11}' + scinot + '\)))[ ]*\n\s+(?P<rxn>[^\n]+)\n'
geos_std_reorder = re.compile(geos_std_reorder_pattern, re.M)
geos_std_rate = re.compile(r'(?P<first>GEOS_STD\(' + scinot + ', ' + scinot + ', )(?P<CR>' + scinot + ')\)')
clean_up_trail = re.compile(r'([^{} \d\n]\S{1,8})[ ]{2,100}(?=\S)')
clean_up_head = re.compile(r'\+\s+')
stoic_sep = re.compile(r'(?<=[=+])(?P<stoic>' + scinot + r')(?=[^,\d )])')
plus_sep = re.compile(r'(\D[A-Z1-9]{1,8})[ ]+(?P<sign>[+-=])(?=\d)')
dry_dep = re.compile(r'[^\n]+\n[^\n]+\n=[^\n]+DRYDEP[^\n]+\n[^\n]+\n[^\n]+\n[^\n]+\n', re.M)
emission = re.compile(r'^A[^\n]+\n\s+EMISSION\s+\+\s+\n[^\n]+\n[^\n]+\n[^\n]+\n[^\n]+\n', re.M)
kinetic_prelude = re.compile(r'\*[\n\s\S]+#=============================================================================\n# Kinetic reactions\n#=============================================================================\n\nBEGIN\n', re.M)
phot_prelude = re.compile(r'  9999 0\.00E-00 0\.0 0 0     0\.00 0\.     0\.     \n      END KINETIC\n                    \n\n#=============================================================================\n# Photolysis reactions\n#=============================================================================\n\nBEGIN\n', re.M)
postlude = re.compile(r'  9999 0\.00E-00 0\.0 0 0     0\.00 0\.     0\.      \n      END PHOTOLYSIS\n', re.M)
newscino2 = re.compile(r'(?<=\.\d{2})E')
newscino1 = re.compile(r'(?<=\.\d{1})E')
comment_spc_and_tail = re.compile(r'(\d.\d\d\d \b(O2|H2O|M|H2|CO2|H2O)\b [+{])')
comment_spc_and_head = re.compile(r'([+}] \d.\d\d\d \b(O2|H2O|M|H2|CO2|H2O)\b)')
double_comment_in = re.compile(r'{}')
double_comment_out = re.compile(r'} {')

def subrxn(matcho):
    found = {}
    found.update(matcho.groupdict())
        
    typ = found['type']
    for k, v in found.iteritems():
        if k[:1] in 'ABCF' and v is not None:
            found[k] = float(v)
        if k == 'ORD':
            found[k] = int(v)

    if found['active'] == 'D':
        typ = found['type'] = 'D'
        
            
    template = {' ': '{%(ORD)4d} GEOS_STD(%(AR0).6e, %(BR0).6e, %(CR0).6e)',
     'Y': '{%(ORD)4d} GEOS_%(type)s(%(AR0).6e, %(BR0).6e, %(CR0).6e)',
     'C': '{%(ORD)4d} GEOS_%(type)s(%(AR0).6e, %(BR0).6e, %(CR0).6e)',
     'K': '{%(ORD)4d} GEOS_%(type)s(%(AR0).6e, %(BR0).6e, %(CR0).6e)',
     'T': '{%(ORD)4d} GEOS_%(type)s(%(AR0).6e, %(BR0).6e, %(CR0).6e)',
     'Q': '{%(ORD)4d} GEOS_%(type)s(TUV_J(?, THETA))',
     'P': '{%(ORD)4d} GEOS_%(type)s(%(AR0).6e, %(BR0).6e, %(CR0).6e, %(AR1).6e, %(BR1).6e, %(CR1).6e, %(FC).6e, %(FCT1).6e, %(FCT2).6e)',
     'E': '{%(ORD)4d} GEOS_%(type)s(%(AR0).6e, %(BR0).6e, %(CR0).6e, lastrate)',
     'V': '{%(ORD)4d} GEOS_%(type)s(%(AR0).6e, %(BR0).6e, %(CR0).6e, %(AR1).6e, %(BR1).6e, %(CR1).6e)',
     'A': '{%(ORD)4d} GEOS_%(type)s(%(AR0).6e, %(BR0).6e, %(CR0).6e, %(AR1).6e, %(BR1).6e, %(CR1).6e)',
     'B': '{%(ORD)4d} GEOS_%(type)s(%(AR0).6e, %(BR0).6e, %(CR0).6e, %(AR1).6e, %(BR1).6e, %(CR1).6e)',
     'G': '{%(ORD)4d} GEOS_%(type)s(%(AR0).6e, %(BR0).6e, %(CR0).6e, %(AR1).6e, %(BR1).6e, %(CR1).6e)',
     'Z': '{%(ORD)4d} GEOS_%(type)s(%(AR0).6e, %(BR0).6e, %(CR0).6e, %(AR1).6e, %(BR1).6e, %(CR1).6e, 1.400000e-21, 0.000000e+00, 2.200000e+02)',
     'X': '{%(ORD)4d} GEOS_%(type)s(%(AR0).6e, %(BR0).6e, %(CR0).6e, %(AR1).6e, %(BR1).6e, %(CR1).6e, %(AR2).6e, %(BR2).6e, %(CR2).6e)',
     'D': '{%(ORD)4d} 0.00E+00',
     }[typ]
     
    return template % found

def print_usage():
    print """

  Usage: %s inputpath

    Converts GEOS-Chem formatted reactions to KPP formatted
    reactions. Output is sent to stdout. Photolysis reactions
    must be updated manually after the conversion.
    
    Example:
      %s globchem.dat > geoschem.kpp
    
    """ % (sys.argv[0], sys.argv[0])
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print_usage()
        exit()
    try:
        kpp_text = file(sys.argv[1], 'r').read()
        kpp_text = emission.sub(r'', kpp_text)
        kpp_text = dry_dep.sub(r'', kpp_text)
        kpp_text = change_ord.sub(lambda match: '%s %d' % (match.groupdict()['type'], counter.next()), kpp_text)
        kpp_text = rxn_continued.sub('', kpp_text)
        kpp_text = superfluous.sub(r'\1', kpp_text)
        kpp_text = superfluous.sub(r'\1', kpp_text)
        kpp_text = superfluous.sub(r'\1', kpp_text)
        kpp_text = superfluous.sub(r'\1', kpp_text)
        kpp_text = superfluous.sub(r'\1', kpp_text)
        kpp_text = superfluous.sub(r'\1', kpp_text)
        kpp_text = superfluous.sub(r'\1', kpp_text)
        kpp_text = superfluous.sub(r'\1', kpp_text)
        kpp_text = superfluous.sub(r'\1', kpp_text)
        kpp_text = superfluous.sub(r'\1', kpp_text)
        kpp_text = geos_spec.sub(subrxn, kpp_text)
        kpp_text = geos_std_reorder.sub(r'\g<key>  \g<rxn> : \g<rate>;\n', kpp_text)
        kpp_text = geos_e_reorder.sub(r'\g<static>\g<key>  \g<rxn>: \g<rate>\g<prate>);\n', kpp_text)
        kpp_text = clean_up_trail.sub(r'\1 ', kpp_text)
        kpp_text = clean_up_head.sub(r'+ ', kpp_text)
        kpp_text = stoic_sep.sub(r'\g<stoic> ', kpp_text)
        kpp_text = plus_sep.sub(r'\1 \g<sign> ', kpp_text)
        kpp_text = kinetic_prelude.sub(r'', kpp_text)
        kpp_text = phot_prelude.sub(r'', kpp_text)
        kpp_text = postlude.sub(r'', kpp_text)
        kpp_text = comment_spc_and_head.sub(r'{\1}', kpp_text)
        kpp_text = comment_spc_and_tail.sub(r'{\1}', kpp_text)
        kpp_text = double_comment_in.sub(r'', kpp_text)
        kpp_text = double_comment_out.sub(r' ', kpp_text)
        kpp_text = M_RCT.sub(r' =', kpp_text)
        kpp_text = '#EQUATIONS\n'+kpp_text
        print kpp_text
    except Exception, e:
        print e
        print
        print_usage()