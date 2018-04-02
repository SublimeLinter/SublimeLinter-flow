SublimeLinter-flow
================================

[![Build Status](https://travis-ci.org/SublimeLinter/SublimeLinter-flow.svg?branch=master)](https://travis-ci.org/SublimeLinter/SublimeLinter-flow)

This linter plugin for [SublimeLinter](https://github.com/SublimeLinter/SublimeLinter) provides an interface to [flow](http://flowtype.org/) (0.1.0 or later), a static type checker for JavaScript.
It will be used with files that have the "JavaScript" syntax.


## Installation

SublimeLinter must be installed in order to use this plugin. 

Please use [Package Control](https://packagecontrol.io) to install the linter plugin.

[Getting started with Flow](http://flowtype.org/docs/getting-started.html#installing-flow)

Please make sure that the path to `flow` is available to SublimeLinter.
The docs cover [troubleshooting PATH configuration](http://sublimelinter.com/en/latest/troubleshooting.html#finding-a-linter-executable).


## Settings

- SublimeLinter settings: http://sublimelinter.com/en/latest/settings.html
- Linter settings: http://sublimelinter.com/en/latest/linter_settings.html

Additional SublimeLinter-flow settings:

|Setting|Description|
|:------|:----------|
|lib|Add a path to your interface files. [More info](http://flowtype.org/docs/third-party.html#interface-files)|
|show-all-errors|It allows flow to output all errors instead of stopping at 50|
|executable|Allows to specify the path to the flow executable|
|coverage|Shows flow coverage warnings|
|all|runs flow against all files regardless of `@flow` comment|

### Warning

At this moment, using `all` in a medium to big sized node.js project may cause a **crash**.  It's recommended to use `flow` incrementally,  one file at a time.

