meld3

Overview

  meld3 is an XML templating system for Python 2.3+ which keeps
  template markup and dynamic rendering logic separate from one
  another.  See http://www.entrian.com/PyMeld for a treatise on the
  benefits of this pattern.

  meld3 is a variation of Paul Winkler's Meld2, which is itself a
  variation of Richie Hindle's PyMeld.

  meld3 uses Frederik Lundh's ElementTree library.

Requirements

  Python 2.3+

  ElementTree 1.2+ (http://effbot.org/downloads/#elementtree)

Differences from PyMeld

  - templates created for use under PyMeld will not work under meld3
    due to differences in meld tag identification (meld3's id
    attributes are in a nondefault XML namespace, PyMeld's are not).

  - The "id" attribute used to mark up is in the a separate namespace
    (aka. xmlns="http://www.plope.com/software/meld3").  So instead of
    marking up a tag like this::

      <div id="thediv"></div>

    meld3 requires that you qualify the "id" attribute with a "meld"
    namespace element, like this::

      <div meld:id="thediv"></div>

    As per the XML namespace specification, the "meld" name is
    completely optional, and must only represent the
    "http://www.plope.com/software/meld3" namespace identifier, so
    this input is just as valid::

      <div xmlns:foo="http://www.plope.com/software/meld3" foo:id="thediv"/>

  - Input documents must be valid XML or XHTML and must include the meld 
    namespace declaration on the root element, eg.:

      <html xmlns:meld="http://www.plope.com/software/meld3">...</html>

  - Output documents do not include any meld namespace attributes.

  - Output is not performed in "html mode" (yet), so some elements
    which are conventionally "autoclosed" by PyMeld to support older
    browsers are not closed by meld3.  For example, if you create an
    empty textarea element in PyMeld, it will likely be rendered as::

       <textarea></textarea>

    In meld3 it is rendered 
    as::

       <textarea/>

    This is arguably a bug given the fact that older browsers may
    choke on this output.

    Another side effect of not having the ability to specify html
    output is that elements in the output may be qualified with the
    'html' namespace, which may also confuse older browsers.

  - meld3 elements are instances of ElementTree elements and support
    the ElementTree element API (http://effbot.org/zone/element.htm)
    instead of the PyMeld node API.  The ElementTree Element API has
    been extended by meld3 to perform various functions specific to
    meld3.

  - meld3 elements do not support the __mod__ (%) modifier (yet).

  - meld3 elements support a Meld2-style "repeat" method.

Examples

  An example script which uses meld3 to dynamicize an XHTML
  template::

    xml = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml"
          xmlns:meld="http://www.plope.com/software/meld3"
          xmlns:bar="http://foo/bar">
      <head>
        <meta content="text/html; charset=ISO-8859-1" http-equiv="content-type" />
        <title meld:id="title">This is the title</title>
      </head>
      <body>
        <div meld:id="content_well">
          <form meld:id="form1" action="." method="POST">
          <table border="0" meld:id="table1">
            <tbody meld:id="tbody">
              <tr>
                <th>Name</th>
                <th>Description</th>
              </tr>
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
    from meld3 import parse
    from meld3 import write
    from StringIO import StringIO
    import sys

    root = parse(StringIO(xml))
    root.meld['title'].text = 'My document'
    root.meld['form1'].attrib['action'] = './handler'
    data = (
        {'name':'Boys',
         'description':'Ugly'},
        {'name':'Girls',
         'description':'Pretty'},
        )
    iterator = root.meld['tr'].meld.repeat(data)
    for element, item in iterator:
        element.meld['td1'].text = item['name']
        element.meld['td2'].text = item['description']
    write(root, sys.stdout)


  The output of this script
  is::

    <html:html xmlns:html="http://www.w3.org/1999/xhtml">
      <html:head>
        <html:meta content="text/html; charset=ISO-8859-1" http-equiv="content-type" />
        <html:title>My document</html:title>
      </html:head>
      <html:body>
        <html:div>
          <html:form action="./handler" method="POST">
          <html:table border="0">
            <html:tbody>
              <html:tr>
                <html:th>Name</html:th>
                <html:th>Description</html:th>
              </html:tr>
              <html:tr class="foo">
                <html:td>Boys</html:td>
                <html:td>Ugly</html:td>
              </html:tr>
            <html:tr class="foo">
                <html:td>Girls</html:td>
                <html:td>Pretty</html:td>
              </html:tr>
            </html:tbody>
          </html:table>
          </html:form>
        </html:div>
      </html:body>
    </html:html>      

Extensions to the ElementTree Element API

  Meld elements support all of the ElementTree API.

  Meld elements support a "clone" method which clones a node and all
  of its children via a "deepcopy".

  Elements support a "meld" attribute, which is a helper that can be
  obtained by getting a hold of the "meld" attribute on any element,
  like so::

    element.meld

  The meld helper is an object that supports the following 
  methods::

    __getitem__(name) -- searches the this element and its children for 
      elements that have a "meld:id" attribute that matches "name".

    get(name, default=None) -- searches the this element and its children
      for elements that have a 'meld:id' attribute that matches
      "name"; if no element can be found, return the default.

    repeat(iterable, childname=None) -- repeats an element with values
      from an iterable.  If 'childname' is not None, repeat the
      element from which the meld helper was obtained, otherwise find
      the child element with a 'meld:id' matching 'childname' and
      repeat that.  The element is repeated within its parent element.
      This method returns an iterable; the value of each iteration is
      a two-sequence in the form (newelement, data).  'newelement' is
      a clone of the template element (including clones of its
      children) which has already been seated in its parent element in
      the template. 'data' is a value from the passed in iterable.
      Changing 'newelement' (typically based on values from 'data')
      mutates the element "in place".

To Do

  The API is by no means fixed in stone.  It is apt to change at any
  time; this is really a very alpha release.

  This implementation depends on classes internal to ElementTree and
  hasn't been tested with cElementTree or lxml, and almost certainly
  won't work with either due to this.

  Obviously getting rid of extraneous output in the form of namespaced
  elements would be nice.

Reporting Bugs and Requesting Features

  Please visit http://www.plope.com/software/collector to report bugs
  and request features.

Have fun!

- Chris McDonough (chrism@plope.com)
