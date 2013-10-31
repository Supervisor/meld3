import sys
import unittest
import tempfile

try:
    from StringIO import StringIO
except ImportError: # python 3
    from io import StringIO

_SOURCE_XML = """
<root>
  <a meld:id="a">
     <b meld:id="b">
       <c meld:id="c"></c>
     </b>
  </a>
  <z meld:id="z">
    <y meld:id="y"></y>
  </z>
</root>"""

_TARGET_XML = """
<root>
  <b meld:id="b">
    <c meld:id="c"></c>
  </b>
  <a meld:id="a"></a>
  <d meld:id="d">
     <e meld:id="e"></e>
  </d>
</root>
"""


class MeldExampleTests(unittest.TestCase):
    def test_diffs_files_and_outputs_results(self):
        src = tempfile.NamedTemporaryFile()
        src.write(_b(_SOURCE_XML))
        src.flush()

        tgt = tempfile.NamedTemporaryFile()
        tgt.write(_b(_TARGET_XML))
        tgt.flush()

        from .melddiff import main
        sio = StringIO()
        try:
            main(src.name, tgt.name, sio)
        finally:
            src.close()
            tgt.close()

        output = sio.getvalue()
        self.assertTrue("Added: d, e" in output)
        self.assertTrue("Removed: z, y" in output)
        self.assertTrue("Moved: b" in output)

def _b(x):
    try:
        unicode
    except NameError: #pragma NO COVER Python >= 3.0
        return bytes(x, 'latin1')
    else:
        return x

def test_suite():
    return unittest.findTestCases(sys.modules[__name__])

def main():
    unittest.main(defaultTest='test_suite')

if __name__ == '__main__':
    main()
