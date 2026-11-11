import json
M = 'editor_toolset.toolsets.material.MaterialTools.'
O = 'editor_toolset.toolsets.object.ObjectTools.'
AT = 'editor_toolset.toolsets.asset.AssetTools.'
def t(n, a):
    return execute_tool(n, json.dumps(a))['returnValue']
def sp(obj, vals):
    return t(O + 'set_properties', {'instance': obj, 'values': json.dumps(vals)})
class G:
    def __init__(self, mat):
        self.mat = mat; self.n = {}; self.x = -1600; self.y = 0
    def node(self, name, cls, props=None):
        e = t(M + 'add_expression', {'material_or_function': self.mat,'expression_class': {'refPath': '/Script/Engine.MaterialExpression' + cls},'x': self.x, 'y': self.y})
        self.y += 160
        if props: sp(e, props)
        self.n[name] = e
        return e
    def custom(self, name, code, inputs, otype='CMOT_Float3'):
        e = self.node(name, 'Custom', {'code': code, 'outputType': otype})
        sp(e, {'inputs': [{'inputName': inputs[0]}]})
        if len(inputs) > 1:
            cur = json.loads(t(O+'get_properties',{'instance':e,'properties':['inputs']}))['inputs']
            sp(e, {'inputs': cur + [{'inputName': i} for i in inputs[1:]]})
        return e
    def sparam(self, name, pname, val):
        return self.node(name, 'ScalarParameter', {'parameterName': pname, 'defaultValue': val})
    def vparam(self, name, pname, rgb):
        return self.node(name, 'VectorParameter', {'parameterName': pname,'defaultValue': {'r': rgb[0], 'g': rgb[1], 'b': rgb[2], 'a': 1}})
    def link(self, src, dst, din, sout=''):
        t(M + 'connect_expressions', {'from_expression': self.n[src], 'from_output_name': sout,'to_expression': self.n[dst], 'to_input_name': din})
    def out(self, src, prop, sout=''):
        t(M + 'connect_to_output', {'expression': self.n[src], 'output_name': sout, 'material_property': prop})
    def compile(self):
        t(M + 'layout_expressions', {'material_or_function': self.mat})
        t(M + 'recompile', {'material_or_function': self.mat})
def new_material(folder, name, props=None):
    path = folder + '/' + name
    if t(AT + 'exists', {'path': path}): t(AT + 'delete', {'path': path})
    mat = t(M + 'create_material', {'folder_path': folder, 'asset_name': name})
    if props: sp(mat, props)
    return G(mat)
