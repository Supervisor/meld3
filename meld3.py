import htmlentitydefs
import re
import types

from elementtree.ElementTree import _ElementInterface
from elementtree.ElementTree import TreeBuilder
from elementtree.ElementTree import XMLTreeBuilder
from elementtree.ElementTree import Comment
from elementtree.ElementTree import ProcessingInstruction
from elementtree.ElementTree import QName
from elementtree.ElementTree import _raise_serialization_error
from elementtree.ElementTree import _escape_cdata
from elementtree.ElementTree import _escape_attrib
from elementtree.ElementTree import _encode
from elementtree.ElementTree import _namespace_map
from elementtree.ElementTree import fixtag
from elementtree.ElementTree import parse as et_parse

_MELD_PREFIX = '{http://www.plope.com/software/meld3}'
_MELD_LOCAL = 'id'
_MELD_ID = '%s%s' % (_MELD_PREFIX, _MELD_LOCAL)
_XHTML_PREFIX = '{http://www.w3.org/1999/xhtml}'

_marker = []

class doctype:
    # lookup table for ease of use in external code
    html_strict  = ('HTML', '-//W3C//DTD HTML 4.01//EN',
                    'http://www.w3.org/TR/html4/strict.dtd')
    html         = ('HTML', '-//W3C//DTD HTML 4.01 Transitional//EN',
                   'http://www.w3.org/TR/html4/loose.dtd')
    xhtml_strict = ('html', '-//W3C//DTD XHTML 1.0 Strict//EN',
                    'http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd')
    xhtml        = ('html', '-//W3C//DTD XHTML 1.0 Transitional//EN',
                    'http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd')

class _MeldElementInterface(_ElementInterface):
    parent = None

    # overrides to support parent pointers
    def __setitem__(self, index, element):
        _ElementInterface.__setitem__(self, index, element)
        element.parent = self

    def __delitem__(self, index):
        element = self[index]
        element.parent = None # remove any potential circref
        _ElementInterface.__delitem__(self, index)
        
    def append(self, element):
        _ElementInterface.append(self, element)
        element.parent = self

    def insert(self, index, element):
        _ElementInterface.insert(self, index, element)
        element.parent = self

    # overrides to support subclassing (use correct factories/functions)
    def makeelement(self, tag, attrib):
        return _MeldElementInterface(tag, attrib)

    # meld-specific

    def parse(self, src, xhtml=True):
        """ Shortcut to parse module-scope function """
        return parse(src, xhtml)

    def __mod__(self, other):
        """ Fill in the text values of meld nodes in tree; only
        support dictionarylike operand (sequence operand doesn't seem
        to make sense here)"""
        for k in other:
            node = self.findmeld(k)
            if node is not None:
                node.text = other[k]

    def findmeld(self, name, default=_marker):
        """ Find a node in the tree that has a 'meld id' corresponding
        to 'name'. Iterate over all subnodes recursively looking for a
        node which matches.  If we can't find the node, return None."""
        # this could be faster if we indexed all the meld nodes in the
        # tree; we just walk the whole hierarchy now.
        iterator = self.getiterator()
        for element in iterator:
            val = element.attrib.get(_MELD_ID)
            if val == name:
                return element
        if default is _marker:
            return None
        return default

    def repeat(self, iterable, childname=None):
        """repeats an element with values from an iterable.  If
        'childname' is not None, repeat the element on which the
        repeat is called, otherwise find the child element with a
        'meld:id' matching 'childname' and repeat that.  The element
        is repeated within its parent element (nodes that are created
        as a result of a repeat share the same parent).  This method
        returns an iterable; the value of each iteration is a
        two-sequence in the form (newelement, data).  'newelement' is
        a clone of the template element (including clones of its
        children) which has already been seated in its parent element
        in the template. 'data' is a value from the passed in
        iterable.  Changing 'newelement' (typically based on values
        from 'data') mutates the element 'in place'."""
        if childname is None:
            element = self
        else:
            element = self.findmeld(childname)

        parent = element.parent
        first = True

        for thing in iterable:
            if first:
                yield element, thing
            else:
                clone = element.clone()
                parent.append(clone)
                yield clone, thing
            first = False

    # ZPT-alike methods
    def replace(self, text, structure=False):
        """ Replace this element with a Replace node in our parent with
        the text 'text' and return the index of our position in
        our parent.  If we have no parent, do nothing, and return None.
        Pass the 'structure' flag to the replace node so it can do the right
        thing at render time. """
        parent = self.parent
        i = self.remove()
        if i is not None:
            parent.insert(i, Replace(text, structure))
            return i

    def content(self, text, structure=False):
        """ Delete this node's children and append a Replace node that
        contains text.  Always return None.  Pass the 'structure' flag
        to the replace node so it can do the right thing at render
        time."""
        for child in self._children:
            child.parent = None # clean up potential circrefs
        self.text = None
        self._children = []
        self.append(Replace(text, structure))

    def attributes(self, **kw):
        """ Set attributes on this node. """
        for k, v in kw.items():
            # prevent this from getting to the parser if possible
            if not isinstance(k, types.StringTypes):
                raise ValueError, 'do not set non-stringtype as key: %s' % k
            if not isinstance(v, types.StringTypes):
                raise ValueError, 'do not set non-stringtype as val: %s' % v
            self.attrib[k] = kw[k]

    # output methods
    def write_xml(self, file, encoding=None, doctype=None,
                  fragment=False, declaration=True, pipeline=False):
        """ Write XML to 'file' (which can be a filename or filelike object)

        encoding    - encoding string (if None, 'utf-8' encoding is assumed)
                      Must be a recognizable Python encoding type.
        doctype     - 3-tuple indicating name, pubid, system of doctype.
                      The default is to prevent a doctype from being emitted.
        fragment    - True if a 'fragment' should be emitted for this node (no
                      declaration, no doctype).  This causes both the
                      'declaration' and 'doctype' parameters to become ignored
                      if provided.
        declaration - emit an xml declaration header (including an encoding
                      if it's not None).  The default is to emit the
                      doctype.
        pipeline    - preserve 'meld' namespace identifiers in output
                      for use in pipelining
        """
        if not hasattr(file, "write"):
            file = open(file, "wb")
        if not fragment:
            if declaration:
                _write_declaration(file, encoding)
            if doctype:
                _write_doctype(file, doctype)
        _write_xml(file, self, encoding, {}, pipeline)

    def write_html(self, file, encoding=None, doctype=doctype.html,
                   fragment=False):
        """ Write HTML to 'file' (which can be a filename or filelike object)

        encoding    - encoding string (if None, 'utf-8' encoding is assumed).
                      Unlike XML output, this is not used in a declaration,
                      but it is used to do actual character encoding during
                      output.  Must be a recognizable Python encoding type.
        doctype     - 3-tuple indicating name, pubid, system of doctype.
                      The default is the value of doctype.html (HTML 4.0
                      'loose')
        fragment    - True if a "fragment" should be omitted (no doctype).
                      This overrides any provided "doctype" parameter if
                      provided.

        Namespace'd elements and attributes have their namespaces removed
        during output when writing HTML, so pipelining cannot be performed.

        HTML is not valid XML, so an XML declaration header is never emitted.
        """
        if not hasattr(file, "write"):
            file = open(file, "wb")
        if not fragment:
            if doctype:
                _write_doctype(file, doctype)
        _write_html(file, self, encoding, {})

    def write_xhtml(self, file, encoding=None, doctype=doctype.xhtml,
                    fragment=False, declaration=False, pipeline=False):
        """ Write XHTML to 'file' (which can be a filename or filelike object)

        encoding    - encoding string (if None, 'utf-8' encoding is assumed)
                      Must be a recognizable Python encoding type.
        doctype     - 3-tuple indicating name, pubid, system of doctype.
                      The default is the value of doctype.xhtml (XHTML
                      'loose').
        fragment    - True if a 'fragment' should be emitted for this node (no
                      declaration, no doctype).  This causes both the
                      'declaration' and 'doctype' parameters to be ignored.
        declaration - emit an xml declaration header (including an encoding
                      string if 'encoding' is not None)
        pipeline    - preserve 'meld' namespace identifiers in output
                      for use in pipelining
        """
        if not hasattr(file, "write"):
            file = open(file, "wb")
        if not fragment:
            if declaration:
                _write_declaration(file, encoding)
            if doctype:
                _write_doctype(file, doctype)
        _write_xml(file, self, encoding, {}, pipeline, xhtml=True)
            
    def clone(self, parent=None):
        """ Create a clone of an element.  If parent is not None,
        append the element to the parent.  Recurse as necessary to create
        a deep clone of the element. """
        element = self.makeelement(self.tag, self.attrib.copy())
        if parent is not None:
            parent.append(element)
        for child in self.getchildren():
            child.clone(element)
        return element
    
    def remove(self):
        """ Remove ourselves from our parent node (de-parent) and return
        the index of the parent which was deleted. """
        i = self.parentindex()
        if i is not None:
            del self.parent[i]
            return i

    def parentindex(self):
        """ Return the parent node index in which we live """
        parent = self.parent
        if parent is not None:
            for i in range (len(parent)):
                if parent[i] is self:
                    return i

# replace element factory
def Replace(text, structure=False):
    element = _MeldElementInterface(Replace, {})
    element.text = text
    element.structure = structure
    return element

def MeldTreeBuilder():
    return TreeBuilder(element_factory=_MeldElementInterface)

class MeldParser(XMLTreeBuilder):

    """ A parser based on Fredrik's PIParser at
    http://effbot.org/zone/element-pi.htm.  It blithely ignores the
    case of a comment existing outside the root element and ignores
    processing instructions entirely.  We need to validate that there
    are no repeated meld id's in the source as well """
    
    def __init__(self, html=0, target=None):
        XMLTreeBuilder.__init__(self, html, target)
        # assumes ElementTree 1.2.X
        self._parser.CommentHandler = self.handle_comment
        self.meldids = {}

    def handle_comment(self, data):
        self._target.start(Comment, {})
        self._target.data(data)
        self._target.end(Comment)

    def _start(self, tag, attrib_in):
        for key in attrib_in:
            if '{' + key == _MELD_ID:
                meldid = attrib_in[key]
                if self.meldids.get(meldid):
                    raise ValueError, ('Repeated meld id "%s" in source' %
                                       meldid)
                self.meldids[meldid] = 1
        return XMLTreeBuilder._start(self, tag, attrib_in)

    def _start_list(self, tag, attrib_in):
        i = 0
        indexes = []
        for attrib in attrib_in:
            if '{' + attrib == _MELD_ID:
                meldid = attrib_in[i+1]
                if self.meldids.get(meldid):
                    raise ValueError, ('Repeated meld id "%s" in source' %
                                       meldid)
                self.meldids[meldid] = 1
        return XMLTreeBuilder._start_list(self, tag, attrib_in)

    def close(self):
        val = XMLTreeBuilder.close(self)
        self.meldids = {}
        return val

class XHTMLMeldParser(MeldParser):

    """ A tree builder that understands XHTML entities by default by
    including am XHTML 'loose' doctype in the stream used by the
    parser if the document doesn't declare a specific doctype.  Expat
    requires such a declaration if it is to resolve any entities, but
    it's convenient to not need to declare a doctype in source documents."""

    xhtml_doctype = '<!DOCTYPE %s PUBLIC "%s" "%s">\n' % doctype.xhtml
    xml_decl_re = re.compile(r'<\?xml .*?\?>')

    def __init__(self, html=0, target=None):
        MeldParser.__init__(self, html, target)
        self.entity = htmlentitydefs.entitydefs.copy()
        self.beginning = True

    def feed(self, data):
        if self.beginning:
            # assume that the doctype declaration will be in the first
            # data payload (not strictly true, and it's perhaps a bit
            # lame, but it's easier and clearer than maintaining a
            # buffer of the stream in the unlikely circumstance that
            # the doctype can't be found in this payload)
            index = data.find('<!DOCTYPE')
            if index == -1:
                # jam an xhtml doctype declaration into the stream if the
                # document doesn't already have a doctype declaration
                match = self.xml_decl_re.search(data)
                if match is not None:
                    start, end = match.span(0)
                    before = data[:start]
                    after = data[end:]
                    data = before + self.xhtml_doctype + after
                else:
                    data = self.xhtml_doctype + data
            self.beginning = False
        return XMLTreeBuilder.feed(self, data)

def parse(source, xhtml=True):
    """ Parse source (a filelike object) into an element tree.  If
    xhtml is true, use a special parser that knows about html
    entities.  Otherwise use a 'normal' parser only. """
    builder = MeldTreeBuilder()
    if xhtml:
        # XHTMLTreeBuilder knows about html entities by default
        parser = XHTMLMeldParser(target=builder)
    else:
        parser = MeldParser(target=builder)
    root = et_parse(source, parser=parser).getroot()

    iterator = root.getiterator()
    for p in iterator:
        for c in p:
            c.parent = p
            
    return root

_HTMLTAGS_UNBALANCED    = ['area', 'base', 'basefont', 'br', 'col', 'frame',
                           'hr', 'img', 'input', 'isindex', 'link', 'meta',
                           'param']
_HTMLTAGS_NOESCAPE      = ['script', 'style']
_HTMLATTRS_BOOLEAN      = ['selected', 'checked', 'compact', 'declare',
                           'defer', 'disabled', 'ismap', 'multiple', 'nohref',
                           'noresize', 'noshade', 'nowrap']

def _write_html(file, node, encoding, namespaces):
    " Write HTML to file """
    if encoding is None:
        encoding = 'utf-8'
    tag = node.tag
    if tag is Comment:
        file.write("<!-- %s -->" % _escape_cdata(node.text, encoding))
    elif tag is ProcessingInstruction:
        file.write("<?%s?>" % _escape_cdata(node.text, encoding))
    elif tag is Replace:
        if node.structure:
            # this may produce invalid html
            file.write(_encode(node.text, encoding))
        else:
            file.write(_escape_cdata(node.text, encoding))
    else:
        if tag.startswith(_XHTML_PREFIX):
            tag = tag[len(_XHTML_PREFIX):]
        items = node.items()
        xmlns_items = [] # new namespaces in this scope
        try:
            if isinstance(tag, QName) or tag[:1] == "{":
                tag, xmlns = fixtag(tag, namespaces)
                if xmlns:
                    xmlns_items.append(xmlns)
        except TypeError:
            _raise_serialization_error(tag)
        file.write("<" + _encode(tag, encoding))
        if items or xmlns_items:
            items.sort() # lexical order
            for k, v in items:
                try:
                    if isinstance(k, QName) or k[:1] == "{":
                        continue
                except TypeError:
                    _raise_serialization_error(k)
                try:
                    if isinstance(v, QName):
                        v, xmlns = fixtag(v, namespaces)
                        if xmlns:
                            xmlns_items.append(xmlns)
                except TypeError:
                    _raise_serialization_error(v)
                if k.lower() in _HTMLATTRS_BOOLEAN:
                    file.write(' %s' % _encode(k, encoding))
                else:
                    file.write(" %s=\"%s\"" % (_encode(k, encoding),
                                               _escape_attrib(v, encoding)))
            for k, v in xmlns_items:
                file.write(" %s=\"%s\"" % (_encode(k, encoding),
                                           _escape_attrib(v, encoding)))
        if node.text or len(node):
            file.write(">")
            if node.text:
                if tag in _HTMLTAGS_NOESCAPE:
                    file.write(_encode(node.text, encoding))
                else:
                    file.write(_escape_cdata(node.text, encoding))
            for n in node:
                _write_html(file, n, encoding, namespaces)
            file.write("</" + _encode(tag, encoding) + ">")
        else:
            tag = node.tag
            if tag.startswith('{'):
                ns_uri, local = tag[1:].split('}', 1)
                if _namespace_map.get(ns_uri) == 'html':
                    tag = local
            if tag.lower() in _HTMLTAGS_UNBALANCED:
                file.write('>')
            else:
                file.write('>')
                file.write("</" + _encode(tag, encoding) + ">")
        for k, v in xmlns_items:
            del namespaces[v]
    if node.tail:
        file.write(_escape_cdata(node.tail, encoding))

def _write_xml(file, node, encoding, namespaces, pipeline, xhtml=False):
    """ Write XML to a file """
    if encoding is None:
        encoding = 'utf-8'
    tag = node.tag
    if tag is Comment:
        file.write("<!-- %s -->" % _escape_cdata(node.text, encoding))
    elif tag is ProcessingInstruction:
        file.write("<?%s?>" % _escape_cdata(node.text, encoding))
    elif tag is Replace:
        if node.structure:
            # this may produce invalid xml
            file.write(_encode(node.text, encoding))
        else:
            file.write(_escape_cdata(node.text, encoding))
    else:
        if xhtml:
            if tag.startswith(_XHTML_PREFIX):
                tag = tag[len(_XHTML_PREFIX):]
        items = node.items()
        xmlns_items = [] # new namespaces in this scope
        try:
            if isinstance(tag, QName) or tag[:1] == "{":
                tag, xmlns = fixtag(tag, namespaces)
                if xmlns:
                    xmlns_items.append(xmlns)
        except TypeError:
            _raise_serialization_error(tag)
        file.write("<" + _encode(tag, encoding))
        if items or xmlns_items:
            items.sort() # lexical order
            for k, v in items:
                try:
                    if isinstance(k, QName) or k[:1] == "{":
                        if not pipeline:
                            if k == _MELD_ID:
                                continue
                        k, xmlns = fixtag(k, namespaces)
                        if xmlns: xmlns_items.append(xmlns)
                except TypeError:
                    _raise_serialization_error(k)
                try:
                    if isinstance(v, QName):
                        v, xmlns = fixtag(v, namespaces)
                        if xmlns: xmlns_items.append(xmlns)
                except TypeError:
                    _raise_serialization_error(v)
                file.write(" %s=\"%s\"" % (_encode(k, encoding),
                                           _escape_attrib(v, encoding)))
            for k, v in xmlns_items:
                file.write(" %s=\"%s\"" % (_encode(k, encoding),
                                           _escape_attrib(v, encoding)))
        if node.text or len(node):
            file.write(">")
            if node.text:
                file.write(_escape_cdata(node.text, encoding))
            for n in node:
                _write_xml(file, n, encoding, namespaces, pipeline, xhtml)
            file.write("</" + _encode(tag, encoding) + ">")
        else:
            file.write(" />")
        for k, v in xmlns_items:
            del namespaces[v]
    if node.tail:
        file.write(_escape_cdata(node.tail, encoding))

def _write_declaration(file, encoding):
    if not encoding:
        file.write('<?xml version="1.0"?>\n')
    else:
        file.write('<?xml version="1.0" encoding="%s"?>\n' % encoding)

def _write_doctype(file, doctype):
    try:
        name, pubid, system = doctype
    except (ValueError, TypeError):
        raise ValueError, ("doctype must be supplied as a 3-tuple in the form "
                           "(name, pubid, system) e.g. '%s'" % doctype.xhtml)
    file.write('<!DOCTYPE %s PUBLIC "%s" "%s">\n' % (name, pubid, system))

def test(filename):
    root = parse(open(filename, 'r'))
    ob = root.findmeld('tr')
    values = []
    for thing in range(0, 20):
        values.append((str(thing), str(thing)))
    for tr, (name, desc) in ob.repeat(values):
        tr.findmeld('td1').text = name
        tr.findmeld('td2').text = desc
    from cStringIO import StringIO
    root.write_xml(StringIO())
    
if __name__ == '__main__':
    import sys
    filename = sys.argv[1]
    import timeit
    t = timeit.Timer("test('%s')" % filename, "from __main__ import test")
    print t.timeit(300) / 300
    
    
