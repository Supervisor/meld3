import unittest
from StringIO import StringIO

_SIMPLE_XML = r"""<?xml version="1.0"?>
<root xmlns:meld="http://www.plope.com/software/meld3">
  <list meld:id="list">
    <item meld:id="item">
       <name meld:id="name">Name</name>
       <description meld:id="description">Description</description>
    </item>
  </list>
</root>
"""

_SIMPLE_XHTML = r"""<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:meld="http://www.plope.com/software/meld3">
   <body meld:id="body">Hello!</body>
</html>
"""

_COMPLEX_XHTML = r"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:meld="http://www.plope.com/software/meld3"
      xmlns:bar="http://foo/bar">
  <head>
    <meta content="text/html; charset=ISO-8859-1" http-equiv="content-type" />
    <title meld:id="title">This is the title</title>
  </head>
  <!-- a comment -->
  <body>
    <div bar:baz="slab"/>
    <div meld:id="content_well">
      <form meld:id="form1" action="." method="POST">
      <table border="0" meld:id="table1">
        <tbody meld:id="tbody">
          <tr meld:id="tr" class="foo">
            <td meld:id="td1">Name</td>
            <td meld:id="td2">Description</td>
          </tr>
        </tbody>
      </table>
      </form>
    </div>
  </body>
</html>
"""

class MeldHelperTests(unittest.TestCase):
    def _getTargetClass(self):
        from meld3 import _MeldHelper
        return _MeldHelper

    def _makeOne(self, *arg, **kw):
        klass = self._getTargetClass()
        return klass(*arg, **kw)

    def _makeElement(self, string):
        data = StringIO(string)
        from meld3 import parse
        return parse(data)

    def test_ctor(self):
        helper = self._makeOne('foo')
        self.assertEqual(helper.element, 'foo')

    def test__getitem__(self):
        root = self._makeElement(_SIMPLE_XML)
        helper = self._makeOne(root)
        item = helper['item']
        self.assertEqual(item.tag, 'item')
        name = helper['name']
        self.assertEqual(name.text, 'Name')

    def test_get(self):
        root = self._makeElement(_SIMPLE_XML)
        helper = self._makeOne(root)
        item = helper.get('item')
        self.assertEqual(item.tag, 'item')
        unknown = helper.get('unknown', 'foo')
        self.assertEqual(unknown, 'foo')

    def test_repeat_nochild(self):
        root = self._makeElement(_SIMPLE_XML)
        helper = self._makeOne(root)
        item = helper['item']
        self.assertEqual(item.tag, 'item')
        data = [{'name':'Jeff Buckley', 'description':'ethereal'},
                {'name':'Slipknot', 'description':'heavy'}]
        for element, d in item.meld.repeat(data):
            element.meld['name'].text = d['name']
            element.meld['description'].text = d['description']
        self.assertEqual(item[0].text, 'Jeff Buckley')
        self.assertEqual(item[1].text, 'ethereal')

    def test_repeat_child(self):
        root = self._makeElement(_SIMPLE_XML)
        helper = self._makeOne(root)
        list = helper['list']
        self.assertEqual(list.tag, 'list')
        data = [{'name':'Jeff Buckley', 'description':'ethereal'},
                {'name':'Slipknot', 'description':'heavy'}]
        for element, d in list.meld.repeat(data, 'item'):
            element.meld['name'].text = d['name']
            element.meld['description'].text = d['description']
        self.assertEqual(list[0][0].text, 'Jeff Buckley')
        self.assertEqual(list[0][1].text, 'ethereal')
        self.assertEqual(list[1][0].text, 'Slipknot')
        self.assertEqual(list[1][1].text, 'heavy')

class MeldElementInterfaceTests(unittest.TestCase):
    def _getTargetClass(self):
        from meld3 import _MeldElementInterface
        return _MeldElementInterface

    def _makeOne(self, *arg, **kw):
        klass = self._getTargetClass()
        return klass(*arg, **kw)

    def test_ctor(self):
        iface = self._makeOne('div', {'id':'thediv'})
        self.assertEqual(iface.parent, None)
        self.assertEqual(iface.tag, 'div')
        self.assertEqual(iface.attrib, {'id':'thediv'})

    def test_append(self):
        div = self._makeOne('div', {'id':'thediv'})
        span = self._makeOne('span', {})
        div.append(span)
        self.assertEqual(div[0].tag, 'span')
        self.assertEqual(span.parent, div)

    def test__setitem__(self):
        div = self._makeOne('div', {'id':'thediv'})
        span = self._makeOne('span', {})
        span2 = self._makeOne('span', {'id':'2'})
        div.append(span)
        div[0] = span2
        self.assertEqual(div[0].tag, 'span')
        self.assertEqual(div[0].attrib, {'id':'2'})
        self.assertEqual(div[0].parent, div)

    def test_insert(self):
        div = self._makeOne('div', {'id':'thediv'})
        span = self._makeOne('span', {})
        span2 = self._makeOne('span', {'id':'2'})
        div.append(span)
        div.insert(0, span2)
        self.assertEqual(div[0].tag, 'span')
        self.assertEqual(div[0].attrib, {'id':'2'})
        self.assertEqual(div[0].parent, div)
        self.assertEqual(div[1].tag, 'span')
        self.assertEqual(div[1].attrib, {})
        self.assertEqual(div[1].parent, div)

    def test_meldproperty(self):
        div = self._makeOne('div', {'id':'thediv'})
        meld = div.meld
        from meld3 import _MeldHelper
        self.assertEqual(meld.__class__, _MeldHelper)
        self.assertEqual(meld.element, div)

    def test_clone(self):
        div = self._makeOne('div', {'id':'thediv'})
        span = self._makeOne('span', {})
        span2 = self._makeOne('span', {'id':'2'})
        span3 = self._makeOne('span3', {'id':'3'})
        div.append(span)
        span.append(span2)
        span2.append(span3)
        div2 = div.clone()

        self.assertEqual(div.tag, div2.tag)
        self.assertEqual(div.attrib, div2.attrib)
        self.assertEqual(div[0].tag, div2[0].tag)
        self.assertEqual(div[0].attrib, div2[0].attrib)
        self.assertEqual(div[0][0].tag, div2[0][0].tag)
        self.assertEqual(div[0][0].attrib, div2[0][0].attrib)
        self.assertEqual(div[0][0][0].tag, div2[0][0][0].tag)
        self.assertEqual(div[0][0][0].attrib, div2[0][0][0].attrib)
        
        self.failIfEqual(id(div), id(div2))
        self.failIfEqual(id(div[0]), id(div2[0]))
        self.failIfEqual(id(div[0][0]), id(div2[0][0]))
        self.failIfEqual(id(div[0][0][0]), id(div2[0][0][0]))
        
    def test_remove_noparent(self):
        div = self._makeOne('div', {})
        self.assertEqual(div.parent, None)
        div.remove()
        self.assertEqual(div.parent, None)
        
    def test_remove_withparent(self):
        parent = self._makeOne('parent', {})
        self.assertEqual(parent.parent, None)
        child = self._makeOne('child', {})
        parent.append(child)
        self.assertEqual(parent.parent, None)
        self.assertEqual(child.parent, parent)
        self.assertEqual(parent[0], child)
        child.remove()
        self.assertEqual(child.parent, None)
        self.assertRaises(IndexError, parent.__getitem__, 0)

class ParserTests(unittest.TestCase):
    def test_parse_simple_xml(self):
        from meld3 import parse
        from meld3 import _MELD_ID
        data = StringIO(_SIMPLE_XML)
        root = parse(data)
        self.assertEqual(root.tag, 'root')
        self.assertEqual(root.parent, None)
        l1st = root[0]
        self.assertEqual(l1st.tag, 'list')
        self.assertEqual(l1st.parent, root)
        self.assertEqual(l1st.attrib[_MELD_ID], 'list')
        item = l1st[0]
        self.assertEqual(item.tag, 'item')
        self.assertEqual(item.parent, l1st)
        self.assertEqual(item.attrib[_MELD_ID], 'item')
        name = item[0]
        description = item[1]
        self.assertEqual(name.tag, 'name')
        self.assertEqual(name.parent, item)
        self.assertEqual(name.attrib[_MELD_ID], 'name')
        self.assertEqual(description.tag, 'description')
        self.assertEqual(description.parent, item)
        self.assertEqual(description.attrib[_MELD_ID], 'description')

    def test_parse_simple_xhtml(self):
        xhtml_ns = '{http://www.w3.org/1999/xhtml}%s'
        from meld3 import parse
        from meld3 import _MELD_ID
        data = StringIO(_SIMPLE_XHTML)
        root = parse(data)
        self.assertEqual(root.tag, xhtml_ns % 'html')
        self.assertEqual(root.attrib, {})
        self.assertEqual(root.parent, None)
        body = root[0]
        self.assertEqual(body.tag, xhtml_ns % 'body')
        self.assertEqual(body.attrib[_MELD_ID], 'body')
        self.assertEqual(body.parent, root)

    def test_parse_complex_xhtml(self):
        xhtml_ns = '{http://www.w3.org/1999/xhtml}%s'
        from meld3 import parse
        from meld3 import _MELD_ID
        data = StringIO(_COMPLEX_XHTML)
        root = parse(data)
        self.assertEqual(root.tag, xhtml_ns % 'html')
        self.assertEqual(root.attrib, {})
        self.assertEqual(root.parent, None)
        head = root[0]
        self.assertEqual(head.tag, xhtml_ns % 'head')
        self.assertEqual(head.attrib, {})
        self.assertEqual(head.parent, root)
        meta = head[0]
        self.assertEqual(meta.tag, xhtml_ns % 'meta')
        self.assertEqual(meta.attrib['content'],
                         'text/html; charset=ISO-8859-1')
        self.assertEqual(meta.parent, head)
        title = head[1]
        self.assertEqual(title.tag, xhtml_ns % 'title')
        self.assertEqual(title.attrib[_MELD_ID], 'title')
        self.assertEqual(title.parent, head)
        body = root[1]
        self.assertEqual(body.tag, xhtml_ns % 'body')
        self.assertEqual(body.attrib, {})
        self.assertEqual(body.parent, root)
        
        div1 = body[0]
        self.assertEqual(div1.tag, xhtml_ns % 'div')
        self.assertEqual(div1.attrib, {'{http://foo/bar}baz': 'slab'})
        self.assertEqual(div1.parent, body)

        div2 = body[1]
        self.assertEqual(div2.tag, xhtml_ns % 'div')
        self.assertEqual(div2.attrib[_MELD_ID], 'content_well')
        self.assertEqual(div2.parent, body)

        form = div2[0]
        self.assertEqual(form.tag, xhtml_ns % 'form')
        self.assertEqual(form.attrib[_MELD_ID], 'form1')
        self.assertEqual(form.attrib['action'], '.')
        self.assertEqual(form.attrib['method'], 'POST')
        self.assertEqual(form.parent, div2)

        table = form[0]
        self.assertEqual(table.tag, xhtml_ns % 'table')
        self.assertEqual(table.attrib[_MELD_ID], 'table1')
        self.assertEqual(table.attrib['border'], '0')
        self.assertEqual(table.parent, form)

        tbody = table[0]
        self.assertEqual(tbody.tag, xhtml_ns % 'tbody')
        self.assertEqual(tbody.attrib[_MELD_ID], 'tbody')
        self.assertEqual(tbody.parent, table)

        tr = tbody[0]
        self.assertEqual(tr.tag, xhtml_ns % 'tr')
        self.assertEqual(tr.attrib[_MELD_ID], 'tr')
        self.assertEqual(tr.attrib['class'], 'foo')
        self.assertEqual(tr.parent, tbody)

        td1 = tr[0]
        self.assertEqual(td1.tag, xhtml_ns % 'td')
        self.assertEqual(td1.attrib[_MELD_ID], 'td1')
        self.assertEqual(td1.parent, tr)

        td2 = tr[1]
        self.assertEqual(td2.tag, xhtml_ns % 'td')
        self.assertEqual(td2.attrib[_MELD_ID], 'td2')
        self.assertEqual(td2.parent, tr)


class WriterTests(unittest.TestCase):
    def test_write_simple_xml(self):
        from meld3 import parse
        from meld3 import write
        data = StringIO(_SIMPLE_XML)
        root = parse(data)
        out = StringIO()
        write(root, out)
        out.seek(0)
        actual = out.read()
        expected = """<root>
  <list>
    <item>
       <name>Name</name>
       <description>Description</description>
    </item>
  </list>
</root>"""
        self.assertEqual(actual, expected)

        for el, data in root.meld['item'].meld.repeat(((1,2),)):
            el.meld['name'].text = str(data[0])
            el.meld['description'].text = str(data[1])
        out = StringIO()
        write(root, out)
        out.seek(0)
        actual = out.read()
        expected = """<root>
  <list>
    <item>
       <name>1</name>
       <description>2</description>
    </item>
  </list>
</root>"""
        self.assertEqual(actual, expected)
        
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest( unittest.makeSuite( MeldHelperTests ) )
    suite.addTest( unittest.makeSuite( MeldElementInterfaceTests ) )
    suite.addTest( unittest.makeSuite( ParserTests ) )
    suite.addTest( unittest.makeSuite( WriterTests ) )
    return suite

def main():
    unittest.main(defaultTest='test_suite')

if __name__ == '__main__':
    main()
    
