import hou
import re

# get gas upres node, create a null and copy+rename all parms and expressions
# add "_GU" to all
gu = hou.node('/obj/geo2/lowres1_upres/dopnet1/pyro_solver/solver/gasupres1')
pos = gu.position()
gu_copy = gu.parent().createNode("null")
gu_copy.setPosition((pos[0],pos[1]-1))

gu_template = gu.parmTemplateGroup()
gu_copy.setParmTemplateGroup(gu_template)

strCode = gu_copy.asCode(True,True)

new_lines = []
tokens = ['parm','ParmTemplate']

for line in strCode.split("\n"):
    for token in tokens:
        t = token+'("'
        if t in line:
            l = line.split('("')[1].split('"')[0]
            if not l.startswith("/") and not l.startswith("$"):
                if len(line)>1:
                    line = re.sub(l,l+"_GU",line,1)

    # deal with disable/hide when expressions
    if '"{' in line:
        l = line.split("{")
        l.pop(0)
        names = []
        for j in l:
            name =  (j.split("}")[0]).split()[0]
            names.append(name)

        # remove duplicates    
        names = list(set(names))
        for name in names:
            line = re.sub(name,name+"_GU",line)

    new_lines.append(line)

new_asCode = "\n".join(new_lines)

# write to disk for debug purpose
# with open("/tmp/temp","w") as f:
#     f.write(code)

gu_copy.destroy()
exec(new_asCode)

