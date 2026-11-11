import json
M = 'editor_toolset.toolsets.material.MaterialTools.'
O = 'editor_toolset.toolsets.object.ObjectTools.'
AT = 'editor_toolset.toolsets.asset.AssetTools.'
MI = 'editor_toolset.toolsets.material_instance.MaterialInstanceTools.'


def t(n, a):
    return execute_tool(n, json.dumps(a))['returnValue']


def sp(obj, vals):
    return t(O + 'set_properties', {'instance': obj, 'values': json.dumps(vals)})


class G:
    def __init__(self, mat):
        self.mat = mat
        self.n = {}
        self.x = -1600
        self.y = 0

    def node(self, name, cls, props=None, x=None, y=None):
        if x is None:
            x, y = self.x, self.y
            self.y += 180
            if self.y > 2400:
                self.y = 0
                self.x += 320
        e = t(M + 'add_expression', {'material_or_function': self.mat,
                                    'expression_class': {'refPath': '/Script/Engine.MaterialExpression' + cls},
                                    'x': x, 'y': y})
        if props:
            sp(e, props)
        self.n[name] = e
        return e

    def custom(self, name, code, inputs, otype='CMOT_Float3'):
        return self.node(name, 'Custom', {'code': code, 'outputType': otype,
                                          'inputs': [{'inputName': i} for i in inputs]})

    def sparam(self, name, pname, val):
        return self.node(name, 'ScalarParameter', {'parameterName': pname, 'defaultValue': val})

    def vparam(self, name, pname, rgb):
        return self.node(name, 'VectorParameter', {'parameterName': pname,
                                                   'defaultValue': {'r': rgb[0], 'g': rgb[1], 'b': rgb[2], 'a': 1}})

    def link(self, src, dst, din, sout=''):
        s = self.n[src] if isinstance(src, str) else src
        d = self.n[dst] if isinstance(dst, str) else dst
        t(M + 'connect_expressions', {'from_expression': s, 'from_output_name': sout,
                                      'to_expression': d, 'to_input_name': din})

    def out(self, src, prop, sout=''):
        s = self.n[src] if isinstance(src, str) else src
        t(M + 'connect_to_output', {'expression': s, 'output_name': sout, 'material_property': prop})

    def compile(self):
        t(M + 'layout_expressions', {'material_or_function': self.mat})
        t(M + 'recompile', {'material_or_function': self.mat})


def new_material(folder, name, props=None):
    path = folder + '/' + name
    if t(AT + 'exists', {'path': path}):
        t(AT + 'delete', {'path': path})
    mat = t(M + 'create_material', {'folder_path': folder, 'asset_name': name})
    if props:
        sp(mat, props)
    return G(mat)
