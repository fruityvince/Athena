*Currently in beta, can be unstable. Feel free to give feedback and open issues if needed.*

# What is Athena ?

Athena is an **API** and a **Tool** made to create and manage Sanity Check and Fix process in Python.
It allow the user to define a list of process to execute in a specific order with some sort of parameters to ensure a minimum Quality/Sanity in a specific environment.

The built-in tool works with a lot of the most used CG software that have a python interpreter like Autodesk Maya, The Foundry Katana, Mari, Nuke, SideFx Houdini etc... (Feel free to test it in another software)
Off course the tool also works as a standalone tool into Linux, MacOs and Windows.


# How to setup an Athena package ?

Athena will automatically retrieve imported packages and modules in `sys.path` to find thoses with the matching name.
The convention is to have the `Athena_` prefix before the package name.

1. Create a python package starting with `Athena_`.
2. Create any package you whant that will all contain the following hierarchy. (This is the **context** that can also contain an image named `icon.png`)
3. Create in this package any package you need with the name of a soft in lowercase (`standalone` is also natively supported). see `Athena.AtConstants` module for the currently supported softwares.
4. In all of theses packages you need an `envs` and `processes` python packages.
5. Add python module with the name of your env in the `envs` package to start. (If you want, also a `.png` file with the same name)
6. In the `processes` package you are free to create any module you want to write your processes. (e.g. Animation, Pipeline, Texturing or whatever you want.)

You should have something like:
```
├───Athena_example
   │   __init__.py
   │
   └───UserContext
       │   icon.png
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


# How to write an Athena Process class ?

Any process to use within Athena have to inherit from `Athena.AtCore.Process` that is an abstract object and can not be instanciated, it comes with `check`, `fix` and `tool` methods that you will need to override. If they are overrided the `Athena.AtCore.Blueprint` object will have its equivalent attributes to `True` (`isCheckable` if the Process have the `check` method overrided, `isFixable` for the `fix` and `hasTool` for the `tool`).

The Process base class will also define attributes like `toCheck`, `toFix`, `data` and `iChecked` for you to manage your data internally (But you can define yours).
There also are dunder variables like `_docFormat_` which have to be a dict containing key/value pair to format the `__doc__` attribute of your class.

## The methods to override:

###### check
First in the check method you have to clear the feedback by calling `clearFeedback` method (to prevent have the feedback added everytime you will launch the check again).
Then you are free to retieve/update the data to check and do whatever you need. (Note that you can define all the methods you want. PS: You should not override parent class methods except `check`, `fix` and/or `tool`)

At the end of the check or wherever you will have to add data to fix you will need to call the `addFeedback` method.
This method takes a `title` and an iterable `toDisplay` for data retrieved (if python object `Ellipsis` is given the check will only have a title). You can also add another iterable `toSelect` with the data to use for selection (of course `toDisplay` and `toSelect` will need to be ordered the same way). The last optional argument `documentation` is meant to be used to link a doc to this feedback (Usefull to display a pop up with detailled indication for a possible manual fix).

###### fix
The fix will have to use the data retrieved through the check method, you can use the data stored in an instance attribute or re-launch the check.
The `isChecked` default Process attribute is meant to be set to `True` before leaving the check and to `False` after leaving the fix, you can easily use it or any other boolean attribute to check if you have to launch the check before or not.

###### tool
The tool is the quickest method to override because it only need to handle the initialisation of another Qt tool.
You can either choose to:
- Call `show()` directly in the tool method to show your ui.
- Create your object and return it. (Athena tool will automatically parent your window to itself)


## What else ?

###### QProgressBar
The Process object can give you access to a QProgressBar (That you will need to connect in you ui using `Athena.AtCore.Blueprint.setProgressbar` method).
If a progress bar is connected to your Process you can use the `Athena.AtCore.Process.setProgressValue` that take first the new progress value and the text to display in the widget.

###### Athena.AtCore.automatic
This decorator allow you to decorate a Process to handle many things:
- Call `Athena.AtCore.Process.clearFeedback` automatically before running the `check` method.
- Reset `toCheck`, `toFix` and `data` attributes to their default value.
- Set the `isChecked` value to `True` after the `check` and `False` after the `fix`.

###### e.g.
```python
from Athena import AtCore

class ProcessExample1(AtCore.Process):
    """This docstring will be retrieved to be used as a help documentation. (included in Athena tool)
    You should explain clearly what the check, fix and other overrided method will do.

    Check: 
	Explain clearly what this check will do.

    Fix: 
	Explain clearly how the fix will correst the errors.

    Misc: 
	- Here you can specify if there is specificities to know before using this check
	- You can also give details on known issues.
    """

    def __init__(self):
        """ __init__ docstring """

	pass

    def check(self):
        """ check docstring """

        self.clearFeedback()
        toFix = []

        toCheck = range(50)
        baseValue = 100./(len(toCheck) or 0)
        for i, each in enumerate(toCheck):
            self.setProgressValue(i*baseValue)
            
	    # Check what you want, do you condition ...
            toFix.append(each)

        self.toFix = toFix

        self.isChecked = True
        return toFix
      
    def fix(self):
        """ fix docstring """

        if not self.isChecked:
            self.check()
         
        for each in self.toFix:
            # fix the problem
         
        self.isChecked = False
    
    def tool(self):
        """ tool docstring """
      
        return myUi()

```

# How to write an env file ?

The environment file is a classic python module that define specific attributes that will be interpreted through Athena API, it have to follow a simple convention to be clear and easy to manage and support.

###### header
This is the first variable to define in an env module, it define the process execution order and the IDs to use in all the module.
The header can be any ordered python iterable object containing one ID for each process you will add in the register. Each ID have to be unique and different from python object's default attributes. (I recommand a `tuple` if you want to define a basic env or a `list` if you have to append/insert/extend the header on the fly)

###### register
This variable will store all processes description, it needs to be a python `dict` with the precedently defined IDs as keys and a dict as value that contain:
- **'process'**: The process key is the minimum needed to define a process, its basically the full python import string.
- **'category'**: The category can be defined for any process and used to group them in a ui.
- **'tags'**: The tags will define some parameters into the Processes's Blueprints. Its one or more Tag separated with `|`.
- **'arguments'**: This is a dict with the method name as key and any ordered python iterable containing a `list` (for the args) and a `dict` (for the kwargs) as value.
- **'links'**: The links allow you to connect processes methods executions, it can be any ordered python iterable containing the ID of the linked process, the driver method and the driven method.
- **'options'**: The options allow you to specify custom parameters for your Process that will be available through the Blueprint to customize behaviour into a tool.

###### parameters
The `parameters` variable is a classic python dict where you can add any key/value pair you want to affect your tool behaviour.
Athena tool can recognize:
- 'recheck': If `True` the `Fix all` will trigger the `Check all`. (bool)

###### e.g.
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

# How to load your env ?

As I said before, the Register object will retrieve all imported Athena packages by parsing the `sys.path` so your Athena modules have to be be imported.
To test it you can run the following code:
```python
import Athena.ressources.Athena_example.UserContext
```

To simplify the use of this mechanic you can:
- Import your package in any startup script of you software. (Best for personal use)
- Resolve the right package through rez, conda or whatever you use. (Best for production)


**This project is licensed under the terms of the MIT license.**
