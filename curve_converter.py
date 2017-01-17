# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "Curve Converter",
    "description": "Converts Curve To Mesh To Allow Updating Of Mesh",
    "author": "Jacob Morris",
    "blender": (2, 78, 0),
    "location": "View 3D > Tools > Tools > Curve Converter",
    "version": (0, 9),
    "category": "Object"
    }

import bpy
from bpy.props import StringProperty, BoolProperty, CollectionProperty
bpy.types.Object.cc_parent_curve = StringProperty(name="", default="")
bpy.types.Object.cc_rscale = BoolProperty(name="Respect Scale?", default=False)


def convert_curve(self, context):
    o = context.object
    o.select = False
    names = o.cc_parent_curve.split(",")
    converted_names = []

    # get materials names from mesh object before update
    mats = []
    for mat in o.data.materials:
        mats.append(mat.name)            
            
    for name in names:
        if name in bpy.data.objects:
            curve = bpy.data.objects[name]

            if curve.type == "CURVE":
                curve.select = True
                context.scene.objects.active = curve
                bpy.ops.object.duplicate()               
                bpy.ops.object.convert(target="MESH")
                temp = context.object

                # if name == names[0]:  # if first mesh
                #     for mat in curve.data.materials:
                #         if mat.name not in o.data.materials:
                #             o.data.materials.append(mat)
                #
                #     o.data = context.object.data
                #     o.select, temp.select = False, True
                #     context.scene.objects.active = temp
                #     bpy.ops.object.delete()
                #     o.select = True
                #     context.scene.objects.active = o
                # else:
                converted_names.append(temp.name)

                # for mat in mats:
                #     if mat not in o.data.materials:
                #         o.data.materials.append(bpy.data.materials[mat])
            else:
                self.report({"ERROR"}, "Curve Converter: Object Not Curve")
        else:
            self.report({"ERROR"}, "Curve Converter: Object Not Found")

    # join multiple objects and update o.data
    if converted_names:
        for name in converted_names:
            bpy.data.objects[name].select = True

        context.scene.objects.active = bpy.data.objects[converted_names[0]]
        bpy.ops.object.join()
        o.data = context.object.data
        bpy.ops.object.delete()

        o.select = True
        context.scene.objects.active = o

        # clean up geometry
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0001)
        bpy.ops.mesh.normals_make_consistent()
        bpy.ops.object.mode_set()

        # respect scale of curve is cc_rscale and only a single parent scale
        if o.cc_rscale and len(converted_names) == 1:
            o.scale = bpy.data.objects[converted_names[0]].scale
        else:
            o.scale = (1, 1, 1)


class CurveConverterAdd(bpy.types.Operator):
    bl_label = "Add Mesh Object"
    bl_idname = "mesh.curve_convert_add"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        out = []
        highest = -1000000  # basically any value should be larger than this
        for ob in context.selected_objects:
            if ob.type == "CURVE":
                out.append(ob.name)
                if ob.location[2] > highest:
                    highest = ob.location[2]

        if out:
            bpy.ops.mesh.primitive_cube_add()
            context.object.cc_parent_curve = ",".join(out)

            convert_curve(self, context)
            loc = list(context.object.location)
            loc[2] = highest + 0.5
            context.object.location = loc
        
        return {"FINISHED"}


class CurveConverterAddMultiple(bpy.types.Operator):
    bl_label = "Add Multiple Mesh Objects"
    bl_idname = "mesh.curve_convert_add_multiple"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        currently_selected = []
        # get names
        for i in context.selected_objects:
            currently_selected.append(i.name)

        # deselect all
        for o in context.selected_objects:
            o.select = False

        # use name to get objects and convert
        for ob_name in currently_selected:
            ob = bpy.data.objects[ob_name]
            loc = list(ob.location)
            loc[2] += 0.5
            bpy.ops.mesh.primitive_cube_add(location=loc)
            context.object.cc_parent_curve = ob_name
            convert_curve(self, context)
            
        return {"FINISHED"}
            
        
class CurveConversionUpdate(bpy.types.Operator):
    bl_label = "Update Mesh"
    bl_idname = "mesh.curve_convert_update"
    bl_options = {"UNDO"}
    
    def execute(self, context):
        convert_curve(self, context)
        return {"FINISHED"}


class CurveConversionUpdateAll(bpy.types.Operator):
    bl_label = "Propagate Changes"
    bl_idname = "mesh.curve_convert_update_all"
    bl_options = {"UNDO"}
    
    @classmethod
    def poll(cls, context):
        return context.object.type == "CURVE"

    def execute(self, context):
        o = context.object
        # change out of editmode if needed
        mode = o.mode
        bpy.ops.object.mode_set(mode="OBJECT")
        
        names = []

        for obj in bpy.data.objects:
            split_names = obj.cc_parent_curve.split(",")
            if o.name in split_names:
                names.append(obj.name)

        o.select = False
        
        for n in names:
            temp = bpy.data.objects[n]
            temp.select = True
            context.scene.objects.active = temp
            convert_curve(self, context)
            temp.select = False

        # tell user number of objects updated
        if not names:
            self.report({"INFO"}, "Curve Converter: No Objects Updated")
        else:
            self.report({"INFO"}, "Curve Converter: {} Object(s) Updated".format(len(names)))
            
        o.select = True
        context.scene.objects.active = o
        bpy.ops.object.mode_set(mode=mode)
        
        return {"FINISHED"}
        
                
class CurveConverterPanel(bpy.types.Panel):
    bl_label = "Curve Converter"
    bl_idname = "OBJECT_PT_curve_convert"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = "Tools"

    def draw(self, context):
        layout = self.layout
        o = context.object

        if o is not None:
            if o.type == "MESH":
                layout.label("Curve Name(s):", icon="OUTLINER_OB_CURVE")

                names = o.cc_parent_curve.split(",")
                if len(names) > 1:
                    for name in names:
                        layout.label("    " + name)
                else:
                    layout.prop_search(o, "cc_parent_curve",  context.scene, "objects")
                    layout.prop(o, "cc_rscale", icon="MAN_SCALE")

                layout.separator()
                layout.operator("mesh.curve_convert_update", icon="FILE_REFRESH")
            elif o.type == "CURVE":
                if context.mode not in ("EDIT_CURVE", "EDIT_MESH"):
                    layout.operator("mesh.curve_convert_add", icon="MESH_CUBE")

                    if len(context.selected_objects) > 1:
                        layout.operator("mesh.curve_convert_add_multiple", icon="GROUP")
                        
                layout.operator("mesh.curve_convert_update_all", icon="FILE_REFRESH")
            else:
                layout.label("Object Needs To Be Curve Or Mesh Object", icon="ERROR")
        else:
            layout.label("Select Curve Or Mesh Object", icon="ERROR")


def register():
    bpy.utils.register_module(__name__)


def unregister():
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()
