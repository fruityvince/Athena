# What is Athena ?

Athena is an **API** and a **Tool** made to create, manage and use Sanity Check and Fix process in Python.
It allow the user to define a list of process to execute in a specific order with some sort of parameter to ensure a minimum Quality/Sanity in a specific environment.

The built-in tool works with a lot of the most used CG software that have a python interpreter like Autodesk Maya, The Foundry Katana, Mari, Nuke, SideFx Houdini etc... (Feel free to test it in another software)
Off course the tool also works as a standalone tool into Linux, MacOs and Windows.


# How to setup an Athena package ?

Athena will automatically retrieve imported packages and modules in `sys.path` to find thoses with the matching name.
The convention is to have packages named **Athena_{whatever}** where you replace `{whatever}` with the name of you choice.

1. Create a python package starting with `Athena_`.
2. Create in this package any package you want with the name of a soft in lowercase (`standalone` is also natively supported). see AtConstants module for the currently supported software.
3. In all of theses packages you need an `envs` and `processes` python packages.
4. Add python module with the name of your env in the `envs` package to start. (If you want, also a a `png` file with the same name)
5 In the `processes` package you are free to create any module you whant to write your processes. (e.g. Animation, Pipeline, Texturing or whatever you want.)

You should have something like:
```
────Athena_example
    │   __init__.py
    │
    └───standalone
        │   __init__.py
        │
        ├───envs
        │       exampleEnv.png
        │       exampleEnv.py
        │       __init__.py
        │
        └───processes
                exampleProcessesModule.py
                __init__.py
```


# How to write an env file ?

The environment file is a classic python module that define specific attributes that will be interpreted through Athena API, it have to follow a simple convention to be clear and easy to manage and support.

###### header
`header` is the first variable to define in an env module, it define the process execution order and the IDs to use in all the module.
The header can be any ordered python iterable object containing one ID for each process you will add in the register. Each ID have to be unique and different from python object's default attributes. (I recommand a `tuple` if you want to define a basic env or a `list` if you have to append/insert/extend the header on the fly)

###### register
`register` is the variable that will store all process description, it needs to be a python `dict` with the precedently defined IDs as keys and a dict as value that contain:
- **'process'**: The process key is the minimum needed to define a process, its basically the full python import string.
- **'category'**: The category can be defined for any process and used to group them in a ui.
- **'tags'**: The tags will define some parameters into the Processes's Blueprints. Its one or more Tag separated with `|`.
- **'arguments'**: This is a dict with the method name as key and any ordered python iterable containing a `list` (for the args) and a `dict` (for the kwargs) as value.
- **'links'**: The links allow you to connect processes methods executions, it can be any ordered python iterable containing the ID of the linked process, the driver method and the driven method.

###### parameters
The `parameters` variable is a classic python dict where you can add any key/value pair you want to affect your tool comportment.

```python
"""
Description of the env
"""

from Athena.AtCore import Tag, Link, ID

header = \
(
  ID.ProcessExample1,
  ID.ProcessExample2,
  ID.ReadMeExample,
)

register = \
(
  ID.ProcessExample1:
    {
      'process': 'Athena_example.GitHub_README.standalone.process.exampleProcessesModule.ProcessExample1', 
      'category': 'Example',
      'tags': Tag.NO_BATCH | Tag.OPTIONAL,
      'arguments': 
        {
          '__init__': ([], {'value': 'example'})
        },
      'links': 
        [
          (ID.ReadMeExample, Link.FIX, Link.CHECK), 
        ],
    },

  ID.ProcessExample2:
    {
      'process': 'Athena_example.GitHub_README.standalone.process.exampleProcessesModule.ProcessExample2',
      'category': 'Test',
    }, 

  ID.ReadMeExample:
    {
      'process': 'Athena_example.GitHub_README.standalone.process.exampleProcessesModule.ReadMeExample',
      'tags': Tag.NO_BATCH,
      'category': 'Example'
    },
)

parameters = \
{
  'recheck': True,
}
```

## How to load your env ?

As I said before, the Register object will retrieve all imported Athena packages by parsing the `sys.path` so your Athena modules have to be be imported.
To simplify the use of this mechanic you can:
- Import your package in any startup script of you software. (Best for personal use)
- Resolve the right package through rez, conda or whatever you use. (Best for production)
