import unittest


class MeldExampleTests(unittest.TestCase):
    def test_mutates_xml_and_outputs_it(self):
        from xml.etree.ElementTree import fromstring as et_fromstring
        try:
            from io import BytesIO
        except: # python 2.5
            from StringIO import StringIO as BytesIO
        from .example import main
        sio = BytesIO()
        main(sio)

        output = sio.getvalue()
        root = et_fromstring(output)

        if hasattr(root, "iter"):
            iterator = root.iter("tr") # python 2.7 or later
        else:
            iterator = root.getiterator("tr")

        for i, tr in enumerate(iterator):
            els = list(tr)
            self.assertEqual(len(els), 2)

            if i == 0:
                self.assertEqual(els[0].tag, "th")
                self.assertEqual(els[0].text, "Name")
                self.assertEqual(els[1].tag, "th")
                self.assertEqual(els[1].text, "Description")
            elif i == 1:
                self.assertEqual(els[0].tag, "td")
                self.assertEqual(els[0].text, "Boys")
                self.assertEqual(els[1].tag, "td")
                self.assertEqual(els[1].text, "Ugly")
            elif i == 2:
                self.assertEqual(els[0].tag, "td")
                self.assertEqual(els[0].text, "Girls")
                self.assertEqual(els[1].tag, "td")
                self.assertEqual(els[1].text, "Pretty")

        self.assertEqual(i, 2)


def test_suite():
    import sys
    return unittest.findTestCases(sys.modules[__name__])

def main():
    unittest.main(defaultTest='test_suite')

if __name__ == '__main__':
    main()
