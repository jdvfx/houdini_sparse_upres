import hou
import re

# get gas upres node, create a null and copy+rename all parms and expressions
# add "_GU" to all
a = hou.node('/obj/geo2/lowres1_upres/dopnet1/pyro_solver/solver/gasupres1')
pos = a.position()
b = a.parent().createNode("null")
b.setPosition((pos[0],pos[1]-1))

g = a.parmTemplateGroup()
b.setParmTemplateGroup(g)


strCode = b.asCode(True,True)

x = []
tokens = ['parm','ParmTemplate']
#rep = []

for i in strCode.split("\n"):
    for token in tokens:
        t = token+'("'
        if t in i:
            l = i.split('("')[1].split('"')[0]
            if not l.startswith("/") and not l.startswith("$"):
                if len(i)>1:
                    i = re.sub(l,l+"_GU",i,1)

    # deal with disable/hide when expressions
    if '"{' in i:
        l = i.split("{")
        l.pop(0)
        names = []
        for j in l:
            name =  (j.split("}")[0]).split()[0]
            names.append(name)

        # remove duplicates    
        names = list(set(names))
        for name in names:
            i = re.sub(name,name+"_GU",i)

    x.append(i)



code = "\n".join(x)

with open("/home/bunker/Desktop/temp","w") as f:
    f.write(code)



b.destroy()
exec(code)

