import os, json, itertools, argparse, yaml
import distutils.util


def load_yaml(yaml_path):
    with open(yaml_path, "r", encoding="utf-8") as infile:
        return yaml.load(infile, Loader=yaml.FullLoader)


def load_json(path):
    with open(path, "r", encoding="utf-8") as infile:
        data = json.load(infile)
    return data


def load_cfg(path):
    if path.endswith(".json"):
        return load_json(path)
    elif path.endswith(".yaml"):
        return load_yaml(path)
    else:
        raise Exception(f"Unsupported config format: {path}")


def environ_or_required(key):
    return (
        {'default': os.environ.get(key)} if os.environ.get(key)
        else {'required': True}
    )


def val_to_bool(val):
    # print("val_to_bool:", val, type(val))
    if type(val) == str:
        return bool(distutils.util.strtobool(val))
    else:
        return bool(val)

def type_by_name(name):
    if name == "str":
        return str
    if name == "int":
        return int
    if name == "float":
        return float

    # other types handle as string ...
    return 'str'


class Commandr(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.parser = None
        # print("Commandr created!", cfg)

    @staticmethod
    def from_file(path):
        c = Commandr(load_cfg(path))
        c.build()
        return c

    def schema_version():
        return "1.0"

    def build(self):
        # print("Building Commandr", self.cfg)
        self.parser, required, optional = Commandr.prepare_cli_args()
        for arg in self.cfg["args"]:
            # print("Argument:", arg)
            name = arg["name"]
            cli = arg["cli"].split("|")
            is_required = arg.get("required", False)
            help = arg.get("help")
            type = arg.get('type', 'str')
            basictype = type_by_name(type)
            # handle 'bool' options differently...
            target = required if is_required else optional
            if type == "switch":
                target.add_argument(*cli, dest=name, help=help, action='store_true')
            else:
                target.add_argument(*cli, dest=name, help=help, type=basictype)
        return self

    def parse(self, verbose=False):
        args = self.parser.parse_args()
        args_dict = vars(args)
        out = {}
        configs = {}
        for arg in self.cfg["args"]:
            name = arg["name"]
            required = arg.get("required")
            cli_val = args_dict.get(name)
            if arg.get('type') == 'bool':
                cli_val = val_to_bool(cli_val)
            default_val = arg.get("default")
            if arg.get("required") and "default" in arg:
                raise Exception(f"{name}: Required args cannot have default values!")
            has_default = "default" in arg
            env_val = os.getenv(arg.get("env")) if arg.get("env") else None
            if arg.get("type") == "switch" and arg.get("env"):
                env_val = val_to_bool(env_val)
            if verbose:
                print(f"{name}:")
                print("  CLI({cli_val}) ENV({env_val}) DEFAULT({default_val} REQUIRED({required})")

            source = None
            used_value = cli_val
            if (used_value is None) or ((arg.get("type") == "switch") and ("env" in arg)):
                used_value = env_val
                if used_value is None:
                    used_value = default_val
                    if used_value is None and not has_default:
                        if arg.get("required"):
                            raise Exception(f"{name} is required argument, but it is not provided!")
                        source = None
                    else:
                        source = "DEF"
                else:
                    source = "ENV"
            else:
                source = "CLI"

            if arg.get("loadconfig"):
                # the value will be used as path to config file
                configs[name] = load_cfg(used_value)

            if verbose:
                print(f"  source={source} value={used_value}")
            out[name] = dict(source=source, value=used_value)

        self.validate(out)

        return out, configs
        

    def validate(self, out):
        #print("Validating parsed params:", out)
        for arg in self.cfg["args"]:
            name = arg["name"]
            val = out[name]
            #print("  Validating:", val, arg)

    @staticmethod
    def prepare_cli_args():
        parser = argparse.ArgumentParser()
        optional = parser._action_groups.pop()
        required = parser.add_argument_group('required arguments')
        parser._action_groups.append(optional)
        return parser, required, optional

