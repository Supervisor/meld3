import htmlentitydefs
import re
import types
import mimetools
from StringIO import StringIO

from elementtree.ElementTree import TreeBuilder
from elementtree.ElementTree import XMLTreeBuilder
from elementtree.ElementTree import Comment
from elementtree.ElementTree import ProcessingInstruction
from elementtree.ElementTree import QName
from elementtree.ElementTree import _raise_serialization_error
from elementtree.ElementTree import _namespace_map
from elementtree.ElementTree import fixtag
from elementtree.ElementTree import parse as et_parse
from elementtree.ElementTree import ElementPath
from elementtree.HTMLTreeBuilder import HTMLParser
from elementtree.HTMLTreeBuilder import IGNOREEND
from elementtree.HTMLTreeBuilder import AUTOCLOSE
from elementtree.HTMLTreeBuilder import is_not_ascii

class IO:
    def __init__(self):
        self.data = ""

    def write(self, data):
        self.data += data

    def getvalue(self):
        return self.data

    def clear(self):
        self.data = ""

try:
    import cmeld3 as helper
except ImportError:
    class Helper:
        def findmeld(self, node, name, default=None):
            iterator = self.getiterator(node)
            for element in iterator:
                val = element.attrib.get(_MELD_ID)
                if val == name:
                    return element
            return default

        def clone(self, node, parent=None):
            element = _MeldElementInterface(node.tag, node.attrib.copy())
            element.text = node.text
            element.tail = node.tail
            if parent is not None:
                # avoid calling self.append to reduce function call overhead
                parent._children.append(element)
                element.parent = parent
            for child in node._children:
                self.clone(child, element)
            return element

        def getiterator(self, node, tag=None):
            nodes = []
            if tag == "*":
                tag = None
            if tag is None or node.tag == tag:
                nodes.append(node)
            for element in node._children:
                nodes.extend(self.getiterator(element, tag))
            return nodes
    helper = Helper()

_MELD_NS_URL  = 'http://www.plope.com/software/meld3'
_MELD_PREFIX  = '{%s}' % _MELD_NS_URL
_MELD_LOCAL   = 'id'
_MELD_ID      = '%s%s' % (_MELD_PREFIX, _MELD_LOCAL)
_XHTML_NS_URL = 'http://www.w3.org/1999/xhtml'
_XHTML_PREFIX = '{%s}' % _XHTML_NS_URL
_XHTML_PREFIX_LEN = len(_XHTML_PREFIX)

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

class _MeldElementInterface:
    parent = None
    attrib = None
    text   = None
    tail   = None

    # overrides to reduce MRU lookups
    def __init__(self, tag, attrib):
        self.tag = tag
        self.attrib = attrib
        self._children = []

    def __repr__(self):
        return "<MeldElement %s at %x>" % (self.tag, id(self))

    def __len__(self):
        return len(self._children)

    def __getitem__(self, index):
        return self._children[index]

    def __getslice__(self, start, stop):
        return self._children[start:stop]

    def getchildren(self):
        return self._children

    def find(self, path):
        return ElementPath.find(self, path)

    def findtext(self, path, default=None):
        return ElementPath.findtext(self, path, default)

    def findall(self, path):
        return ElementPath.findall(self, path)

    def clear(self):
        self.attrib.clear()
        self._children = []
        self.text = self.tail = None

    def get(self, key, default=None):
        return self.attrib.get(key, default)

    def set(self, key, value):
        self.attrib[key] = value

    def keys(self):
        return self.attrib.keys()

    def items(self):
        return self.attrib.items()

    def getiterator(self, tag=None):
        return helper.getiterator(self)

    # overrides to support parent pointers and factories

    def __setitem__(self, index, element):
        self._children[index] = element
        element.parent = self

    def __setslice__(self, start, stop, elements):
        for element in elements:
            element.parent = self
        self._children[start:stop] = list(elements)

    def append(self, element):
        self._children.append(element)
        element.parent = self

    def insert(self, index, element):
        self._children.insert(index, element)
        element.parent = self

    def __delitem__(self, index):
        ob = self._children[index]
        ob.parent = None
        del self._children[index]

    def __delslice__(self, start, stop):
        obs = self._children[start:stop]
        for ob in obs:
            ob.parent = None
        del self._children[start:stop]

    def remove(self, element):
        self._children.remove(element)
        element.parent = None

    def makeelement(self, tag, attrib):
        return self.__class__(tag, attrib)

    # meld-specific

    def __mod__(self, other):
        """ Fill in the text values of meld nodes in tree; only
        support dictionarylike operand (sequence operand doesn't seem
        to make sense here)"""
        return self.fillmelds(**other)

    def fillmelds(self, **kw):
        """ Fill in the text values of meld nodes in tree using the
        keyword arguments passed in; use the keyword keys as meld ids
        and the keyword values as text that should fill in the node
        text on which that meld id is found.  Return a list of keys
        from **kw that were not able to be found anywhere in the tree.
        Never raises an exception. """
        unfilled = []
        for k in kw:
            node = self.findmeld(k)
            if node is None:
                unfilled.append(k)
            else:
                node.text = kw[k]
        return unfilled

    def findmeld(self, name, default=None):
        """ Find a node in the tree that has a 'meld id' corresponding
        to 'name'. Iterate over all subnodes recursively looking for a
        node which matches.  If we can't find the node, return None."""
        # this could be faster if we indexed all the meld nodes in the
        # tree; we just walk the whole hierarchy now.
        result = helper.findmeld(self, name)
        if result is None:
            return default
        return result

    def findmelds(self):
        iterator = helper.getiterator(self)
        elements = []
        for element in iterator:
            val = element.attrib.get(_MELD_ID)
            if val is not None:
                elements.append(element)
        return elements

    # ZPT-alike methods
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
                clone = element.clone(parent)
                yield clone, thing
            first = False

    def replace(self, text, structure=False):
        """ Replace this element with a Replace node in our parent with
        the text 'text' and return the index of our position in
        our parent.  If we have no parent, do nothing, and return None.
        Pass the 'structure' flag to the replace node so it can do the right
        thing at render time. """
        parent = self.parent
        i = self.deparent()
        if i is not None:
            # reduce function call overhead by not calliing self.insert
            node = Replace(text, structure)
            parent._children.insert(i, node)
            node.parent = parent
            return i

    def content(self, text, structure=False):
        """ Delete this node's children and append a Replace node that
        contains text.  Always return None.  Pass the 'structure' flag
        to the replace node so it can do the right thing at render
        time."""
        for child in self._children:
            child.parent = None # clean up potential circrefs
        self.text = None
        #node = Replace(text, structure)
        # reduce function call overhead by not calling Replace
        node = self.__class__(Replace, {})
        node.text = text
        node.structure = structure
        # reduce function call overhead by not calling self.append
        node.parent = self
        self._children = [node]

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
        # use a list as a collector, and only call the write method of
        # the file once we've collected all output (reduce function call
        # overhead)
        io = IO()
        write = io.write
        if not hasattr(file, "write"):
            file = open(file, "wb")
        if not fragment:
            if declaration:
                _write_declaration(write, encoding)
            if doctype:
                _write_doctype(write, doctype)
        _write_xml(write, self, encoding, {}, pipeline)
        file.write(''.join(data))

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
        io = IO()
        write = io.write
        if encoding is None:
            encoding = 'utf-8'
        if encoding in ('utf8', 'utf-8', 'latin-1', 'latin1',
                        'ascii'):
            # optimize for common case
            string = u""
            if not fragment:
                if doctype:
                    _write_doctype(write, doctype)
                    string = io.getvalue()
            _write_html_no_encoding(string, self, {})
            file.write(string.encode(encoding))
        else:
            if not fragment:
                if doctype:
                    _write_doctype(write, doctype)
            _write_html(write, self, encoding, {})
            file.write(io.data)

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
        # use a list as a collector, and only call the write method of
        # the file once we've collected all output (reduce function call
        # overhead)
        data = []
        write = data.append
        if not hasattr(file, "write"):
            file = open(file, "wb")
        if not fragment:
            if declaration:
                _write_declaration(write, encoding)
            if doctype:
                _write_doctype(write, doctype)
        _write_xml(write, self, encoding, {}, pipeline, xhtml=True)
        file.write(''.join(data))
            
    def clone(self, parent=None):
        """ Create a clone of an element.  If parent is not None,
        append the element to the parent.  Recurse as necessary to create
        a deep clone of the element. """
        return helper.clone(self, parent)
    
    def deparent(self):
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
            # avoid calling len(parent) in favor of len(parent._children)
            # to reduce function call overhead
            for i in range (len(parent._children)):
                if parent[i] is self:
                    return i

    def shortrepr(self, encoding=None):
        data = []
        _write_html(data.append, self, encoding, {}, maxdepth=2)
        return ''.join(data)

    def diffmeld(self, other):
        """ Compute the meld element differences from this node (the
        source) to 'other' (the target).  Return a dictionary of
        sequences in the form {'unreduced:
               {'added':[], 'removed':[], 'moved':[]},
                               'reduced':
               {'added':[], 'removed':[], 'moved':[]},}
                               """
        srcelements = self.findmelds()
        tgtelements = other.findmelds()
        srcids = [ x.meldid() for x in srcelements ]
        tgtids = [ x.meldid() for x in tgtelements ]
        
        removed = []
        for srcelement in srcelements:
            if srcelement.meldid() not in tgtids:
                removed.append(srcelement)

        added = []
        for tgtelement in tgtelements:
            if tgtelement.meldid() not in srcids:
                added.append(tgtelement)
                
        moved = []
        for srcelement in srcelements:
            srcid = srcelement.meldid()
            if srcid in tgtids:
                i = tgtids.index(srcid)
                tgtelement = tgtelements[i]
                if not sharedlineage(srcelement, tgtelement):
                    moved.append(tgtelement)

        unreduced = {'added':added, 'removed':removed, 'moved':moved}

        moved_reduced = diffreduce(moved)
        added_reduced = diffreduce(added)
        removed_reduced = diffreduce(removed)

        reduced = {'moved':moved_reduced, 'added':added_reduced,
                   'removed':removed_reduced}

        return {'unreduced':unreduced,
                'reduced':reduced}
            
    def meldid(self):
        return self.attrib.get(_MELD_ID)

    def lineage(self):
        L = []
        parent = self
        while parent is not None:
            L.append(parent)
            parent = parent.parent
        return L


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

class HTMLMeldParser(HTMLParser):
    """ A mostly-cut-and-paste of ElementTree's HTMLTreeBuilder that
    does special meld3 things (like preserve comments and munge meld
    ids).  Subclassing is not possible due to private attributes. :-("""

    def __init__(self, builder=None, encoding=None):
        self.__stack = []
        if builder is None:
            builder = MeldTreeBuilder()
        self.builder = builder
        self.encoding = encoding or "iso-8859-1"
        HTMLParser.__init__(self)
        self.meldids = {}

    def close(self):
        HTMLParser.close(self)
        self.meldids = {}
        return self.builder.close()

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            # look for encoding directives
            http_equiv = content = None
            for k, v in attrs:
                if k == "http-equiv":
                    http_equiv = v.lower()
                elif k == "content":
                    content = v
            if http_equiv == "content-type" and content:
                # use mimetools to parse the http header
                header = mimetools.Message(
                    StringIO("%s: %s\n\n" % (http_equiv, content))
                    )
                encoding = header.getparam("charset")
                if encoding:
                    self.encoding = encoding
        if tag in AUTOCLOSE:
            if self.__stack and self.__stack[-1] == tag:
                self.handle_endtag(tag)
        self.__stack.append(tag)
        attrib = {}
        if attrs:
            for k, v in attrs:
                if k == 'meld:id':
                    k = _MELD_ID
                    if self.meldids.get(v):
                        raise ValueError, ('Repeated meld id "%s" in source' %
                                           v)
                    self.meldids[v] = 1
                attrib[k.lower()] = v
        self.builder.start(tag, attrib)
        if tag in IGNOREEND:
            self.__stack.pop()
            self.builder.end(tag)

    def handle_endtag(self, tag):
        if tag in IGNOREEND:
            return
        lasttag = self.__stack.pop()
        if tag != lasttag and lasttag in AUTOCLOSE:
            self.handle_endtag(lasttag)
        self.builder.end(tag)

    def handle_charref(self, char):
        if char[:1] == "x":
            char = int(char[1:], 16)
        else:
            char = int(char)
        if 0 <= char < 128:
            self.builder.data(chr(char))
        else:
            self.builder.data(unichr(char))

    def handle_entityref(self, name):
        entity = htmlentitydefs.entitydefs.get(name)
        if entity:
            if len(entity) == 1:
                entity = ord(entity)
            else:
                entity = int(entity[2:-1])
            if 0 <= entity < 128:
                self.builder.data(chr(entity))
            else:
                self.builder.data(unichr(entity))
        else:
            self.unknown_entityref(name)

    def handle_data(self, data):
        if isinstance(data, type('')) and is_not_ascii(data):
            # convert to unicode, but only if necessary
            data = unicode(data, self.encoding, "ignore")
        self.builder.data(data)

    def unknown_entityref(self, name):
        pass # ignore by default; override if necessary

    def handle_comment(self, data):
        self.builder.start(Comment, {})
        self.builder.data(data)
        self.builder.end(Comment)

def do_parse(source, parser):
    root = et_parse(source, parser=parser).getroot()
    iterator = root.getiterator()
    for p in iterator:
        for c in p:
            c.parent = p
    return root

def parse_xml(source):
    """ Parse source (a filelike object) into an element tree.  If
    html is true, use a parser that can resolve somewhat ambiguous
    HTML into XHTML.  Otherwise use a 'normal' parser only."""
    builder = MeldTreeBuilder()
    parser = MeldParser(target=builder)
    return do_parse(source, parser)

def parse_html(source, encoding=None):
    builder = MeldTreeBuilder()
    parser = HTMLMeldParser(builder, encoding)
    return do_parse(source, parser)

def parse_xmlstring(text):
    source = StringIO(text)
    return parse_xml(source)

def parse_htmlstring(text, encoding=None):
    source = StringIO(text)
    return parse_html(source, encoding)

attrib_needs_escaping = re.compile(r'[&]|["]|[<]').search
cdata_needs_escaping = re.compile(r'[&]|[<]').search

_HTMLTAGS_UNBALANCED    = {'area':1, 'base':1, 'basefont':1, 'br':1, 'col':1,
                           'frame':1, 'hr':1, 'img':1, 'input':1, 'isindex':1,
                           'link':1, 'meta':1, 'param':1}
_HTMLTAGS_NOESCAPE      = {'script':1, 'style':1}
_HTMLATTRS_BOOLEAN      = {'selected':1, 'checked':1, 'compact':1, 'declare':1,
                           'defer':1, 'disabled':1, 'ismap':1, 'multiple':1,
                           'nohref':1, 'noresize':1, 'noshade':1, 'nowrap':1}
_SIMPLE = {Comment:"<!-- %s -->", ProcessingInstruction:"<?%s?>"}

def _write_html(write, node, encoding, namespaces, depth=-1, maxdepth=None):
    " Write HTML to file """
    if encoding is None:
        encoding = 'utf-8'

    tag = node.tag
    tail = node.tail
    text = node.text
    tail = node.tail

    if tag is Comment or tag is ProcessingInstruction:
        template = _SIMPLE[tag]
        if cdata_needs_escaping(text):
            write(template % _escape_cdata(text, encoding))
        else:
            write(template % text.encode(encoding))
            
    elif tag is Replace:
        if node.structure:
            # this may produce invalid html
            write(text.encode(encoding))
        else:
            if cdata_needs_escaping(text):
                write(_escape_cdata(text, encoding))
            else:
                write(text.encode(encoding))
    else:
        if tag[:_XHTML_PREFIX_LEN] == _XHTML_PREFIX:
            tag = tag[_XHTML_PREFIX_LEN:]
        if node.attrib:
            items = node.attrib.items()
        else:
            items = ()
        xmlns_items = [] # new namespaces in this scope
        try:
            if tag[:1] == "{":
                tag, xmlns = fixtag(tag, namespaces)
                if xmlns:
                    xmlns_items.append(xmlns)
        except TypeError:
            _raise_serialization_error(tag)
        write("<" + tag.encode(encoding))
        if items or xmlns_items:
            items.sort() # lexical order
            for k, v in items:
                try:
                    if k[:1] == "{":
                        continue
                except TypeError:
                    _raise_serialization_error(k)
                if k.lower() in _HTMLATTRS_BOOLEAN:
                    write(' %s' % k.encode(encoding))
                else:
                    if attrib_needs_escaping(v):
                        write(" %s=\"%s\"" % (k.encode(encoding),
                                              _escape_attrib(v, encoding)))
                    else:
                        write(" %s=\"%s\"" % (k.encode(encoding),
                                              v.encode(encoding)))
                        
            for k, v in xmlns_items:
                if attrib_needs_escaping(v):
                    write(" %s=\"%s\"" % (k.encode(encoding),
                                          _escape_attrib(v, encoding)))
                else:
                    write(" %s=\"%s\"" % (k.encode(encoding),
                                          v.encode(encoding)))
                    
        if text or node._children:
            write(">")
            if text:
                if tag in _HTMLTAGS_NOESCAPE:
                    write(text.encode(encoding))
                elif cdata_needs_escaping(text):
                    write(_escape_cdata(text, encoding))
                else:
                    write(text.encode(encoding))

            for n in node._children:
                if maxdepth is not None:
                    depth = depth + 1
                    if depth < maxdepth:
                        _write_html(write, n, encoding, namespaces, depth,
                                    maxdepth)
                    elif depth == maxdepth:
                        write(' [...]\n')
                                 
                else:
                    _write_html(write, n, encoding, namespaces)
            write("</" + tag.encode(encoding) + ">")
        else:
            tag = node.tag
            if tag.startswith('{'):
                ns_uri, local = tag[1:].split('}', 1)
                if _namespace_map.get(ns_uri) == 'html':
                    tag = local
            if tag.lower() in _HTMLTAGS_UNBALANCED:
                write('>')
            else:
                write('>')
                write("</" + tag.encode(encoding) + ">")
        for k, v in xmlns_items:
            del namespaces[v]
    if tail:
        if cdata_needs_escaping(tail):
            write(_escape_cdata(tail, encoding))
        else:
            write(tail.encode(encoding))

def _write_html_no_encoding(string, node, namespaces, depth=-1, maxdepth=None):
    """ Append HTML to string without any particular unicode encoding.
    We have a separate function for this due to the fact that encoding
    while recursing is very expensive if this will get serialized out to
    utf8 anyway (the encoding can happen afterwards).  We append to a string
    because it's faster than calling any 'write' or 'append' function."""

    tag  = node.tag
    tail = node.tail
    text = node.text
    tail = node.tail

    if tag is Comment or tag is ProcessingInstruction:
        template = _SIMPLE[tag]
        if cdata_needs_escaping(text):
            string += template % _escape_cdata_noencoding(text)
        else:
            string += template % text
    elif tag is Replace:
        if node.structure:
            # this may produce invalid html
            string += text
        else:
            if cdata_needs_escaping(text):
                string += _escape_cdata_noencoding(text)
            else:
                string += text
    else:
        if tag[:_XHTML_PREFIX_LEN] == _XHTML_PREFIX:
            tag = tag[_XHTML_PREFIX_LEN:]
        if node.attrib:
            items = node.attrib.items()
        else:
            items = ()
        xmlns_items = [] # new namespaces in this scope
        try:
            if tag[:1] == "{":
                tag, xmlns = fixtag(tag, namespaces)
                if xmlns:
                    xmlns_items.append(xmlns)
        except TypeError:
            _raise_serialization_error(tag)
        string += "<" + tag
        if items or xmlns_items:
            items.sort() # lexical order
            for k, v in items:
                try:
                    if k[:1] == "{":
                        continue
                except TypeError:
                    _raise_serialization_error(k)
                if _HTMLATTRS_BOOLEAN.has_key(k.lower()):
                    string += ' ' + k
                else:
                    if attrib_needs_escaping(v):
                        string += " %s=\"%s\"" % (k,
                                                  _escape_attrib_noencoding(v))
                    else:
                        string += " %s=\"%s\"" % (k, v)
                        
            for k, v in xmlns_items:
                if attrib_needs_escaping(v):
                    string += " %s=\"%s\"" % (k, _escape_attrib_noencoding(v))
                else:
                    string += " %s=\"%s\"" % (k, v)
                    
        if text or node._children:
            string += ">"
            if text:
                if _HTMLTAGS_NOESCAPE.has_key(tag):
                    string += text
                else:
                    if cdata_needs_escaping(text):
                        string += _escape_cdata_noencoding(text)
                    else:
                        string += text

            for n in node._children:
                if maxdepth is not None:
                    depth = depth + 1
                    if depth < maxdepth:
                        _write_html_no_encoding(string, n, namespaces, depth,
                                                maxdepth)
                    elif depth == maxdepth:
                        string += ' [...]\n'
                                 
                else:
                    _write_html_no_encoding(string, n, namespaces)
            string += "</" + tag + ">"
        else:
            tag = node.tag
            if tag.startswith('{'):
                ns_uri, local = tag[1:].split('}', 1)
                if _namespace_map.get(ns_uri) == 'html':
                    tag = local
            if _HTMLTAGS_UNBALANCED.has_key(tag.lower()):
                string += '>'
            else:
                string += '>'
                string += "</" + tag  + ">"
        for k, v in xmlns_items:
            del namespaces[v]
    if tail:
        if cdata_needs_escaping(tail):
            string += _escape_cdata_noencoding(tail)
        else:
            string += tail
        
def _write_xml(write, node, encoding, namespaces, pipeline, xhtml=False):
    """ Write XML to a file """
    if encoding is None:
        encoding = 'utf-8'
    tag = node.tag
    if tag is Comment:
        write("<!-- %s -->" % _escape_cdata(node.text, encoding))
    elif tag is ProcessingInstruction:
        write("<?%s?>" % _escape_cdata(node.text, encoding))
    elif tag is Replace:
        if node.structure:
            # this may produce invalid xml
            write(node.text.encode(encoding))
        else:
            write(_escape_cdata(node.text, encoding))
    else:
        if xhtml:
            if tag[:_XHTML_PREFIX_LEN] == _XHTML_PREFIX:
                tag = tag[_XHTML_PREFIX_LEN:]
        if node.attrib:
            items = node.attrib.items()
        else:
            items = ()
        xmlns_items = [] # new namespaces in this scope
        try:
            if tag[:1] == "{":
                tag, xmlns = fixtag(tag, namespaces)
                if xmlns:
                    xmlns_items.append(xmlns)
        except TypeError:
            _raise_serialization_error(tag)
        write("<" + tag.encode(encoding))
        if items or xmlns_items:
            items.sort() # lexical order
            for k, v in items:
                try:
                    if k[:1] == "{":
                        if not pipeline:
                            if k == _MELD_ID:
                                continue
                        k, xmlns = fixtag(k, namespaces)
                        if xmlns: xmlns_items.append(xmlns)
                    if not pipeline:
                        # special-case for HTML input
                        if k == 'xmlns:meld':
                            continue
                except TypeError:
                    _raise_serialization_error(k)
                write(" %s=\"%s\"" % (k.encode(encoding),
                                      _escape_attrib(v, encoding)))
            for k, v in xmlns_items:
                write(" %s=\"%s\"" % (k.encode(encoding),
                                      _escape_attrib(v, encoding)))
        if node.text or node._children:
            write(">")
            if node.text:
                write(_escape_cdata(node.text, encoding))
            for n in node._children:
                _write_xml(write, n, encoding, namespaces, pipeline, xhtml)
            write("</" + tag.encode(encoding) + ">")
        else:
            write(" />")
        for k, v in xmlns_items:
            del namespaces[v]
    if node.tail:
        write(_escape_cdata(node.tail, encoding))

# overrides to elementtree to increase speed and get entity quoting correct.

nonentity_re = re.compile('&(?!([#\w]*;))') # negative lookahead assertion

def _escape_cdata(text, encoding=None):
    # escape character data
    try:
        if encoding:
            try:
                text = text.encode(encoding)
            except UnicodeError:
                return _encode_entity(text)
        text = nonentity_re.sub('&amp;', text)
        text = text.replace("<", "&lt;")
        return text
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def _escape_attrib(text, encoding=None):
    # escape attribute value
    try:
        if encoding:
            try:
                text = text.encode(encoding)
            except UnicodeError:
                return _encode_entity(text)
        # don't requote properly-quoted entities
        text = nonentity_re.sub('&amp;', text)
        text = text.replace("<", "&lt;")
        text = text.replace('"', "&quot;")
        return text
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def _escape_cdata_noencoding(text):
    # escape character data
    text = nonentity_re.sub('&amp;', text)
    text = text.replace("<", "&lt;")
    return text

def _escape_attrib_noencoding(text):
    # don't requote properly-quoted entities
    text = nonentity_re.sub('&amp;', text)
    text = text.replace("<", "&lt;")
    text = text.replace('"', "&quot;")
    return text

# utility functions

def _write_declaration(write, encoding):
    if not encoding:
        write('<?xml version="1.0"?>\n')
    else:
        write('<?xml version="1.0" encoding="%s"?>\n' % encoding)

def _write_doctype(write, doctype):
    try:
        name, pubid, system = doctype
    except (ValueError, TypeError):
        raise ValueError, ("doctype must be supplied as a 3-tuple in the form "
                           "(name, pubid, system) e.g. '%s'" % doctype.xhtml)
    write('<!DOCTYPE %s PUBLIC "%s" "%s">\n' % (name, pubid, system))

xml_decl_re = re.compile(r'<\?xml .*?\?>')
begin_tag_re = re.compile(r'<[^/?!]?\w+')
'<!DOCTYPE %s PUBLIC "%s" "%s">' % doctype.html

def insert_doctype(data, doctype=doctype.xhtml):
    # jam an html doctype declaration into 'data' if it
    # doesn't already contain a doctype declaration
    match = xml_decl_re.search(data)
    dt_string = '<!DOCTYPE %s PUBLIC "%s" "%s">' % doctype
    if match is not None:
        start, end = match.span(0)
        before = data[:start]
        tag = data[start:end]
        after = data[end:]
        return before + tag + dt_string + after
    else:
        return dt_string + data

def insert_meld_ns_decl(data):
    match = begin_tag_re.search(data)
    if match is not None:
        start, end = match.span(0)
        before = data[:start]
        tag = data[start:end] + ' xmlns:meld="%s"' % _MELD_NS_URL
        after = data[end:]
        data =  before + tag + after
    return data

def prefeed(data, doctype=doctype.xhtml):
    if data.find('<!DOCTYPE') == -1:
        data = insert_doctype(data, doctype)
    if data.find('xmlns:meld') == -1:
        data = insert_meld_ns_decl(data)
    return data

def sharedlineage(srcelement, tgtelement):
    srcparent = srcelement.parent
    tgtparent = tgtelement.parent
    srcparenttag = getattr(srcparent, 'tag', None)
    tgtparenttag = getattr(tgtparent, 'tag', None)
    if srcparenttag != tgtparenttag:
        return False
    elif tgtparenttag is None and srcparenttag is None:
        return True
    elif tgtparent and srcparent:
        return sharedlineage(srcparent, tgtparent)
    return False

def diffreduce(elements):
    # each element in 'elements' should all have non-None meldids, and should
    # be preordered in depth-first traversal order
    reduced = []
    for element in elements:
        parent = element.parent
        if parent is None:
            reduced.append(element)
            continue
        if parent in reduced:
            continue
        reduced.append(element)
    return reduced
    
def intersection(S1, S2):
    L = []
    for element in S1:
        if element in S2:
            L.append(element)
    return L

def melditerator(element, meldid=None, _MELD_ID=_MELD_ID):
    nodeid = element.attrib.get(_MELD_ID)
    if nodeid is not None:
        if meldid is None or nodeid == meldid:
            yield element
    for child in element._children:
        for el2 in melditerator(child, meldid):
            nodeid = el2.attrib.get(_MELD_ID)
            if nodeid is not None:
                if meldid is None or nodeid == meldid:
                    yield el2

def search(name):
    if not "." in name:
        raise ValueError("unloadable datatype name: " + `name`)
    components = name.split('.')
    start = components[0]
    g = globals()
    package = __import__(start, g, g)
    modulenames = [start]
    for component in components[1:]:
        modulenames.append(component)
        try:
            package = getattr(package, component)
        except AttributeError:
            n = '.'.join(modulenames)
            package = __import__(n, g, g, component)
    return package

def sample_mutator(root):
    values = []
    for thing in range(0, 20):
        values.append((str(thing), str(thing)))

    ob = root.findmeld('tr')
    for tr, (name, desc) in ob.repeat(values):
        tr.findmeld('td1').content(name)
        tr.findmeld('td2').content(desc)

if __name__ == '__main__':
    # call interactively by invoking meld3.py with a filename and
    # a dotted-python-path name to a mutator function that accepts a single
    # argument (the root), e.g.:
    #
    # python meld3.py sample.html meld3.sample_mutator
    #
    # the rendering will be sent to stdout
    import sys
    filename = sys.argv[1]
    try:
        mutator = sys.argv[2]
    except IndexError:
        mutator = None
    import timeit
    root = parse_html(open(filename, 'r'))
    io = StringIO()
    if mutator:
        mutator = search(mutator)
        mutator(root)
    root.write_html(io)
    sys.stdout.write(io.getvalue())
    
    
    
