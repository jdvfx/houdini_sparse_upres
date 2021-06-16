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
                #ramps.append(r) # TO FIX!!! wtf is that doing here?
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
    for i in hou.nodeType("Sop/dopnet").instances():
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


###############################################################################
###############################################################################
###############################################################################


def get_pyro_nodes():

    global __sop_node__
    global __sop_pyro_solver__

    # auto-detect: search for DOP pyrosolver nodes
    pyrosolver_instances = hou.nodeType("Dop/pyrosolver_sparse").instances()

    if len(pyrosolver_instances)>1:

        # # multiple pyrosolver nodes detected, use manual selection
        selected_nodes = hou.selectedNodes()
        if len(selected_nodes) > 0:

            node = selected_nodes[0]
            node_type = node.type().name()

            if node_type == 'pyrosolver':
                __sop_node__ = node
                __sop_pyro_solver__ = node

            if node_type == 'dopnet':
                for child in node.children():
                    if child.type().name() == "pyrosolver_sparse":
                        __sop_node__ = node
                        break

        # no node selected or no pyrosolver found in selection
        if __sop_node__=='':
            hou.ui.displayMessage("ERROR: \nselect SOP pyrosolver node\nor SOP dopnet containing pyrosolver", buttons=("OK",))

    else:

        # only one instance of pyrosolver_sparse node found
        # search for SOP pyrosolver node
        sop_pyro = hou.nodeType("Sop/pyrosolver").instances()

        if len(sop_pyro)>0:
            print("SOP pyrosolver detected")
            __sop_node__ = sop_pyro[0]
            __sop_pyro_solver__ = sop_pyro[0]
        else:
            print("DOP pyrosolver detected")
            for child in sop_pyro[0].children():
                if child.type().name() == "pyrosolver_sparse":
                    __sop_node__ = child
                    break


def create_sop_upres_node(sop_node):

    global __upres_sop_node__
    global __pyro_solver__

    # duplicate SOP node, rename, offset position, change color
    nodescopy = hou.copyNodesTo((sop_node,), sop_node.parent())
    upres_sop_node = nodescopy[0]

    pos = sop_node.position()
    upres_sop_node.setPosition((pos[0]+4, pos[1]))
    upres_sop_node.setName(sop_node.name()+"_upres")

    unlock(upres_sop_node)

    __upres_sop_node__ = upres_sop_node

    # get pyrosolver (if no sop_pyro, then it's DOP)
    if __sop_pyro_solver__ == '':
        solverpath = 'pyrosolver_sparse1'
    else:
        solverpath = 'dopnet1/pyro_solver'

    __pyro_solver__ = upres_sop_node.node(solverpath)

def bypassNodes(sparsePyro):
    # list of nodes to bypass (created from selection)
    bypassedNodes = [
        'MOTION_OPERATORS', 'DISTURBANCE', 'FORCES', 'SHREDDING', 'TURBULENCE',
        'add_turbulence', 'disturb_vel', 'shred_vel', 'temp_diffusion',
        'TEMPERATURE', 'temp_cooling', 'scaled_external', 'absolute_external',
        'FORCES_2', 'buoyancy', 'viscosity', 'project', 'reset_collision',
        'reset_collisionvel', 'build_collision_mask', 'IOP', 'reset',
        'collision_velocities', 'collision_feedback', 'COLLISION_MASK',
        'CORRECT_IN_COLLISIONS', 'PRESSURE_PROJECTION', 'hourglass_filter',
        'HOURGLASS', 'VISUALIZE_HF', 'create_temp_div', 'hg_f_vis',
        'reset_temp_div', 'CLEANUP', 'reset_divergence', 'VELOCITY_ADVECTION',
        'ADVECTION_REFLECTION_DOUBLE', 'advect_vel', 'create_temp_vel2',
        'copy_preproj', 'ADVECTION_REFLECTION_SINGLE', 'reflect',
        'advect_temp_vel', 'copy_to_vel', 'do_reflect', 'advect_vel_normal',
        'update_pass', 'clear_temp_vel', 'SAVE_PREPROJ', 'minimal_solve_2',
        'ADVECTION_REFLECTION', 'minimal_solve_3', 'minimal_solve_4_FORCES',
        'minimal_solve_5', 'minimal_solve_6', 'minimal_solve_7',
        'minimal_solve_8', 'PP_NORMAL', 'project_minimal', 'match_speed',
        'calculate_speed', 'minimal_solve_10', 'enable_speed'
    ]
    solver = sparsePyro.node("solver")
    for i in sparsePyro.children():
        if i.name() in bypassedNodes:
            i.bypass(1)
    for i in solver.children():
        if i.name() in bypassedNodes:
            i.bypass(1)

# allow editing of content and set color
def unlock(node):
    node.allowEditingOfContents()
    node.setColor(hou.Color((1,0,0)))


# create upres node and unlock
def createGasUpres():

    global __gas_upres__

    gas_upres = __pyro_solver__.parent().createNode("gasupres::2.0")
    unlock(gas_upres)
    __gas_upres__ = gas_upres

def cleanupGasupresSolver(gasupres):

    # fixing some gasUpres default config issues
    #

    # disable lowres fuel
    gasupres.parm("enablesolver3/enable").deleteAllKeyframes()
    # set borders to constant (no interpolation)
    n = ['lowrestemperature','lowresdensity','lowresvel']
    for i in n: gasupres.node(i).parm("border").set(0)
    # remove lowresvel from list and set type to "scalar"
    n.pop()
    for i in n: gasupres.node(i).parm("rank").set(0)
    # fix lowresdensity's data name
    gasupres.parm("add_lowresdensity/datapath").set("lowresdensity")
    # disable rest regen
    gasupres.parm("autoregenrest").set(0)
    # set timescale to 1
    gasupres.parm("import_low_res_time").set(0)



    # set lowres path to be the second input of the solver
    #gasupres.parm("lowressoppath").set("`opinputpath('.',1)`")

# -----------------------------------------------------------------------------

__upres_sop_node__ = ''
__sop_pyro_solver__ = ''
__dopnet__ = ''
__pyro_solver__ = ''
__upres_ui_node__ = ''
__sop_node__ = ''
__gas_upres__ = ''

def main():

    # delete previous upres nodes (for dev/testing)
    deleteAllUpresNodes()

    # auto detect pyrosolver node or use selection if multiple found
    get_pyro_nodes()

    # no pyro node found > exit
    if __sop_node__ =='': return

    # duplicate SOP network (upres)
    create_sop_upres_node(__sop_node__)

    # unlock pyro and solver nodes
    unlock(__pyro_solver__)
    unlock(__pyro_solver__.node("solver"))

    # disable nodes not needed for upres
    bypassNodes(__pyro_solver__)

    # create gasUpres Solver node and fix some issues
    createGasUpres()
    cleanupGasupresSolver(__gas_upres__)

if __name__ == "__main__":
    main()

# --------------------------------------------------------------------------

# case 1 (SOP)
# SOP pyrosolver >>> "sopPyroSolver" !upresUI! !SOP_node!
# + dopnet >>> "dopnet"
#   + pyro_solver [pyro solver (sparse)] >>> pyroSolver
#     + solver [smoke solver (sparse)] >>> smokeSolver --- implied from pyro_solver

# case 2 (DOP)
# dopnet (in SOPs) !SOP_node!
#   + pyro_solver [pyro solver (sparse)] !upresUI!
#     + solver [smoke solver (sparse)] >>> smokeSolver --- implied from pyro_solver

# --------------------------------------------------------------------------

# sopPyroSolver.allowEditingOfContents()
# sparsePyro = sopPyroSolver.node("dopnet1/pyro_solver")
# solver = sparsePyro.node("solver")
# sparsePyro.allowEditingOfContents()
# solver.allowEditingOfContents()
# bypassNodes(sparsePyro)
# upresNode = createUpresNode(sparsePyro)
# cleanupUpresSolver(upresNode)
# renameDuplicateParms(upresNode,sparsePyro,sopPyroSolver)
# copyParmFolders(upresNode,sparsePyro)
# copyUpresNodes(upresNode,sparsePyro)
# parmFolders = ('Upres Simulation','Upres Shape','Upres Advanced')
# copyParmsFolders(sparsePyro,sopPyroSolver,parmFolders)
# upresUIcleanup(sopPyroSolver)


# --------------------------------------------------------------------------
# TO DO:
# - PEP8/utf8 (check python3 header)
# - get SOP_Pyro or DOP_Pyro
# - make code less monolithic
# - should work for SOP pyrosolver and DOP pyrosolver (inside SOP) - no /OBJ/DOP/pyrosolver BS!
#
# --------------------------------------------------------------------------



