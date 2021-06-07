##!/usr/bin/env python3

import hou

# Houdini Sparse Pyro Upres prototype
#
def copyParmsFolders(sourceNode,destinationNode,parmFolders):
    # sourceNode(node),destinationNode(node),parmFolders(list)
    # create a list of folders from sourceNode and parmFolders
    sourceTemplateGroup = sourceNode.parmTemplateGroup()
    sourceNodeFolders=[]
    for parmFolder in parmFolders:
        folder = sourceTemplateGroup.findFolder(parmFolder)
        sourceNodeFolders.append(folder)

    destinationNodeTemplateGroup = destinationNode.parmTemplateGroup()
    # add folders to destinationNode
    for folder in sourceNodeFolders:
        destinationNodeTemplateGroup.append(folder)
    destinationNode.setParmTemplateGroup(destinationNodeTemplateGroup)

    ramps=[]
    for i in parmFolders:
        j = destinationNode.parmsInFolder((i,))
        for k in j:
            sourceParm = sourceNode.parm(k.name())
            if sourceParm.parmTemplate().type() == hou.parmTemplateType.Ramp:
                r = [k,sourceParm]
                ramps.append(r)
            else:
                #ramps.append(r) # TO FIX!!!
                sourceParm.set(k)

    if len(ramps)>0:
        n = ramps[0][0].node()
        ptg = n.parmTemplateGroup()

        for i in ramps:
            source_ramp = i[0]
            dest_ramp = i[1]
            source_ramp_template = ptg.find(source_ramp.name())
            dest_ramp_relpath = source_ramp.node().relativePathTo(dest_ramp.node())+"/"+dest_ramp.name()
            callbackScript = 'dest_ramp=hou.parm("'+dest_ramp_relpath+'");source_ramp=hou.pwd().evalParm("'+source_ramp.name()+'"); dest_ramp.set(source_ramp)'
            tags = {}
            tags["script_callback_language"]="python"
            tags['script_callback']=callbackScript
            source_ramp_template.setTags(tags)
            ptg.replace(source_ramp.name(),source_ramp_template)

        n.setParmTemplateGroup(ptg)

def deleteAllUpresNodes():
    for i in hou.nodeType("Sop/pyrosolver").instances():
        if i.name().endswith("upres"):
            i.destroy()

def getSopPyroSolver():
    # if only one sparse_pyro node, return it, else use node selection
    sparsePyro=''
    sparsePyroNodes=hou.nodeType("Sop/pyrosolver").instances()
    if len(sparsePyroNodes)==1:
        sparsePyro=sparsePyroNodes[0]
    else:
        selectedNodes = hou.selectedNodes()
        for i in selectedNodes:
          if i.type().name()=='pyrosolver':
            sparsePyro=i
    if sparsePyro=='':
        hou.ui.displayMessage("Select the Sparse Pyro node to upres (Dops)",buttons=("OK",))
    else:
        pos = sparsePyro.position()
        n = sparsePyro.name()
        a = hou.copyNodesTo((sparsePyro,),sparsePyro.parent())
        a[0].setPosition((pos[0]+4,pos[1]))
        a[0].setName(n+"_upres")
        sparsePyro=a[0]
    return sparsePyro

def bypassNodes(sparsePyro):
    bypassesNodesStr='MOTION_OPERATORS#DISTURBANCE#FORCES#SHREDDING#TURBULENCE#add_turbulence#disturb_vel#shred_vel#temp_diffusion#TEMPERATURE#temp_cooling#scaled_external#absolute_external#FORCES_2#buoyancy#viscosity#project#reset_collision#reset_collisionvel#build_collision_mask#IOP#collision_velocities#collision_feedback#reset#COLLISION_MASK#CORRECT_IN_COLLISIONS#PRESSURE_PROJECTION#hourglass_filter#HOURGLASS#VISUALIZE_HF#create_temp_div#hg_f_vis#reset_temp_div#CLEANUP#reset_divergence#VELOCITY_ADVECTION#ADVECTION_REFLECTION_DOUBLE#advect_vel#create_temp_vel2#copy_preproj#ADVECTION_REFLECTION_SINGLE#reflect#advect_temp_vel#copy_to_vel#do_reflect#advect_vel_normal#update_pass#clear_temp_vel#SAVE_PREPROJ#minimal_solve_2#ADVECTION_REFLECTION#minimal_solve_3#minimal_solve_4_FORCES#minimal_solve_5#minimal_solve_6#minimal_solve_7#minimal_solve_8#PP_NORMAL#project_minimal#match_speed#calculate_speed#minimal_solve_10#enable_speed#'
    bypassesNodes=bypassesNodesStr.split("#")
    solver = sparsePyro.node("solver")
    for i in sparsePyro.children():
        if i.name() in bypassesNodes:
            i.bypass(1)
    for i in solver.children():
        if i.name() in bypassesNodes:
            i.bypass(1)

# create upres node and unlock
def createUpresNode(sparsePyro):
    upresNode = sparsePyro.parent().createNode("gasupres::2.0")
    upresNode.allowEditingOfContents()
    return upresNode

def cleanupUpresSolver(upresNode):
    # disable fuel,set borders to constant,set temperature,density to scalar
    upresNode.parm("enablesolver3/enable").deleteAllKeyframes()
    n = ['lowrestemperature','lowresdensity','lowresvel']
    for i in n: upresNode.node(i).parm("border").set(0)
    n.pop()
    for i in n: upresNode.node(i).parm("rank").set(0)
    # fix lowres density import path, disable rest regen, set lowres timescale=1

def renameDuplicateParms(upresNode,sparsePyroNode,sopPyroSolver):
    # add sparsePyro and sopPyro parms in list
    usedParmNames=[]
    for i in sparsePyroNode.parmTemplateGroup().entriesWithoutFolders():
        usedParmNames.append(i.name())
    for i in sopPyroSolver.parmTemplateGroup().entriesWithoutFolders():
        usedParmNames.append(i.name())
    usedParmNames = list(set(usedParmNames))

    # rename upres parm if in sparse
    upresGroup = upresNode.parmTemplateGroup()
    upresEntries=upresGroup.entriesWithoutFolders()
    for i in upresEntries:
        n = i.name()
        if n in usedParmNames:
            parmTemplate = upresGroup.find(n)
            parmTemplate.setName(n+"_")
            upresGroup.replace(n,parmTemplate)
    # update upres template group
    upresNode.setParmTemplateGroup(upresGroup)

def copyParmFolders(upresNode,sparsePyro):
    upresGroup = upresNode.parmTemplateGroup()
    # copy upres folders to sparse
    l = ['Simulation','Shape','Advanced']
    upresFolders=[]
    for i in l:
        folder = upresGroup.findFolder(i)
        folder.setLabel("Upres "+i)
        upresFolders.append(folder)
    sparseGroup = sparsePyro.parmTemplateGroup()
    # add folders to sparse
    for i in upresFolders:
        sparseGroup.append(i)
    sparsePyro.setParmTemplateGroup(sparseGroup)

def copyUpresNodes(upresNode,sparsePyro):
    merge1 = sparsePyro.node("merge1")
    rootNodes=["SOURCE__LOW_RES_FIELDS","compute_turb","ramp_turbscale","do_rest_autoregen3","primary_noise"]

    for i in rootNodes:
        networkBox=upresNode.node(i).parentNetworkBox()
        for j in networkBox.nodes():
            j.setColor(hou.Color(1,0,0))
            pos = j.position()
            j.setPosition((pos[0]-20,pos[1]+50))
        hou.copyNodesTo(networkBox.nodes(),sparsePyro)

    for i in rootNodes:
        rootnode = sparsePyro.node(i)
        merge1.setNextInput(rootnode)

def upresUIcleanup(sopPyroSolver):
    sopPyroSolver.setParms({"autoregenrest":0,"lowressoppath":"`opinputpath('.',1)`","import_low_res_time":0})

deleteAllUpresNodes()
sopPyroSolver=getSopPyroSolver()
sopPyroSolver.allowEditingOfContents()
sparsePyro = sopPyroSolver.node("dopnet1/pyro_solver")
solver = sparsePyro.node("solver")
sparsePyro.allowEditingOfContents()
solver.allowEditingOfContents()
bypassNodes(sparsePyro)
upresNode = createUpresNode(sparsePyro)
cleanupUpresSolver(upresNode)
renameDuplicateParms(upresNode,sparsePyro,sopPyroSolver)
copyParmFolders(upresNode,sparsePyro)
copyUpresNodes(upresNode,sparsePyro)
parmFolders = ('Upres Simulation','Upres Shape','Upres Advanced')
copyParmsFolders(sparsePyro,sopPyroSolver,parmFolders)
upresUIcleanup(sopPyroSolver)



