# SPDX-License-Identifier: MIT
# Copyright (c) 2021 The Pybricks Authors

# Flatten imports into a single file prior to downloading - useful for hubs with no file system

import os
import ast


def flatten(script_path, import_base=None):
    """
    Flatten imports into a single file

    script_path: Path to the script to be processed.
    import_base: Path to a secondary root directory for inlined imports. Optional.
    The return value is the path to the flattened script
    """
    file_name = os.path.basename(script_path)
    file_dir = os.path.dirname(script_path)
    if file_name.endswith(".py"):
        file_name = file_name[: - 3]
    output_path = file_dir + "/" + file_name + ".flat.py"
    with open(output_path, "w") as output:
        _Script(script_path, file_name, import_base).flatten_into(output)
    return output_path


def _read_file_contents_as_lines(path):
    with open(path, "r") as f:
        contents = f.readlines()
    return contents


class _Module:
    def __init__(self, path, module_name, import_base, imports_done):
        self.script_path = path
        self.other_base_path = import_base
        self.exported_symbol_mappings = {}
        self.local_symbol_mappings = {}
        self.module_name = module_name
        self.imports_done = imports_done  # map of import path to its exported symbols

    def is_script(self):
        return False

    def flatten_into(self, output_file):
        code_lines = _read_file_contents_as_lines(self.script_path)
        code = "".join(code_lines)
        tree = ast.parse(code, self.script_path)
        # insert a backward pointer in every node
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node
        imports = []        # list of all imports to be performed
        names = []          # list of all symbolic names that might need to be substituted
        definitions = []    # list of all class and function definitions that will need to be exported
        assigns = []        # list of all assignments to variables that will need to be exported
        base_path = os.path.dirname(self.script_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if node.col_offset == 0:
                    for name in node.names:
                        imports.append(
                            _ImportStatement(
                                name.name,
                                name.asname,
                                node.lineno - 1,
                                base_path,
                                self.other_base_path,
                            )
                        )
            elif isinstance(node, ast.Name):
                symbol = node.id
                parent = node.parent
                end_offset = node.end_col_offset
                names.append(_Symbol(symbol, node.lineno - 1, node.col_offset, end_offset))
                while isinstance(parent, ast.Attribute):
                    symbol = symbol + "." + parent.attr
                    end_offset = parent.end_col_offset
                    names.append(_Symbol(symbol, node.lineno - 1, node.col_offset, end_offset))
                    parent = parent.parent
            elif not self.is_script():
                # only look for things to export if this is not the top level script
                if isinstance(node, ast.ClassDef) or isinstance(node, ast.FunctionDef):
                    # don't record class/function definitions made inside other definitions
                    if node.col_offset == 0:
                        name_offset = 6 if isinstance(node, ast.ClassDef) else 4
                        definitions.append(_DefStatement(node.name, self.module_name))
                        # the name of the class/function is not an AST 'name' so it won't
                        # be added to the list to substitute automatically - add it here
                        names.append(
                            _Symbol(
                                node.name,
                                node.lineno - 1,
                                name_offset,
                                name_offset + len(node.name),
                            )
                        )
                elif isinstance(node, ast.Assign):
                    if node.col_offset == 0:
                        assigns.append(
                            _AssignmentStatement(
                                ast.get_source_segment(code, node), self.module_name
                            )
                        )

        for an_import in imports:
            previous_import = self.imports_done.get(an_import.module_path)
            if previous_import is None:
                an_import.flatten(into=output_file, imports_done=self.imports_done)
                self.imports_done[an_import.module_path] = an_import
            else:
                if previous_import.alias != an_import.alias:
                    raise ImportError(
                        f"Module '{an_import.module_path}' has already been inlined using alias '{previous_import.alias}' so cannot be inlined using alias '{an_import.alias}'",
                        name=an_import.module_path,
                    )
            # always load the exported symbols into the current context, even if the import has already been done
            self.local_symbol_mappings.update(
                self.imports_done[an_import.module_path].exports
            )

        for a_definition in definitions:
            self.exported_symbol_mappings.update(
                a_definition.get_exported_symbol_mapping()
            )
            self.local_symbol_mappings.update(a_definition.get_local_symbol_mapping())

        for an_assign in assigns:
            self.exported_symbol_mappings.update(an_assign.get_exported_symbol_mapping())
            self.local_symbol_mappings.update(an_assign.get_local_symbol_mapping())

        # sort the symbols by line number and then start column number
        names.sort(key=lambda x: (x.line_number * 10000) + x.start_col_offset)
        current_line_num = 0
        import_lines = [x.line_number for x in imports]
        # copy all the lines up to next 'name' line
        while len(names) > 0 and current_line_num < len(code_lines):
            while current_line_num < names[0].line_number:
                if current_line_num not in import_lines:
                    self.write_with_reference(
                        output_file, code_lines[current_line_num], current_line_num
                    )
                current_line_num += 1
            # replace 'names' in the line
            up_to = 0
            result = ""
            current_line = code_lines[current_line_num]
            while len(names) > 0 and current_line_num == names[0].line_number:
                next_symbol = names[0]
                del names[0]
                result += current_line[up_to : next_symbol.start_col_offset]
                up_to = max(up_to, next_symbol.start_col_offset)
                if next_symbol.name in self.local_symbol_mappings:
                    result += self.local_symbol_mappings[next_symbol.name]
                    up_to = next_symbol.end_col_offset
                elif next_symbol.name in self.exported_symbol_mappings:
                    result += self.exported_symbol_mappings[next_symbol.name]
                    up_to = next_symbol.end_col_offset
                elif len(names) > 0 and current_line_num == names[0].line_number and next_symbol.start_col_offset == names[0].start_col_offset:
                    # There's another overlapping name that might match, so skip this one
                    pass
                else:
                    result += current_line[up_to : next_symbol.end_col_offset]
                    up_to = next_symbol.end_col_offset
            result += current_line[up_to:]

            # write the updated line
            self.write_with_reference(output_file, result, current_line_num)
            current_line_num += 1
        # copy any remaining lines
        while current_line_num < len(code_lines):
            self.write_with_reference(
                output_file, code_lines[current_line_num], current_line_num
            )
            current_line_num += 1
        return self.exported_symbol_mappings

    def write_with_reference(self, output_file, line, line_number):
        stripped_line = line.rstrip()
        if len(stripped_line) == 0:
            print(stripped_line, file=output_file)
        else:
            print(
                stripped_line
                + " # "
                + self.module_name
                + "#"
                + str(line_number + 1),
                file=output_file
            )


class _Script(_Module):
    def __init__(self, path, module_name, import_base):
        super().__init__(path, module_name, import_base, {})

    def is_script(self):
        return True


class _Symbol:
    def __init__(self, name, line_number, start_col_offset, end_col_offset):
        self.end_col_offset = end_col_offset
        self.name = name
        self.line_number = line_number
        self.start_col_offset = start_col_offset


class _ImportStatement:
    def __init__(self, module_path, alias, line_number, base_path, other_base_path):
        self.module_path = module_path
        self.alias = alias
        self.base_path = base_path
        self.other_base_path = other_base_path
        self.line_number = line_number
        self.exports = None

    def flatten(self, into, imports_done):
        import_file_name = self.module_path.replace(".", "/") + ".py"
        lookup_paths = [self.base_path]
        if self.other_base_path is not None:
            lookup_paths.append(self.other_base_path)
        for base_path in lookup_paths:
            module_file_path = base_path + "/" + import_file_name
            as_name = self.module_path if self.alias is None else self.alias
            if os.path.exists(module_file_path):
                self.exports = _Module(
                    module_file_path, as_name, self.other_base_path, imports_done
                ).flatten_into(into)
                return
        self.exports = {}
        # make sure this object isn't found when removing imports
        self.line_number = -1


class _NameDefiningStatement:
    def __init__(self, name, module):
        self.module = module
        self.name = name

    def get_exported_symbol_mapping(self):
        existing_access_symbol = self.module + "." + self.name
        new_access_symbol = self.module.replace(".", "__") + "__" + self.name
        return {existing_access_symbol: new_access_symbol}

    def get_local_symbol_mapping(self):
        existing_access_symbol = self.name
        new_access_symbol = self.module.replace(".", "__") + "__" + self.name
        return {existing_access_symbol: new_access_symbol}


class _DefStatement(_NameDefiningStatement):
    def __init__(self, name, module):
        super().__init__(name, module)


class _AssignmentStatement(_NameDefiningStatement):
    def __init__(self, line, module):
        chunks = line.split("=")
        name = chunks[0].strip()
        super().__init__(name, module)
