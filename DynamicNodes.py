bl_info = {
    "name":        "Dynamic Nodes",
    "description": "Adds Physics(Links Elasticity and Collisions) to Nodes",
    "author":      "Shahzod Boyxonov",
    "version":     (1, 0, 0),
    "blender":     (2, 79, 0),
    "location":    "Node Editor > Tool Shelf",
    "category":    "Node"
}

import bpy
import bgl
import blf
import math

def clamp(val,limit):
    if val>limit:  return limit
    if val<-limit: return -limit
    return val

def add(node,dim,val,min_unit):
    if abs(val)>min_unit:
        node.location[dim] += val
        
def v2r(x,y):
    return bpy.context.region.view2d.view_to_region(x,y, clip=False)
        
def DynamicNodes_DrawCallBack(self, context):
    if context.scene.DynamicNodes_Properties.arrange_mode:
        return
    bgl.glColor4f(0.6,0.6,0.7,1)
    font_id = 0
    blf.size(font_id, 12, 0)
    blf.position(font_id, 12, context.area.height - 48, 0)
    blf.enable(font_id, blf.SHADOW)
    blf.shadow(font_id, 3, 0,0,0,1)
    blf.draw(font_id, 'Dynamic Nodes')

    if self.ghost:
        bgl.glEnable(bgl.GL_BLEND)
        for node in context.selected_nodes:
            if node.parent:continue
            if hasattr(node,'shrink'):continue
            x1,y1 = v2r(node.location[0] - 10,                    node.location[1] + 10)
            x2,y2 = v2r(node.location[0]+node.dimensions[0] + 10, node.location[1]-node.dimensions[1] - 10)
            
            bgl.glColor4f(0.5,0.95,1.0, 0.1)
            bgl.glBegin(bgl.GL_QUADS)
            bgl.glVertex2i(x1,y1)
            bgl.glVertex2i(x2,y1)
            bgl.glVertex2i(x2,y2)
            bgl.glVertex2i(x1,y2)
            bgl.glEnd()
            
            bgl.glColor4f(0.0,0.4,0.7, 1)
            bgl.glBegin(bgl.GL_LINE_STRIP)
            bgl.glVertex2i(x1,y1)
            bgl.glVertex2i(x2,y1)
            bgl.glVertex2i(x2,y2)
            bgl.glVertex2i(x1,y2)
            bgl.glVertex2i(x1,y1)
            bgl.glEnd()
        bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)
    blf.disable(font_id, blf.SHADOW)
    
def DynamicNodes_Arrange_DrawCallBack(self, context):
    bgl.glColor4f(0.6,0.6,0.7,1)
    font_id = 0
    blf.size(font_id, 12, 0)
    blf.enable(font_id, blf.SHADOW)
    blf.shadow(font_id, 3, 0,0,0,1)
    props = context.scene.DynamicNodes_Properties
    
    blf.position(font_id, 12, context.area.height - 50, 0)
    blf.draw(font_id, str(min(self.iteration_cnt,                                      props.step1)) + '/' + str(props.step1))
    blf.position(font_id, 12, context.area.height - 70, 0)
    blf.draw(font_id, str(min(max(self.iteration_cnt - props.step1,0),                 props.step2)) + '/' + str(props.step2))
    blf.position(font_id, 12, context.area.height - 90, 0)
    blf.draw(font_id, str(min(max(self.iteration_cnt - props.step1 - props.step2,0),   props.step3)) + '/' + str(props.step3))
    blf.position(font_id, 12, context.area.height - 110, 0)
    blf.draw(font_id, str(    max(self.iteration_cnt - props.step1 - props.step2 - props.step3,0)  ) + '/' + str(props.step4))
    
    bgl.glBegin(bgl.GL_QUADS)
    bgl.glColor4f(0.7, 0.7, 1.0, 1.0)
    bgl.glVertex2i(8, context.area.height - 128)
    bgl.glVertex2i(52,context.area.height - 128)
    bgl.glVertex2i(52,context.area.height - 142)
    bgl.glVertex2i(8, context.area.height - 142)
    
    bgl.glColor4f(0.1, 0.1, 0.1, 1.0)
    bgl.glVertex2i(9 ,context.area.height - 129)
    bgl.glVertex2i(51,context.area.height - 129)
    bgl.glVertex2i(51,context.area.height - 141)
    bgl.glVertex2i(9 ,context.area.height - 141)
    
    progress = self.iteration_cnt/(props.step1 + props.step2 + props.step3 + props.step4)
    bgl.glColor4f(0.7, 0.7, 1.0, 1.0)
    bgl.glVertex2i(10,                    context.area.height - 130)
    bgl.glVertex2i(int(10 + progress*40), context.area.height - 130)
    bgl.glVertex2i(int(10 + progress*40), context.area.height - 140)
    bgl.glVertex2i(10,                    context.area.height - 140)
    bgl.glEnd()
    
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)
    blf.disable(font_id, blf.SHADOW)

def collide(node1,node2,shift,distance,ignore_selected):
    if node1.parent:
        return
    if hasattr(node1,'shrink'):
        return
    if hasattr(node2,'shrink'):
        return
    n2_loc = global_loc(node2)
    p1 = (node1.location[0]+node1.dimensions[0]/2,   node1.location[1]-node1.dimensions[1]/2,
                                (node1.dimensions[0]+distance)/2,     (node1.dimensions[1]+distance)/2)
    p2 = (n2_loc[0]+node2.dimensions[0]/2,   n2_loc[1]-node2.dimensions[1]/2,
                                (node2.dimensions[0]+distance)/2,     (node2.dimensions[1]+distance)/2)
                                             
    x_dis = abs(p1[0] - p2[0])
    y_dis = abs(p1[1] - p2[1])
    x_del = x_dis - (p1[2]+p2[2])
    y_del = y_dis - (p1[3]+p2[3])
    if x_del<0 and y_del<0:
        if x_del>y_del:
            if p1[0]<p2[0]:
                if not(ignore_selected and node1.select): shift[0] += x_del*0.5
            else:
                if not(ignore_selected and node1.select): shift[0] -= x_del*0.5
        else:
            if p1[1]<p2[1]:
                if not(ignore_selected and node1.select): shift[1] += y_del*0.5
            else:
                if not(ignore_selected and node1.select): shift[1] -= y_del*0.5
                
def collide_y(node1,node2,distance):
    if node1.parent:
        return 0
    if hasattr(node1,'shrink'):
        return 0
    if hasattr(node2,'shrink'):
        return 0
    n2_loc = global_loc(node2)
    p1 = (node1.location[0]+node1.dimensions[0]/2,   node1.location[1]-node1.dimensions[1]/2,
                                (node1.dimensions[0]+distance)/2,     (node1.dimensions[1]+distance)/2)
    p2 = (n2_loc[0]+node2.dimensions[0]/2,   n2_loc[1]-node2.dimensions[1]/2,
                                (node2.dimensions[0]+distance)/2,     (node2.dimensions[1]+distance)/2)
                                             
    x_dis = abs(p1[0] - p2[0])
    y_dis = abs(p1[1] - p2[1])
    x_del = x_dis - (p1[2]+p2[2])
    y_del = y_dis - (p1[3]+p2[3])
    if x_del<0 and y_del<0:
        if p1[1]<p2[1]:
            return y_del*0.5
        else:
            return -y_del*0.5
    else:
        return 0
    
def global_loc(node):
    if node.parent:
        g_loc = global_loc(node.parent)
        return (g_loc[0]+node.location[0],g_loc[1]+node.location[1])
    else:
        return node.location
    
################################################################################

class DynamicNodes(bpy.types.Operator):
    """Adds a Physics to Nodes"""
    bl_idname = "dynamic.nodes"
    bl_label = "Dynamic Nodes"

    _timer = None
    ghost  = False
    
    def calc_node(self,context,nodes,node,props):
        shift = [0,0]
        if node.select:return
        if node.parent:return
        if props.elasticLinks:
            for input in node.inputs:
                for link in input.links:
                    other_node = link.from_node
                    if other_node.select:
                        if self.ghost:
                            continue
                    other_loc = global_loc(other_node)
                    tar = (other_loc[0] + other_node.dimensions[0]+props.distance*2,
                            other_loc[1] - (other_node.dimensions[1] - node.dimensions[1])/2)
                    shift[0] += clamp((tar[0]-node.location[0])*props.elasticity,10)
                    shift[1] += clamp((tar[1]-node.location[1])*props.elasticity,10)
            for output in node.outputs:
                for link in output.links:
                    other_node = link.to_node
                    if other_node.select:
                        if self.ghost:
                            continue
                    other_loc = global_loc(other_node)
                    tar = (other_loc[0] - node.dimensions[0]-props.distance*2,
                            other_loc[1] - (other_node.dimensions[1] - node.dimensions[1])/2)
                    shift[0] += clamp((tar[0]-node.location[0])*props.elasticity,10)
                    shift[1] += clamp((tar[1]-node.location[1])*props.elasticity,10)
        
        if props.collision:
            for node2 in nodes:
                if node == node2:continue
                if node2.select:
                    if self.ghost:continue
                collide(node,node2,shift,props.distance,True)
                
        add(node,0,shift[0],props.min_unit)
        add(node,1,shift[1],props.min_unit)

    def modal(self, context, event):
        if context.scene.DynamicNodes_Properties.arrange_mode:
            return {'PASS_THROUGH'}
        if event.type == 'ESC' and context.scene.DynamicNodes_Properties.esc_stop:
            self.cancel(context)
            context.area.tag_redraw()
            return {'FINISHED'}
        
        if not context.scene.DynamicNodes_Properties.live_mode:
            self.cancel(context)
            context.area.tag_redraw()
            return {'FINISHED'}

        if event.type == 'TIMER':
            last_ghost = self.ghost
            if event.alt:     self.ghost = True
            else:             self.ghost = False
            if last_ghost is not self.ghost:
                context.area.tag_redraw() # Update on ALT button
            
            space_data = context.space_data
            if not hasattr(space_data,'node_tree'):
                return {'PASS_THROUGH'}
            if not hasattr(space_data.node_tree,'nodes'):
                return {'PASS_THROUGH'}
            nodes = space_data.node_tree.nodes
            props = context.scene.DynamicNodes_Properties
            
            if props.node_limit == 0:
                for node in nodes:
                    self.calc_node(context,nodes,node,props)
            else:
                cntr = 0
                if self.node_iterator >= len(nodes):
                    self.node_iterator = 0
                while cntr<props.node_limit and self.node_iterator<len(nodes):
                    self.calc_node(context,nodes,nodes[self.node_iterator],props)
                    self.node_iterator += 1
                    cntr += 1

        return {'PASS_THROUGH'}

    def execute(self, context):
        props = context.scene.DynamicNodes_Properties
        if props.live_mode:
            return {'CANCELLED'}
        props.live_mode = True
        self.node_iterator = 0
        wm = context.window_manager
        self._timer = wm.event_timer_add(context.scene.DynamicNodes_Properties.interval, context.window)
        wm.modal_handler_add(self)
        self._handle = bpy.types.SpaceNodeEditor.draw_handler_add(
                    DynamicNodes_DrawCallBack, (self, context), 'WINDOW', 'POST_PIXEL')
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        bpy.types.SpaceNodeEditor.draw_handler_remove(self._handle, 'WINDOW')
        context.scene.DynamicNodes_Properties.live_mode = False
        
################################################################################
        
class DynamicNodes_Arrange(bpy.types.Operator):
    """Arranges Nodes"""
    bl_label = "Dynamic Nodes Arrange"
    bl_idname = "dynamic.nodes_arrange"
    _timer = None

    def modal(self, context, event):
        props = context.scene.DynamicNodes_Properties
        if self.iteration_cnt >= props.step1+props.step2+props.step3+props.step4:
            self.cancel(context)
            return {'FINISHED'}
        if event.type == 'ESC':
            self.cancel(context)
            return {'FINISHED'}
        if not context.scene.DynamicNodes_Properties.arrange_mode:
            self.cancel(context)
            return {'FINISHED'}

        if event.type == 'TIMER':
            space_data = context.space_data
            if not hasattr(space_data,'node_tree'):
                return {'PASS_THROUGH'}
            if not hasattr(space_data.node_tree,'nodes'):
                return {'PASS_THROUGH'}
            nodes = space_data.node_tree.nodes
            has_movement = False
            ######################################  STEP 1  ###############################################
            if self.iteration_cnt < props.step1:
                for node in nodes:
                    if node.parent:continue
                    in_exists = False
                    input_max = 0
                    for input in node.inputs:
                        for link in input.links:
                            tar = global_loc(link.from_node)[0] + link.from_node.dimensions[0] + props.distance*2
                            if in_exists:
                                if input_max<tar:
                                    input_max = tar
                            else:
                                input_max = tar
                                in_exists = True
                                
                    out_exists = False
                    output_min = 0
                    for output in node.outputs:
                        for link in output.links:
                            tar = global_loc(link.to_node)[0] - node.dimensions[0] - props.distance*2
                            if out_exists:
                                if output_min>tar:
                                    output_min = tar
                            else:
                                output_min = tar
                                out_exists = True
                    shift = 0
                    if in_exists:
                        shift += (input_max-node.location[0])*0.5
                    if out_exists:
                        shift += (output_min-node.location[0])*0.5
                    node.location[0] += shift
                    if abs(shift)>props.min_unit: has_movement = True
                    
                if not has_movement: # Skip Step if There is No Movement
                    self.iteration_cnt = props.step1
            ######################################  STEP 2  ###############################################
            elif self.iteration_cnt < props.step1+props.step2:
                for node in nodes:
                    if node.parent:continue
                    input_nodes = []
                    c_shift = 0
                    for input in node.inputs:
                        for link in input.links:
                            input_nodes.append(link.from_node)
                    if len(input_nodes):
                        node_part = (node.dimensions[1]+props.distance)/len(input_nodes)
                        node_y_pos = (node.location[1] + props.distance/2) - node_part/2
                        node_cnt = 0
                        for other_node in input_nodes:
                            tar = node_y_pos - node_part * node_cnt + other_node.dimensions[1]/2
                            shift = (tar-global_loc(other_node)[1])/2
                            node.location[1] -= shift
                            c_shift += shift
                            node_cnt += 1
                            
                    output_nodes = []
                    for output in node.outputs:
                        for link in output.links:
                            output_nodes.append(link.to_node)
                    if len(output_nodes):
                        node_part = (node.dimensions[1]+props.distance)/len(output_nodes)
                        node_y_pos = (node.location[1] + props.distance/2) - node_part/2
                        node_cnt = 0
                        for other_node in output_nodes:
                            tar = node_y_pos - node_part * node_cnt + other_node.dimensions[1]/2
                            shift = (tar-global_loc(other_node)[1])/2
                            node.location[1] -= shift
                            c_shift += shift
                            node_cnt += 1
                    if abs(c_shift)>props.min_unit: has_movement = True
                            
                if not has_movement: # Skip Step if There is No Movement
                    self.iteration_cnt = props.step1+props.step2
            ##########################################  STEP 3  ########################################
            elif self.iteration_cnt < props.step1+props.step2+props.step3:
                for node in nodes:
                    shift = 0
                    for node2 in nodes:
                        if node == node2:continue
                        shift += collide_y(node,node2,props.distance)
                    shift *= 0.2
                    node.location[1]+=shift
                    if abs(shift)>props.min_unit: has_movement = True
                    
                if not has_movement: # Skip Step if There is No Movement
                    self.iteration_cnt = props.step1+props.step2+props.step3
            ##########################################  STEP 4  ########################################
            else:
                for node in nodes:
                    if node.parent:continue
                    shift = [0,0]
                    for input in node.inputs:
                        for link in input.links:
                            other_node = link.from_node
                            other_loc = global_loc(other_node)
                            tar = (other_loc[0] + other_node.dimensions[0]+props.distance*2,
                                    other_loc[1] - (other_node.dimensions[1] - node.dimensions[1])/2)
                            shift[0] += clamp((tar[0]-node.location[0])*props.elasticity,10)
                            shift[1] += clamp((tar[1]-node.location[1])*props.elasticity,10)
                    for output in node.outputs:
                        for link in output.links:
                            other_node = link.to_node
                            other_loc = global_loc(other_node)
                            tar = (other_loc[0] - node.dimensions[0]-props.distance*2,
                                    other_loc[1] - (other_node.dimensions[1] - node.dimensions[1])/2)
                            shift[0] += clamp((tar[0]-node.location[0])*props.elasticity,10)
                            shift[1] += clamp((tar[1]-node.location[1])*props.elasticity,10)
                    
                    p_shift = [0,0]
                    for node2 in nodes:
                        if node == node2:continue
                        collide(node,node2,p_shift,props.distance,False)
                            
                    c_shift = [shift[0]+p_shift[0], shift[1]+p_shift[1]]
                    node.location[0]+=c_shift[0]
                    node.location[1]+=c_shift[1]
                    if abs(c_shift[0])>props.min_unit: has_movement = True
                    if abs(c_shift[1])>props.min_unit: has_movement = True
                    
                if not has_movement: # Skip Step if There is No Movement
                    self.iteration_cnt = props.step1+props.step2+props.step3+props.step4
                    
            ####################################################################################################

        self.iteration_cnt +=1

        return {'PASS_THROUGH'}

    def execute(self, context):
        if context.scene.DynamicNodes_Properties.arrange_mode:
            return {'CANCELLED'}
        self.iteration_cnt = 0
        context.scene.DynamicNodes_Properties.arrange_mode = True
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.03, context.window)
        wm.modal_handler_add(self)
        self._handle = bpy.types.SpaceNodeEditor.draw_handler_add(
                    DynamicNodes_Arrange_DrawCallBack, (self, context), 'WINDOW', 'POST_PIXEL')
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        context.scene.DynamicNodes_Properties.arrange_mode = False
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        bpy.types.SpaceNodeEditor.draw_handler_remove(self._handle, 'WINDOW')
        context.area.tag_redraw()
    
################################################################################
        
class DynamicNodes_Stop(bpy.types.Operator):
    """Stops Dynamic Nodes"""
    bl_label = "Dynamic Nodes Stop"
    bl_idname = "dynamic.nodes_stop"
    def execute(self,context):
        context.scene.DynamicNodes_Properties.live_mode = False
        return {'FINISHED'}
    
################################################################################
        
class DynamicNodes_Help(bpy.types.Operator):
    """Help"""
    bl_label = "Dynamic Nodes Help"
    bl_idname = "dynamic.nodes_help"
    def draw(self,context):
        layout = self.layout
        layout.label('Press Start button to start Live Mode.')
        layout.label('Press Arrange button to arrange nodes.')
        layout.label('In Live Mode hold ALT to disable collision of selected nodes.')
    def execute(self,context):
        return {'FINISHED'}
    def invoke(self,context,event):
        return context.window_manager.invoke_popup(self, width=350)
    
################################################################################
        
def elasticityUpdate(self,context):
    self.elasticity = self.showElasticity * 0.1
    
def intervalUpdate(self,context):
    self.interval = 1.0/self.ips
    
class DynamicNodesProps(bpy.types.PropertyGroup):
    defElasticity = 0.5
    defIPS = 24
    min_unit        = bpy.props.FloatProperty(
                        name = 'Min Unit',
                        default = 1)
    live_mode       = bpy.props.BoolProperty(
                        name = 'Live Mode',
                        default = False)
    arrange_mode    = bpy.props.BoolProperty(
                        name = 'Arrange Mode',
                        default = False)
    ips             = bpy.props.IntProperty(
                        name = 'Iterations Per Second',
                        default = defIPS,
                        min = 1,
                        soft_max = 50,
                        max = 100,
                        update = intervalUpdate)
    step1           = bpy.props.IntProperty(
                        name = 'Step 1 Max Iterations',
                        description = 'Set Higher For Better Results',
                        default = 128,
                        min = 0,
                        soft_max = 256)
    step2           = bpy.props.IntProperty(
                        name = 'Step 2 Max Iterations',
                        description = 'Set Higher For Better Results',
                        default = 128,
                        min = 0,
                        soft_max = 256)
    step3           = bpy.props.IntProperty(
                        name = 'Step 3 Max Iterations',
                        description = 'Set Higher For Better Results',
                        default = 64,
                        min = 0,
                        soft_max = 256)
    step4           = bpy.props.IntProperty(
                        name = 'Step 4 Max Iterations',
                        description = 'Set Higher For Better Results',
                        default = 32,
                        min = 0,
                        soft_max = 256)
    interval        = bpy.props.FloatProperty(
                        name = 'Interval',
                        default = 1.0/defIPS)
    distance        = bpy.props.FloatProperty(
                        name = 'Distance',
                        default = 50,
                        min = 10,
                        soft_max  = 150)
    node_limit      = bpy.props.IntProperty(
                        name = 'Node Limit',
                        description = 'Limit Node Calculations per Iteration (0 - No Limit)',
                        default = 0,
                        min = 0,
                        soft_max = 64)
    elasticLinks    = bpy.props.BoolProperty(
                        name = 'Elastic Links',
                        default = True)
    showElasticity  = bpy.props.FloatProperty(
                        name = 'Elasticity',
                        description = 'Elasticity of Links',
                        default = defElasticity,
                        min = 0,
                        max = 2,
                        update = elasticityUpdate)
    elasticity      = bpy.props.FloatProperty(
                        name = 'Elasticity',
                        default = defElasticity*0.1)
    collision       = bpy.props.BoolProperty(
                        name = 'Collision',
                        description = 'Enable Collision Between Nodes',
                        default = True)
    esc_stop       = bpy.props.BoolProperty(
                        name = 'Stop by ESC Button',
                        default = True)

class DynamicNodesPanel(bpy.types.Panel):
    """Adds physics to nodes"""
    bl_label = "Dynamic Nodes"
    bl_idname = "dynamic.nodes_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'TOOLS'
    bl_category = 'Dynamic Nodes'
        
    def draw(self, context):
        props = context.scene.DynamicNodes_Properties
        layout = self.layout
        box = layout.box()
        if props.live_mode:
            box.operator('dynamic.nodes_stop',text = 'Stop',icon = 'PAUSE')
        else:
            box.operator('dynamic.nodes',text = 'Start',icon = 'PLAY')
        
        col = box.column()
        col.prop(props,'ips')
        col.enabled = not props.live_mode
        box.enabled = not props.arrange_mode
        
        layout.separator()
        
        box = layout.box()
        box.operator('dynamic.nodes_arrange',text = 'Arrange',icon = 'SORTALPHA')
        col = box.column(align = True)
        col.prop(props,'step1')
        col.prop(props,'step2')
        col.prop(props,'step3')
        col.prop(props,'step4')
        box.enabled = not props.arrange_mode
        
        layout.separator()
        
        layout.prop(props,'distance')
        layout.prop(props,'node_limit')
        layout.prop(props,'elasticLinks')
        if props.elasticLinks:
            layout.prop(props,'showElasticity')
        layout.prop(props,'collision')
        
        row = layout.row()
        row.prop(props,'esc_stop')
        row.operator('dynamic.nodes_help',icon = 'QUESTION',text = '')

def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.DynamicNodes_Properties = bpy.props.PointerProperty(type = DynamicNodesProps)

def unregister():
    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.DynamicNodes_Properties


if __name__ == "__main__":
    register()
