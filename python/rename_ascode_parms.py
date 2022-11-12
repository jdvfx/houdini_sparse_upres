import re

# rename parms from hou.asCode()
# check line for tokens and rename string
# eg: parm("color") -> parm("color_GU")

tokens = ["parmTuple","parm"]
with open("hou_ascode","r") as f:

    l = f.readlines()
    for i in l:
        line = i.split("\n")[0]
        for token in tokens:
            s = token+'("'
            if s in line:
                name = line.split(s)[1].split('"')[0]
                l = re.sub(name,name+"_GU",line,1)
                print(l)



