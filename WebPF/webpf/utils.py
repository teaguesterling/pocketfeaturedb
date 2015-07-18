class FunctionRegistry(dict):
    def register(self, key, override=False):
        if not override and key in self:
            raise KeyError("Cannot redefine key {} in registry".format(key))

        def decorator(fn):
            self[key] = fn
            return fn

        return decorator


def set_defaults(d, other):
    for k,v in other.items():
        d.setdefault(k, v)
    return d


def getattr_r(root, path, get=getattr):
    branch = root
    for step in path:
        branch = get(branch, step)
    leaf = branch
    return leaf

def getattr_rs(obj, path, delimiter='.', get=getattr):
    return getattr_r(obj, path.split(delimiter), get=get)
