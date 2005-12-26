import unittest
from StringIO import StringIO
import re

_SIMPLE_XML = r"""<?xml version="1.0"?>
<root xmlns:meld="http://www.plope.com/software/meld3">
  <list meld:id="list">
    <item meld:id="item">
       <name meld:id="name">Name</name>
       <description meld:id="description">Description</description>
    </item>
  </list>
</root>"""

_SIMPLE_XHTML = r"""<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:meld="http://www.plope.com/software/meld3">
   <body meld:id="body">Hello!</body>
</html>"""

_EMPTYTAGS_HTML = """<html>
  <body>
    <area/><base/><basefont/><br/><col/><frame/><hr/><img/><input/><isindex/>
    <link/><meta/><param/>
  </body>
</html>"""

_BOOLEANATTRS_HTML= """<html>
  <body>
  <tag selected="true"/>
  <tag checked="true"/>
  <tag compact="true"/>
  <tag declare="true"/>
  <tag defer="true"/>
  <tag disabled="true"/>
  <tag ismap="true"/>
  <tag multiple="true"/>
  <tag nohref="true"/>
  <tag noresize="true"/>
  <tag noshade="true"/>
  <tag nowrap="true"/>
  </body>
</html>"""

_ENTITIES_XHTML= r"""
<html>
<head></head>
<body>
  <!-- test entity references -->
  <p>&nbsp;</p>
</body>
</html>"""

_COMPLEX_XHTML = r"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:meld="http://www.plope.com/software/meld3"
      xmlns:bar="http://foo/bar">
  <head>
    <meta content="text/html; charset=ISO-8859-1" http-equiv="content-type" />
    <title meld:id="title">This will be escaped in html output: &amp;</title>
    <script>this won't be escaped in html output: &amp;</script>
    <script type="text/javascript">
            //<![CDATA[
              // this won't be escaped in html output
              function match(a,b) {
                 if (a < b && a > 0) then { return 1 }
                }
             //]]>
    </script>
    <style>this won't be escaped in html output: &amp;</style>
  </head>
  <!-- a comment -->
  <body>
    <div bar:baz="slab"/>
    <div meld:id="content_well">
      <form meld:id="form1" action="." method="POST">
      <img src="foo.gif"/>
      <table border="0" meld:id="table1">
        <tbody meld:id="tbody">
          <tr meld:id="tr" class="foo">
            <td meld:id="td1">Name</td>
            <td meld:id="td2">Description</td>
          </tr>
        </tbody>
      </table>
      <input type="submit" name="submit" value=" Next "/>
      </form>
    </div>
  </body>
</html>"""

class MeldAPITests(unittest.TestCase):
    def _makeElement(self, string):
        data = StringIO(string)
        from meld3 import parse
        return parse(data)

    def test_findmeld(self):
        root = self._makeElement(_SIMPLE_XML)
        item = root.findmeld('item')
        self.assertEqual(item.tag, 'item')
        name = root.findmeld('name')
        self.assertEqual(name.text, 'Name')

    def test_findmeld_default(self):
        root = self._makeElement(_SIMPLE_XML)
        item = root.findmeld('item')
        self.assertEqual(item.tag, 'item')
        unknown = root.findmeld('unknown', 'foo')
        self.assertEqual(unknown, 'foo')
        self.assertEqual(root.findmeld('unknown'), None)

    def test_repeat_nochild(self):
        root = self._makeElement(_SIMPLE_XML)
        item = root.findmeld('item')
        self.assertEqual(item.tag, 'item')
        data = [{'name':'Jeff Buckley', 'description':'ethereal'},
                {'name':'Slipknot', 'description':'heavy'}]
        for element, d in item.repeat(data):
            element.findmeld('name').text = d['name']
            element.findmeld('description').text = d['description']
        self.assertEqual(item[0].text, 'Jeff Buckley')
        self.assertEqual(item[1].text, 'ethereal')

    def test_repeat_child(self):
        root = self._makeElement(_SIMPLE_XML)
        list = root.findmeld('list')
        self.assertEqual(list.tag, 'list')
        data = [{'name':'Jeff Buckley', 'description':'ethereal'},
                {'name':'Slipknot', 'description':'heavy'}]
        for element, d in list.repeat(data, 'item'):
            element.findmeld('name').text = d['name']
            element.findmeld('description').text = d['description']
        self.assertEqual(list[0][0].text, 'Jeff Buckley')
        self.assertEqual(list[0][1].text, 'ethereal')
        self.assertEqual(list[1][0].text, 'Slipknot')
        self.assertEqual(list[1][1].text, 'heavy')

    def test_mod(self):
        root = self._makeElement(_SIMPLE_XML)
        root % {'description':'foo', 'name':'bar'}
        name = root.findmeld('name')
        self.assertEqual(name.text, 'bar')
        desc = root.findmeld('description')
        self.assertEqual(desc.text, 'foo')

    def test_replace_removes_all_elements(self):
        from meld3 import Replace
        root = self._makeElement(_SIMPLE_XML)
        L = root.findmeld('list')
        L.replace('this is a textual replacement')
        R = root[0]
        self.assertEqual(R.tag, Replace)
        self.assertEqual(len(root.getchildren()), 1)

    def test_replace_replaces_the_right_element(self):
        from meld3 import Replace
        root = self._makeElement(_SIMPLE_XML)
        D = root.findmeld('description')
        D.replace('this is a textual replacement')
        self.assertEqual(len(root.getchildren()), 1)
        L = root[0]
        self.assertEqual(L.tag, 'list')
        self.assertEqual(len(L.getchildren()), 1)
        I = L[0]
        self.assertEqual(I.tag, 'item')
        self.assertEqual(len(I.getchildren()), 2)
        N = I[0]
        self.assertEqual(N.tag, 'name')
        self.assertEqual(len(N.getchildren()), 0)
        D = I[1]
        self.assertEqual(D.tag, Replace)
        self.assertEqual(D.text, 'this is a textual replacement')
        self.assertEqual(len(D.getchildren()), 0)
        self.assertEqual(D.structure, False)

    def test_content(self):
        from meld3 import Replace
        root = self._makeElement(_SIMPLE_XML)
        D = root.findmeld('description')
        D.content('this is a textual replacement')
        self.assertEqual(len(root.getchildren()), 1)
        L = root[0]
        self.assertEqual(L.tag, 'list')
        self.assertEqual(len(L.getchildren()), 1)
        I = L[0]
        self.assertEqual(I.tag, 'item')
        self.assertEqual(len(I.getchildren()), 2)
        N = I[0]
        self.assertEqual(N.tag, 'name')
        self.assertEqual(len(N.getchildren()), 0)
        D = I[1]
        self.assertEqual(D.tag, 'description')
        self.assertEqual(D.text, None)
        self.assertEqual(len(D.getchildren()), 1)
        T = D[0]
        self.assertEqual(T.tag, Replace)
        self.assertEqual(T.text, 'this is a textual replacement')
        self.assertEqual(T.structure, False)

    def test_attributes(self):
        root = self._makeElement(_COMPLEX_XHTML)
        D = root.findmeld('form1')
        D.attributes(foo='bar', baz='1', g='2', action='#')
        self.assertEqual(D.attrib, {
            'foo':'bar', 'baz':'1', 'g':'2',
            'method':'POST', 'action':'#',
            '{http://www.plope.com/software/meld3}id': 'form1'})

    def test_attributes_nonstringtype_raises(self):
        root = self._makeElement('<root></root>')
        self.assertRaises(ValueError, root.attributes, foo=1)

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
        comment = root[1]
        body = root[2]
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

        img = form[0]
        self.assertEqual(img.tag, xhtml_ns % 'img')
        self.assertEqual(img.parent, form)

        table = form[1]
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

    def test_dupe_meldids_fails(self):
        meld_ns = "http://www.plope.com/software/meld3"
        repeated = ('<html xmlns:meld="%s" meld:id="repeat">'
                    '<body meld:id="repeat"/></html>' % meld_ns)
        from meld3 import parse
        data = StringIO(repeated)
        self.assertRaises(ValueError, parse, data)

    def test_nonxhtml_parsing(self):
        from meld3 import parse
        from meld3 import _MELD_ID
        data = StringIO(_SIMPLE_XML)
        root = parse(data, xhtml=False)
        self.assertEqual(root.tag, 'root')
        self.assertEqual(root.parent, None)
        from xml.parsers import expat
        self.assertRaises(expat.error, parse, StringIO(_ENTITIES_XHTML),
                          False)

class WriterTests(unittest.TestCase):
    def _parse(self, xml):
        from meld3 import parse
        data = StringIO(xml)
        root = parse(data)
        return root

    def _write(self, fn, **kw):
        out = StringIO()
        fn(out, **kw)
        out.seek(0)
        actual = out.read()
        return actual

    def _write_xml(self, node, **kw):
        return self._write(node.write_xml, **kw)

    def _write_html(self, node, **kw):
        return self._write(node.write_html, **kw)

    def _write_xhtml(self, node, **kw):
        return self._write(node.write_xhtml, **kw)

    def assertNormalizedXMLEqual(self, a, b):
        a = normalize_xml(a)
        b = normalize_xml(b)
        self.assertEqual(a, b)

    def assertNormalizedHTMLEqual(self, a, b):
        a = normalize_html(a)
        b = normalize_html(b)
        self.assertEqual(a, b)

    def test_write_simple_xml(self):
        root = self._parse(_SIMPLE_XML)
        actual = self._write_xml(root)
        expected = """<?xml version="1.0"?><root>
  <list>
    <item>
       <name>Name</name>
       <description>Description</description>
    </item>
  </list>
</root>"""
        self.assertNormalizedXMLEqual(actual, expected)

        for el, data in root.findmeld('item').repeat(((1,2),)):
            el.findmeld('name').text = str(data[0])
            el.findmeld('description').text = str(data[1])
        actual = self._write_xml(root)
        expected = """<?xml version="1.0"?><root>
  <list>
    <item>
       <name>1</name>
       <description>2</description>
    </item>
  </list>
</root>"""
        self.assertNormalizedXMLEqual(actual, expected)

    def test_write_simple_xhtml(self):
        root = self._parse(_SIMPLE_XHTML)
        actual = self._write_xhtml(root)
        expected = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html:html xmlns:html="http://www.w3.org/1999/xhtml">
   <html:body>Hello!</html:body>
</html:html>"""
        self.assertNormalizedXMLEqual(actual, expected)

    def test_write_simple_xhtml_as_html(self):
        root = self._parse(_SIMPLE_XHTML)
        actual = self._write_html(root)
        expected = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
   <body>Hello!</body>
</html>"""
        self.assertNormalizedHTMLEqual(actual, expected)

    def test_write_complex_xhtml_as_html(self):
        root = self._parse(_COMPLEX_XHTML)
        actual = self._write_html(root)
        expected = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
  <head>
    <meta content="text/html; charset=ISO-8859-1" http-equiv="content-type">
    <title>This will be escaped in html output: &amp;</title>
    <script>this won't be escaped in html output: &</script>
    <script type="text/javascript">
            //
              // this won't be escaped in html output
              function match(a,b) {
                 if (a < b && a > 0) then { return 1 }
                }
             //
    </script>
    <style>this won't be escaped in html output: &</style>
  </head>
  <!-- a comment -->
  <body>
    <div></div>
    <div>
      <form action="." method="POST">
      <img src="foo.gif">
      <table border="0">
        <tbody>
          <tr class="foo">
            <td>Name</td>
            <td>Description</td>
          </tr>
        </tbody>
      </table>
      <input name="submit" type="submit" value=" Next ">
      </form>
    </div>
  </body>
</html>"""
          
        self.assertNormalizedHTMLEqual(actual, expected)

    def test_write_complex_xhtml_as_xhtml(self):
        # I'm not entirely sure if the cdata "script" quoting in this
        # test is entirely correct for XHTML.  Ryan Tomayko suggests
        # that escaped entities are handled properly in script tags by
        # XML-aware browsers at
        # http://sourceforge.net/mailarchive/message.php?msg_id=10835582
        # but I haven't tested it at all.  ZPT does not seem to do
        # this; it outputs unescaped data.
        root = self._parse(_COMPLEX_XHTML)
        actual = self._write_xhtml(root)
        expected = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html:html xmlns:html="http://www.w3.org/1999/xhtml">
  <html:head>
    <html:meta content="text/html; charset=ISO-8859-1" http-equiv="content-type" />
    <html:title>This will be escaped in html output: &amp;</html:title>
    <html:script>this won't be escaped in html output: &amp;</html:script>
    <html:script type="text/javascript">
            //
              // this won't be escaped in html output
              function match(a,b) {
                 if (a &lt; b &amp;&amp; a &gt; 0) then { return 1 }
              }
           //
    </html:script>
    <html:style>this won't be escaped in html output: &amp;</html:style>
  </html:head>
  <!-- a comment -->
  <html:body>
    <html:div ns1:baz="slab" xmlns:ns1="http://foo/bar" />
    <html:div>
      <html:form action="." method="POST">
      <html:img src="foo.gif" />
      <html:table border="0">
        <html:tbody>
          <html:tr class="foo">
            <html:td>Name</html:td>
             <html:td>Description</html:td>
           </html:tr>
         </html:tbody>
      </html:table>
      <html:input name="submit" type="submit" value=" Next " />
      </html:form>
    </html:div>
  </html:body>
</html:html>"""
        self.assertNormalizedXMLEqual(actual, expected)

    def test_write_emptytags_html(self):
        root = self._parse(_EMPTYTAGS_HTML)
        actual = self._write_html(root)
        expected = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
  <body>
    <area><base><basefont><br><col><frame><hr><img><input><isindex>
    <link><meta><param>
  </body>
</html>"""
        self.assertEqual(actual, expected)
        
    def test_write_booleanattrs_html(self):
        root = self._parse(_BOOLEANATTRS_HTML)
        actual = self._write_html(root)
        expected = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
  <body>
  <tag selected></tag>
  <tag checked></tag>
  <tag compact></tag>
  <tag declare></tag>
  <tag defer></tag>
  <tag disabled></tag>
  <tag ismap></tag>
  <tag multiple></tag>
  <tag nohref></tag>
  <tag noresize></tag>
  <tag noshade></tag>
  <tag nowrap></tag>
  </body>
</html>"""
        self.assertNormalizedHTMLEqual(actual, expected)

    def test_write_simple_xhtml_pipeline(self):
        root = self._parse(_SIMPLE_XHTML)
        actual = self._write_xhtml(root, pipeline=True)
        expected = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html:html xmlns:html="http://www.w3.org/1999/xhtml">
        <html:body ns1:id="body" xmlns:ns1="http://www.plope.com/software/meld3">Hello!</html:body>
        </html:html>"""
        self.assertNormalizedXMLEqual(actual, expected)

    def test_write_simple_xml_pipeline(self):
        root = self._parse(_SIMPLE_XML)
        actual = self._write_xml(root, pipeline=True)
        expected = """<?xml version="1.0"?><root>
  <list ns0:id="list" xmlns:ns0="http://www.plope.com/software/meld3">
    <item ns0:id="item">
       <name ns0:id="name">Name</name>
       <description ns0:id="description">Description</description>
    </item>
  </list>
</root>"""
        self.assertNormalizedXMLEqual(actual, expected)

    def test_write_simple_xml_override_encoding(self):
        root = self._parse(_SIMPLE_XML)
        from meld3 import doctype
        actual = self._write_xml(root, encoding="latin-1")
        expected = """<?xml version="1.0" encoding="latin-1"?><root>
  <list>
    <item>
       <name>Name</name>
       <description>Description</description>
    </item>
  </list>
</root>"""
        self.assertNormalizedXMLEqual(actual, expected)

        
    def test_write_simple_xml_as_fragment(self):
        root = self._parse(_SIMPLE_XML)
        from meld3 import doctype
        actual = self._write_xml(root, fragment=True)
        expected = """<root>
  <list>
    <item>
       <name>Name</name>
       <description>Description</description>
    </item>
  </list>
</root>"""
        self.assertNormalizedXMLEqual(actual, expected)
        
    def test_write_simple_xml_with_doctype(self):
        root = self._parse(_SIMPLE_XML)
        from meld3 import doctype
        actual = self._write_xml(root, doctype=doctype.xhtml)
        expected = """<?xml version="1.0"?>
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><root>
  <list>
    <item>
       <name>Name</name>
       <description>Description</description>
    </item>
  </list>
</root>"""
        self.assertNormalizedXMLEqual(actual, expected)

    def test_write_simple_xml_doctype_nodeclaration(self):
        root = self._parse(_SIMPLE_XML)
        from meld3 import doctype
        actual = self._write_xml(root, declaration=False,
                                 doctype=doctype.xhtml)
        expected = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><root>
  <list>
    <item>
       <name>Name</name>
       <description>Description</description>
    </item>
  </list>
</root>"""
        self.assertNormalizedXMLEqual(actual, expected)

    def test_write_simple_xml_fragment_kills_doctype_and_declaration(self):
        root = self._parse(_SIMPLE_XML)
        from meld3 import doctype
        actual = self._write_xml(root, declaration=True,
                                 doctype=doctype.xhtml, fragment=True)
        expected = """<root>
  <list>
    <item>
       <name>Name</name>
       <description>Description</description>
    </item>
  </list>
</root>"""
        self.assertNormalizedXMLEqual(actual, expected)

    def test_write_simple_xhtml_override_encoding(self):
        root = self._parse(_SIMPLE_XHTML)
        from meld3 import doctype
        actual = self._write_xhtml(root, encoding="latin-1", declaration=True)
        expected = """<?xml version="1.0" encoding="latin-1"?>
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html:html xmlns:html="http://www.w3.org/1999/xhtml"><html:body>Hello!</html:body></html:html>"""
        self.assertNormalizedXMLEqual(actual, expected)

    def test_write_simple_xhtml_as_fragment(self):
        root = self._parse(_SIMPLE_XHTML)
        from meld3 import doctype
        actual = self._write_xhtml(root, fragment=True)
        expected = """<html:html xmlns:html="http://www.w3.org/1999/xhtml"><html:body>Hello!</html:body></html:html>"""
        self.assertNormalizedXMLEqual(actual, expected)
        
    def test_write_simple_xhtml_with_doctype(self):
        root = self._parse(_SIMPLE_XHTML)
        from meld3 import doctype
        actual = self._write_xhtml(root, doctype=doctype.xhtml)
        expected = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html:html xmlns:html="http://www.w3.org/1999/xhtml"><html:body>Hello!</html:body></html:html>"""
        self.assertNormalizedXMLEqual(actual, expected)

    def test_write_simple_xhtml_doctype_nodeclaration(self):
        root = self._parse(_SIMPLE_XHTML)
        from meld3 import doctype
        actual = self._write_xhtml(root, declaration=False,
                                 doctype=doctype.xhtml)
        expected = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html:html xmlns:html="http://www.w3.org/1999/xhtml"><html:body>Hello!</html:body></html:html>"""
        self.assertNormalizedXMLEqual(actual, expected)

    def test_write_simple_xhtml_fragment_kills_doctype_and_declaration(self):
        root = self._parse(_SIMPLE_XHTML)
        from meld3 import doctype
        actual = self._write_xhtml(root, declaration=True,
                                 doctype=doctype.xhtml, fragment=True)
        expected = """<html:html xmlns:html="http://www.w3.org/1999/xhtml"><html:body>Hello!</html:body></html:html>"""
        self.assertNormalizedXMLEqual(actual, expected)

    def test_write_simple_xhtml_as_html_fragment(self):
        root = self._parse(_SIMPLE_XHTML)
        from meld3 import doctype
        actual = self._write_html(root, fragment=True)
        expected = """<html><body>Hello!</body></html>"""
        self.assertNormalizedXMLEqual(actual, expected)
        
    def test_write_simple_xhtml_with_doctype_as_html(self):
        root = self._parse(_SIMPLE_XHTML)
        actual = self._write_html(root)
        expected = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html><body>Hello!</body></html>"""
        self.assertNormalizedXMLEqual(actual, expected)

    def test_write_simple_xhtml_as_html_new_doctype(self):
        root = self._parse(_SIMPLE_XHTML)
        from meld3 import doctype
        actual = self._write_html(root, doctype=doctype.html_strict)
        expected = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html><body>Hello!</body></html>"""
        self.assertNormalizedXMLEqual(actual, expected)

    def test_write_entities_xhtml_no_doctype(self):
        root = self._parse(_ENTITIES_XHTML)
        # this will be considered an XHTML document by default; we needn't
        # declare a doctype
        actual = self._write_xhtml(root)
        expected =r"""<html>
<head></head>
<body>
  <!-- test entity references -->
  <p>&nbsp;</p>
</body>
</html>"""

    def test_write_entities_xhtml_with_doctype(self):
        dt = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
        root = self._parse(dt + _ENTITIES_XHTML)
        actual = self._write_xhtml(root)
        expected =r"""<html>
<head></head>
<body>
  <!-- test entity references -->
  <p>&nbsp;</p>
</body>
</html>"""

    def test_unknown_entity(self):
        from xml.parsers import expat
        self.assertRaises(expat.error, self._parse,
                          '<html><head></head><body>&fleeb;</body></html>')

    def test_content_nostructure(self):
        root = self._parse(_SIMPLE_XML)
        D = root.findmeld('description')
        D.content('description &<foo> <bar>', structure=False)
        actual = self._write_xml(root)
        expected = """<?xml version="1.0"?>
        <root>
        <list>
        <item>
        <name>Name</name>
          <description>description &amp;&lt;foo&gt; &lt;bar&gt;</description>
        </item>
        </list>
        </root>"""
        self.assertNormalizedXMLEqual(actual, expected)
        
    def test_content_structure(self):
        root = self._parse(_SIMPLE_XML)
        D = root.findmeld('description')
        D.content('description &<foo> <bar>', structure=True)
        actual = self._write_xml(root)
        expected = """<?xml version="1.0"?>
        <root>
        <list>
        <item>
        <name>Name</name>
          <description>description &<foo> <bar></description>
        </item>
        </list>
        </root>"""
        self.assertNormalizedXMLEqual(actual, expected)

    def test_replace_nostructure(self):
        root = self._parse(_SIMPLE_XML)
        D = root.findmeld('description')
        D.replace('description &<foo> <bar>', structure=False)
        actual = self._write_xml(root)
        expected = """<?xml version="1.0"?>
        <root>
        <list>
        <item>
        <name>Name</name>
          description &amp;&lt;foo&gt; &lt;bar&gt;
        </item>
        </list>
        </root>"""
        self.assertNormalizedXMLEqual(actual, expected)
        
    def test_replace_structure(self):
        root = self._parse(_SIMPLE_XML)
        D = root.findmeld('description')
        D.replace('description &<foo> <bar>', structure=True)
        actual = self._write_xml(root)
        expected = """<?xml version="1.0"?>
        <root>
        <list>
        <item>
        <name>Name</name>
          description &<foo> <bar>
        </item>
        </list>
        </root>"""
        self.assertNormalizedXMLEqual(actual, expected)

def normalize_html(s):
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"/>", ">", s)
    return s

def normalize_xml(s):
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"(?s)\s+<", "<", s)
    s = re.sub(r"(?s)>\s+", ">", s)
    return s

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest( unittest.makeSuite( MeldAPITests ) )
    suite.addTest( unittest.makeSuite( MeldElementInterfaceTests ) )
    suite.addTest( unittest.makeSuite( ParserTests ) )
    suite.addTest( unittest.makeSuite( WriterTests) )
    return suite

def main():
    unittest.main(defaultTest='test_suite')

if __name__ == '__main__':
    main()
    
