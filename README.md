# commandr - utility to build command line parsers for Python

Basically, it is a small convenience wrapper around argparse with some useful bits mixed in. 

* uses `argparse` for parsing CLI args
* substitutes values from ENV vars if provided
* can load multiple config files (JSON, YAML) into Python dicts, with optional
  `-Dkey=value` CLI overrides (dotted-key, via [scalpl](https://pypi.org/project/scalpl/))
* supports `nargs` for multi-value arguments
* can save/load its own schema as JSON/YAML, and auto-adds a `--saveconfig <path>`
  flag to dump the current schema

## Install

This library depends on the sibling library [kommons](https://github.com/mykkro/kommons)
(declared in `install_requires`), plus [PyYAML](https://pypi.org/project/PyYAML/) and
[scalpl](https://pypi.org/project/scalpl/).

```bash
pip install git+https://github.com/mykkro/kommons.git
pip install git+https://github.com/mykkro/commandr.git
```

Or, for local development (editable install, from clones of both repos):

```bash
pip install -e ../kommons
pip install -e .
```

## Basic Usage

```python
import os
import sys
from commandr import Commandr, load_yaml

print("Starting Commandr...")

LOADFROMFILE = False
if LOADFROMFILE:
    cmdr = Commandr.load("target/commandr-demo.cmdr.yaml")
else:
    cmdr = Commandr("commandr-demo", title="Commandr Demo")
    cmdr.add_argument("infile", "-i", type="str", required=True)
    cmdr.add_argument("count", "-c|--count", type="int", default=12345, env="COMMANDR_COUNT")
    cmdr.add_argument("config", "--config", default="config/config.yaml", loadconfig="-D")
    cmdr.add_argument("verbose", "-v|--verbose", type="switch", env="COMMANDR_VERBOSE")
    cmdr.add_argument("mybool", "--mybool", type="bool")
    cmdr.add_argument("date", "--date", type="datetime", format="%Y-%m-%d")
    cmdr.add_argument("foo", "--foo", type="int", nargs="+")
    cmdr.add_argument("bar", "--bar", type="str", nargs="*")
    cmdr.add_argument("baz", "--baz", type="float", nargs=3)
        
args, configs = cmdr.parse()

print("Args parsed:")
for argname in args:
    print(f"  ({args[argname]['source']}) {argname}: {args[argname]['value']}") 

print("Configs loaded:", configs)

# cmdr.save("target/commandr-demo.cmdr.yaml")

```

See [main.py](main.py) for a complete runnable example, including `-D` config
overrides (e.g. `-Ddummy-option=int:67890 -Dfoo.bar="as df"`) and `nargs`.

### Argument types

| `type` | Notes |
| --- | --- |
| `str` (default) | Plain string. |
| `int` / `float` | Cast via the matching Python builtin; CLI, ENV and default values are all coerced consistently. |
| `bool` | Parsed from a string value (CLI/ENV) via `kommons.str_to_bool`. |
| `switch` | A boolean flag (`action="store_true"`); absent means `False` unless `env` resolves it. |
| `datetime` | Requires `format` (a `strptime`-compatible string). |

### Value resolution order

For every argument, `parse()` resolves the value in this order: **CLI flag** >
**environment variable** (`env=...`) > **default** (`default=...`). If none of
these provide a value and `required=True`, parsing prints help and exits (`sys.exit(1)`).

## Development

Install the test dependencies and run the test suite with [pytest](https://docs.pytest.org/):

```bash
pip install -e ../kommons
pip install -e .
pip install pytest
pytest
```

## TODO & Nice2Have

* enhanced args validation
* validate JSON/YAML docs against a schema

## License

MIT, see [LICENSE](LICENSE).

