# Inlining imports with pybricksdev
Most PoweredUp hubs are too small to have file systems, so splitting your PyBricks code
across several imported modules isn't possible - the entire program must 
reside in the script file. However, the `--inline-imports` option
for the 'run' and 'compile' functions in pybricksdev specifies that imports
that refer to modules in the host file system should be flattened into the
main script, so that the resulting program is still in one file. The intention is to
retain compatibility with desktop Python so that PyBricks code could, with simulated
PyBricks libraries, be run on the desktop.

## Using the Command line

### The --inline-imports option
Here's an example command line:

    pybricksdev run --inline-imports True ble "Pybricks Hub" demo/shortdemo.py

With that option, any import statement that refers to a local module will cause
that module to be flattened into the main script. The option can be shortened to just `-i`:

    pybricksdev run -i True ble "Pybricks Hub" demo/shortdemo.py

If you want to look at the flattened result you can find it in the same directory as the input script,
with the name `_flat_<your-script>.py`

### Limitations
There are some limitations:

- Only the import statement is supported, not the `from x import y` syntax
- You can't mix local imports and imports of built-in packages on the same line
  (but you shouldn't do that anyway!)
- Only import statements with no indentation are supported (so no imports inside definitions or
  conditionals)
- Relative imports are not supported
- If you specify an alias for the import (`import x as y`) then the alias has to be the
  same in all places where the module is imported. An exception will be raised if you
  break this rule.

### Module lookup
The base directory for module lookup is the directory containing the
specified script file. So in the above example that is the `demo` directory.

    import myutils

will flatten the file `demo/myutils.py`, and the contents of the import can be
referenced in the normal way:

    print(myutils.pi)

The import:

    import allutils.myutils

will flatten the file `demo/allutils/myutils.py`, and a reference would look like this:

    print(allutils.myutils.pi)

### The --importbase option
You can specify an additional base directory for import lookups using the
`--importbase` option. This additional base directory is only used if the
imported file is not found in the normal base directory.
If you have this file structure:

    demo/
      scripts/
        shortdemo.py
        myimport.py
      resources/
        myutils.py
      myimport.py

then you might use this command:

    pybricksdev run --inline True --importbase demo ble demo/scripts/shortdemo.py

and your script might be:

    import resources.myutils
    import myimport.py        # imports the file found in scripts, not the one in demo
    print(resources.utils.pi)
    print(myimport.x)

### Aliases
Aliases work as normal:

    import resources.myutils as theutils
    print(theutils.pi)

###Example
If your script contains this:

    import myutils
    
    print(myutils.square(4))

and myutils.py, in the same directory, contains this:

    def square(val):
        return val*val

then the resulting flattened file will contain:

    def myutils__square(val):
        return val*val
    
    print(myutils__square(4))

## Using pybricksdev as a library

    from pybricksdev import inline

    output_path = inline.flatten(script_path)

