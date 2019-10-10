# Athena

## What is Athena ?

Athena is an API and a tool made to create, manage and use Sanity Check and Fix process in Python.
It allow the user to define a list of process to execute in a specific order with some sort of parameter to ensure a minimum Quality/Sanity in a specific environment.

The built-in tool works with a lot of the most used CG software that have a python interpreter like Autodesk Maya, The Foundry Katana, Mari, Nuke, SideFx Houdini etc... (Feel free test it in another software.
Off course the tool only works in standalone mode into Linux, MacOs and Windows.


## How to setup an Athena package ?

Athena will automatically retrieve imported packages to find thoses with the matching name to load them.
The conventions is to have packages named **Athena_{prod}** where you replace `{prod}` with the name of you choice.

Congratulation, you are just a few steps to have your own Athena package:
- Create in your package any folder you want with the name of a soft (`standalone` is also natively supported). see AtConstants module for the currently supported software.
- In all of thes packages you need a `envs` and `processes` python packages.
- Add python module with the name of your env in the `envs` package to start.
- In the processes folder you are free to create any module you whant to write your processes. (e.g. Animation, Pipeline, Texturing or whatever you want.)
