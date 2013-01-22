"""Test cases for icode generation."""

import os.path
import re
import sys

import build
import icode
from myunit import Suite, run_test
from testhelpers import assert_string_arrays_equal_wildcards
from testdata import parse_test_cases
from testconfig import test_data_prefix, test_temp_dir
from testoutput import remove_prefix
from testtransform import builtins_wrapper, remove_comment_lines
from transform import DyncheckTransformVisitor
from errors import CompileError


# The builtins stub used during icode generation test cases.
ICODE_GEN_BUILTINS = 'fixtures/icodegen.py'


class IcodeGenerationSuite(Suite):
    test_case_files = ['icode-basic.test']
    
    def cases(self):
        c = []
        for f in self.test_case_files:
            c += parse_test_cases(
                os.path.join(test_data_prefix, f),
                builtins_wrapper(test_transform,
                                 os.path.join(test_data_prefix,
                                              ICODE_GEN_BUILTINS)),
                test_temp_dir, True)
        return c


def test_transform(testcase):
    """Perform a runtime checking transformation test case."""
    expected = remove_comment_lines(testcase.output)

    func_names = get_func_names(expected)

    builder = icode.IcodeBuilder()
    
    try:
        # Construct input as a single single.
        src = '\n'.join(testcase.input)
        # Parse and type check the input program.
        result = build.build(src, program_path='main',
                             target=build.TYPE_CHECK,
                             alt_lib_path=test_temp_dir)
        a = []
        # Transform each file separately.
        for t in result.files.values():
            # Skip the builtins module and files with '_skip.' in the path.
            if not t.path.endswith('/builtins.py') and '_skip.' not in t.path:
                # Transform parse tree and produce pretty-printed output.
                transform = DyncheckTransformVisitor(result.types,
                                                     result.files, True)
                t.accept(transform)
                t.accept(builder)

        for fn in func_names:
            a.append('def {}:'.format(fn))
            code = icode.render(builder.generated[fn])
            a.extend(code)
    except CompileError as e:
        a = e.messages
    assert_string_arrays_equal_wildcards(
        expected, a,
        'Invalid source code output ({}, line {})'.format(testcase.file,
                                                          testcase.line))


def get_func_names(expected):
    res = []
    for s in expected:
        m = re.match(r'def ([_a-zA-Z]+):', s)
        if m:
            res.append(m.group(1))
    if not res:
        raise RuntimeError('No function name in test case output')
    return res


if __name__ == '__main__':
    run_test(IcodeGenerationSuite(), sys.argv[1:])