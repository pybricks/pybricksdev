import traceback
from unittest import TestCase
from pybricksdev import inline


class TestInliner(TestCase):
    def test_1_simple_import_from_sibling(self):
        # given
        script_path = 'inline_test_resources/1/script.py'

        # when
        output_path = inline.flatten(script_path)

        # then
        output = self.readFileContents(output_path)
        expected = self.readFileContents('inline_test_resources/1/expected.py')
        self.assertEqual(expected, output)

    def test_2_chained_import_from_sibling(self):
        # given
        script_path = 'inline_test_resources/2/script.py'

        # when
        output_path = inline.flatten(script_path)

        # then
        output = self.readFileContents(output_path)
        expected = self.readFileContents('inline_test_resources/2/expected.py')
        self.assertEqual(expected, output)

    def test_3_that_functions_and_classes_are_imported(self):
        # given
        script_path = 'inline_test_resources/3/script.py'

        # when
        output_path = inline.flatten(script_path)

        # then
        output = self.readFileContents(output_path)
        expected = self.readFileContents('inline_test_resources/3/expected.py')
        self.assertEqual(expected, output)

    def test_4_imported_file_in_subdirectory(self):
        # given
        script_path = 'inline_test_resources/4/script.py'

        # when
        output_path = inline.flatten(script_path)

        # then
        output = self.readFileContents(output_path)
        expected = self.readFileContents('inline_test_resources/4/expected.py')
        self.assertEqual(expected, output)

    def test_5_that_import_base_is_respected(self):
        # given
        script_path = 'inline_test_resources/5/subA/script.py'
        import_base = 'inline_test_resources/5'

        # when
        output_path = inline.flatten(script_path, import_base)

        # then
        output = self.readFileContents(output_path)
        expected = self.readFileContents('inline_test_resources/5/expected.py')
        self.assertEqual(expected, output)

    def test_6_that_repeated_imports_are_handled_correctly(self):
        # given
        script_path = 'inline_test_resources/6/script.py'

        # when
        output_path = inline.flatten(script_path)

        # then
        output = self.readFileContents(output_path)
        expected = self.readFileContents('inline_test_resources/6/expected.py')
        self.assertEqual(expected, output)

    def test_7_multiple_imports_on_same_line(self):
        # given
        script_path = 'inline_test_resources/7/script.py'

        # when
        output_path = inline.flatten(script_path)

        # then
        output = self.readFileContents(output_path)
        expected = self.readFileContents('inline_test_resources/7/expected.py')
        self.assertEqual(expected, output)

    def test_8_that_consistent_alias_is_handled_ok(self):
        # given
        script_path = 'inline_test_resources/8/script.py'

        # when
        output_path = inline.flatten(script_path)

        # then
        output = self.readFileContents(output_path)
        expected = self.readFileContents('inline_test_resources/8/expected.py')
        self.assertEqual(expected, output)

    def test_9_that_inconsistent_alias_is_an_error(self):
        # given
        script_path = 'inline_test_resources/9/script.py'

        # when
        try:
            inline.flatten(script_path)
            # then
            self.fail('Inconsistent alias should have caused an exception')
        except ImportError as ex:
            self.assertEqual("Module 'importB' has already been inlined using alias 'imbx' so cannot be inlined using alias 'imb'", ex.msg)

    def test_10_that_syntax_error_is_reported_correctly(self):
        # given
        script_path = 'inline_test_resources/10/script.py'

        # when
        try:
            inline.flatten(script_path)
            # then
            self.fail('Syntax error should have caused an exception')
        except SyntaxError as ex:
            self.assertEqual("invalid syntax", ex.msg)
            x = traceback.format_exc()
            self.assertTrue('inline_test_resources/10/importA.py' in traceback.format_exc(), 'Traceback should mention file')

    @staticmethod
    def readFileContents(path):
        with open(path, 'r') as f:
            contents = f.read()
        return contents
