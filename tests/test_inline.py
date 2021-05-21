import traceback
from pybricksdev import inline


def test_1_simple_import_from_sibling():
    # given
    script_path = "inline_test_resources/1/script.py"

    # when
    output_path = inline.flatten(script_path)

    # then
    output = readFileContents(output_path)
    expected = readFileContents("inline_test_resources/1/expected.py")
    assert expected == output


def test_2_chained_import_from_sibling():
    # given
    script_path = "inline_test_resources/2/script.py"

    # when
    output_path = inline.flatten(script_path)

    # then
    output = readFileContents(output_path)
    expected = readFileContents("inline_test_resources/2/expected.py")
    assert expected == output


def test_3_that_functions_and_classes_are_imported():
    # given
    script_path = "inline_test_resources/3/script.py"

    # when
    output_path = inline.flatten(script_path)

    # then
    output = readFileContents(output_path)
    expected = readFileContents("inline_test_resources/3/expected.py")
    assert expected == output


def test_4_imported_file_in_subdirectory():
    # given
    script_path = "inline_test_resources/4/script.py"

    # when
    output_path = inline.flatten(script_path)

    # then
    output = readFileContents(output_path)
    expected = readFileContents("inline_test_resources/4/expected.py")
    assert expected == output


def test_5_that_import_base_is_respected():
    # given
    script_path = "inline_test_resources/5/subA/script.py"
    import_base = "inline_test_resources/5"

    # when
    output_path = inline.flatten(script_path, import_base)

    # then
    output = readFileContents(output_path)
    expected = readFileContents("inline_test_resources/5/expected.py")
    assert expected == output


def test_6_that_repeated_imports_are_handled_correctly():
    # given
    script_path = "inline_test_resources/6/script.py"

    # when
    output_path = inline.flatten(script_path)

    # then
    output = readFileContents(output_path)
    expected = readFileContents("inline_test_resources/6/expected.py")
    assert expected == output


def test_7_multiple_imports_on_same_line():
    # given
    script_path = "inline_test_resources/7/script.py"

    # when
    output_path = inline.flatten(script_path)

    # then
    output = readFileContents(output_path)
    expected = readFileContents("inline_test_resources/7/expected.py")
    assert expected == output


def test_8_that_consistent_alias_is_handled_ok():
    # given
    script_path = "inline_test_resources/8/script.py"

    # when
    output_path = inline.flatten(script_path)

    # then
    output = readFileContents(output_path)
    expected = readFileContents("inline_test_resources/8/expected.py")
    assert expected == output


def test_9_that_inconsistent_alias_is_an_error():
    # given
    script_path = "inline_test_resources/9/script.py"

    # when
    try:
        inline.flatten(script_path)
        # then
        assert False, "Inconsistent alias should have caused an exception"
    except ImportError as ex:
        assert (
            "Module 'importB' has already been inlined using alias 'imbx' so cannot be inlined using alias 'imb'"
            == ex.msg
        )


def test_10_that_syntax_error_is_reported_correctly():
    # given
    script_path = "inline_test_resources/10/script.py"

    # when
    try:
        inline.flatten(script_path)
        # then
        assert False, "Syntax error should have caused an exception"
    except SyntaxError as ex:
        assert "invalid syntax" == ex.msg
        x = traceback.format_exc()
        assert "inline_test_resources/10/importA.py" in traceback.format_exc()


def readFileContents(path):
    with open(path, "r") as f:
        contents = f.read()
    return contents
