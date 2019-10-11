# Athena

## What is Athena ?

Athena is an **API** and a **Tool** made to create, manage and use Sanity Check and Fix process in Python.
It allow the user to define a list of process to execute in a specific order with some sort of parameter to ensure a minimum Quality/Sanity in a specific environment.

The built-in tool works with a lot of the most used CG software that have a python interpreter like Autodesk Maya, The Foundry Katana, Mari, Nuke, SideFx Houdini etc... (Feel free to test it in another software)
Off course the tool also works as a standalone tool into Linux, MacOs and Windows.


## How to setup an Athena package ?

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

###### How to load your env ?

As I said before, the Register object will retrieve all imported Athena packages by parsing the `sys.path` so your Athena modules have to be be imported.
To simplify the use of this mechanic you can:
- Import your package in any startup script of you software. (Best for personal use)
- Resolve the right package through rez, conda or whatever you use. (Best for production)


###### How to write an env file ?

The environment file is a classic python module that define specific attributes that will be interpreted through Athena API, it have to follow a simple convention to be clear and easy to manage and support.

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
