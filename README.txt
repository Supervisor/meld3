meld3

Overview

  meld3 is an XML templating system for Python 2.3+ which keeps
  template markup and dynamic rendering logic separate from one
  another.  See http://www.entrian.com/PyMeld for a treatise on the
  benefits of this pattern.

  meld3 requires well-formed XML/XHTML input and can output
  well-formed XML/XHTML or HTML.

  meld3 is a variation of Paul Winkler's Meld2, which is itself a
  variation of Richie Hindle's PyMeld.

  meld3 uses Frederik Lundh's ElementTree library.

Requirements

  Python 2.3+

  ElementTree 1.2+ (http://effbot.org/downloads/#elementtree)

Differences from PyMeld

  - Templates created for use under PyMeld will not work under meld3
    due to differences in meld tag identification (meld3's id
    attributes are in a nondefault XML namespace, PyMeld's are not).

  - Input documents must be valid XML or XHTML and must include the
    meld3 namespace declaration (conventionally on the root element).
    For example, '<html
    xmlns:meld="http://www.plope.com/software/meld3">...</html>'

  - The "id" attribute used to mark up is in the a separate namespace
    (aka. xmlns="http://www.plope.com/software/meld3").  So instead of
    marking up a tag like this: '<div id="thediv"></div>', meld3
    requires that you qualify the "id" attribute with a "meld"
    namespace element, like this: '<div meld:id="thediv"></div>'.  As
    per the XML namespace specification, the "meld" name is completely
    optional, and must only represent the
    "http://www.plope.com/software/meld3" namespace identifier, so
    '<div xmlns:foo="http://www.plope.com/software/meld3"
    foo:id="thediv"/>' is just as valid as as '<div
    meld:id="thediv"/>'

  - Output documents by default do not include any meld3 namespace id
    attributes.  If you wish to preserve meld3 ids (for instance, in
    order to do pipelining of meld3 templates), you can preserve meld
    ids by passing a "pipeline" option to a "write" function
    (e.g. write_xml, wwrite_xhtml).

  - Output is by default performed in "XML mode".  This is unlike
    "HTML mode" because it doesn't "autoclose" most tags with a
    separate ending tag nor does it strip HTML-related namespace
    declarations.  For example, if you create an empty textarea
    element and output it in XML mode the output will be rendered
    <'textarea/>'.  In HTML mode, it will be rendered as
    '<textarea></textarea>'.  You can decide how you wish to render
    your templates by passing an 'html' flag to the meld 'writer'.

  - meld3 elements are instances of ElementTree elements and support
    the ElementTree element API (http://effbot.org/zone/element.htm)
    instead of the PyMeld node API.  The ElementTree Element API has
    been extended by meld3 to perform various functions specific to
    meld3.

  - meld3 elements do not support the __mod__ method with a sequence
    argument; they do support the __mod__ method with a dictionary
    argument, however.

  - meld3 elements support a Meld2-style "repeat" method.

Examples

  A valid example meld3 template is as
  follows::

    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml"
          xmlns:meld="http://www.plope.com/software/meld3"
          xmlns:bar="http://foo/bar">
      <head>
        <meta content="text/html; charset=ISO-8859-1" http-equiv="content-type" />
        <title meld:id="title">This is the title</title>
      </head> 
      <body>
        <div/> <!-- empty tag -->
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
          <input type="submit" name="next" value=" Next "/>
          </form>
        </div>
      </body>
    </html>

  A script which parses the above template and does some
  transformations is below.  Consider the variable "xml" below bound
  to the string above::

    from meld3 import parse
    from StringIO import StringIO

    root = parse(StringIO(xml))
    root.findmeld('title').text = 'My document'
    root.findmeld('form1').attrib['action'] = './handler'
    data = (
        {'name':'Boys',
         'description':'Ugly'},
        {'name':'Girls',
         'description':'Pretty'},
        )
    iterator = root.findmeld('tr').repeat(data)
    for element, item in iterator:
        element.findmeld('td1').text = item['name']
        element.findmeld('td2').text = item['description']

  To output the result of the transformations to stdout as XML, we use
  the 'write' method of any element.  Below, we use the root element
  (consider it bound to the value of "root" in the above script)::

    import sys
    root.write_xml(sys.stdout)
    ...
    <html:html xmlns:html="http://www.w3.org/1999/xhtml">
      <html:head>
        <html:meta content="text/html; charset=ISO-8859-1" http-equiv="content-type" />
        <html:title>My document</html:title>
      </html:head>
      <html:body>
        <html:div /> <!-- empty tag -->
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
            <html:tr class="foo"><html:td>Girls</html:td><html:td>Pretty</html:td></html:tr></html:tbody>
          </html:table>
          </html:form>
        </html:div>
      </html:body>
    </html:html>

  We can also output text in HTML mode, This serializes the node and
  its children to HTML.  This feature was inspired by and based on
  code Ian Bicking.  By default, the serialization will include a
  'loose' HTML DTD doctype (this can be overridden with the doctype=
  argument).  "Empty" shortcut elements such as '<div/>' will be
  converted to a balanced pair of tags e.g. '<div></div>'.  But some
  HTML tags (defined as per the HTML 4 spec as area, base, basefont,
  br, col, frame, hr, img, input, isindex, link, meta, param) will not
  be followed with a balanced ending tag; only the beginning tag will
  be output.  Additionally, "boolean" tag attributes will not be
  followed with any value.  The "boolean" tags are selected, checked,
  compact, declare, defer, disabled, ismap, multiple, nohref,
  noresize, noshade, and nowrap.  So the XML input '<input
  type="checkbox" checked="checked"/>' will be turned into '<input
  type="checkbox" checked>'.  Additionally, 'script' and 'style' tags
  will not have their contents escaped (e.g. so "&" will not be turned
  into '&amp;' when it's iside the textual content of a script or style
  tag.)::

    import sys
    root.write_html(sys.stdout)
    ...
    <html>
      <head>
        <meta content="text/html; charset=ISO-8859-1" http-equiv="content-type"></meta>
        <title>My document</title>
      </head>
      <body>
        <div></div > <!-- empty tag -->
        <div>
          <form action="./handler" method="POST">
          <table border="0">
            <tbody>
              <tr>
                <th>Name</th>
                <th>Description</th>
              </tr>
              <tr class="foo">
                <td>Boys</td>
                <td>Ugly</td>
              </tr>
            <tr class="foo"><td>Girls</td><td>Pretty</td></tr></tbody>
          </table>
          </form>
        </div>
      </body>
    </html>

Element API

  meld3 elements support all of the ElementTree API.  Other
  meld-specific methods of elements are as follows::

    "clone(parent=None)": clones a node and all of its children via a
    recursive copy.  If parent is passed in, append the clone to the
    parent node.

    "findmeld(name, default=None)": searches the this element and its
    children for elements that have a 'meld:id' attribute that matches
    "name"; if no element can be found, return the default.

    "repeat(iterable, childname=None)": repeats an element with values
    from an iterable.  If 'childname' is not None, repeat the element on
    which repeat was called, otherwise find the child element with a
    'meld:id' matching 'childname' and repeat that.  The element is
    repeated within its parent element.  This method returns an
    iterable; the value of each iteration is a two-sequence in the form
    (newelement, data).  'newelement' is a clone of the template element
    (including clones of its children) which has already been seated in
    its parent element in the template. 'data' is a value from the
    passed in iterable.  Changing 'newelement' (typically based on
    values from 'data') mutates the element "in place".

    "__mod__(other)": Fill in the text values of meld nodes in this
    element and children recursively; only support dictionarylike
    "other" operand (sequence operand doesn't seem to make sense here).

    "write_xml(file, encoding=None, doctype=None, fragment=False, 
    declaration=True, pipeline=False)":
    Write XML to 'file' (which can be a filename or filelike object)
    encoding    -- encoding string (if None, 'utf-8' encoding is assumed)
                   Must be a recognizable Python encoding type.
    doctype     -- 3-tuple indicating name, pubid, system of doctype.
                   The default is to prevent a doctype from being emitted.
    fragment    -- True if a 'fragment' should be emitted for this node (no
                   declaration, no doctype).  This causes both the
                   'declaration' and 'doctype' parameters to become ignored
                   if provided.
    declaration -- emit an xml declaration header (including an encoding
                   if it's not None).  The default is to emit the
                   doctype.
    pipeline    -- preserve 'meld' namespace identifiers in output
                   for use in pipelining

    "write_xhtml(self, file, encoding=None, doctype=doctype.xhtml,
    fragment=False, declaration=False, pipeline=False)":
    Write XHTML to 'file' (which can be a filename or filelike object)

    encoding    -- encoding string (if None, 'utf-8' encoding is assumed)
                   Must be a recognizable Python encoding type.
    doctype     -- 3-tuple indicating name, pubid, system of doctype.
                   The default is the value of doctype.xhtml (XHTML
                   'loose').
    fragment    -- True if a 'fragment' should be emitted for this node (no
                   declaration, no doctype).  This causes both the
                   'declaration' and 'doctype' parameters to be ignored.
    declaration -- emit an xml declaration header (including an encoding
                   string if 'encoding' is not None)
    pipeline    -- preserve 'meld' namespace identifiers in output
                   for use in pipelining

    "write_html(self, file, encoding=None, doctype=doctype.html,fragment=False)":
    Write HTML to 'file' (which can be a filename or filelike object)
    encoding    -- encoding string (if None, 'utf-8' encoding is assumed).
                   Unlike XML output, this is not used in a declaration,
                   but it is used to do actual character encoding during
                   output.  Must be a recognizable Python encoding type.
    doctype     -- 3-tuple indicating name, pubid, system of doctype.
                   The default is the value of doctype.html (HTML 4.0
                   'loose')
    fragment    -- True if a "fragment" should be omitted (no doctype).
                   This overrides any provided "doctype" parameter if
                   provided.
    Namespace'd elements and attributes have their namespaces removed
    during output when writing HTML, so pipelining cannot be performed.
    HTML is not valid XML, so an XML declaration header is never emitted.

    In general: For all output methods, comments are preserved in
    output.  They are also present in the ElementTree node tree (as
    Comment elements), so beware. Processing instructions (e.g. <?xml
    version="1.0">) are completely thrown away at parse time and do
    not exist anywhere in the element tree or in the output (use the
    declaration= parameter to emit a declaration processing
    instruction).

Parsing API

  All source documents are turned into element trees using the "parse"
  function (demonstrated in examples above).

  HTML entities can now be parsed properly (magically) when a DOCTYPE
  is not supplied in the source of the XML passed to 'parse'.  If your
  source document does not contain a DOCTYPE declaration, the DOCTYPE
  is set to 'loose' XHTML 'by magic'.  If your source document does
  contain a DOCTYPE declaration, the existing DOCTYPE is used (and
  HTML entities thus may or may not work as a result, depending on the
  DOCTYPE).  To prevent this behavior, pass a false value to the
  xhtml= parameter of the 'parse' function.  This in no way effects
  output, which is independent of parsing.  This does not imply that
  any *non*-HTML entity can be parsed in the input stream under any
  circumstance without having it defined it in your source document.

  Using duplicate meld identifiers on separate elements in the source
  document causes a ValueError to be raised at parse time.

To Do

  The API is by no means fixed in stone.  It is apt to change at any
  time.

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
