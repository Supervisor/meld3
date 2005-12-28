import htmlentitydefs
import re
import types
import mimetools
from StringIO import StringIO

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
from elementtree.HTMLTreeBuilder import HTMLParser
from elementtree.HTMLTreeBuilder import IGNOREEND
from elementtree.HTMLTreeBuilder import AUTOCLOSE
from elementtree.HTMLTreeBuilder import is_not_ascii

_MELD_NS_URL  = 'http://www.plope.com/software/meld3'
_MELD_PREFIX  = '{%s}' % _MELD_NS_URL
_MELD_LOCAL   = 'id'
_MELD_ID      = '%s%s' % (_MELD_PREFIX, _MELD_LOCAL)
_XHTML_NS_URL = 'http://www.w3.org/1999/xhtml'
_XHTML_PREFIX = '{%s}' % _XHTML_NS_URL

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

    def diffmeld(self, other):
        """ Compute the meld element differences from this node (the
        source) to 'other' (the target).  Return a dictionary of
        sequences in the form {'added':[], 'removed':[], 'moved':[]}"""
        def sharedparents(srcelement, tgtelement):
            srcparent = srcelement.parent
            tgtparent = tgtelement.parent
            srcparenttag = getattr(srcparent, 'tag', None)
            tgtparenttag = getattr(tgtparent, 'tag', None)
            if srcparenttag != tgtparenttag:
                return False
            elif tgtparenttag is None and srcparenttag is None:
                return True
            elif tgtparent and srcparent:
                return sharedparents(srcparent, tgtparent)
            return False

        srcelements = self.findmelds()
        srcids = {}
        for element in srcelements:
            srcids[element.attrib[_MELD_ID]] = element

        tgtelements = other.findmelds()
        tgtids = {}
        for element in tgtelements:
            tgtids[element.attrib[_MELD_ID]] = element
        
        removed = []
        for srcid in srcids:
            if srcid not in tgtids:
                removed.append(srcids[srcid])

        added = []
        for tgtid in tgtids:
            if tgtid not in srcids:
                added.append(tgtids[tgtid])
                
        moved = []
        for srcid in srcids:
            if srcid in tgtids:
                srcelement = srcids[srcid]
                tgtelement = tgtids[srcid]
                if not sharedparents(srcelement, tgtelement):
                    moved.append(tgtelement)

        moved = diffreduce(moved)

        return {'added':added, 'removed':removed, 'moved':moved}
            
    def findmelds(self):
        iterator = self.getiterator()
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
                clone = element.clone()
                parent.append(clone)
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
        element.text = self.text
        element.tail = self.tail
        if parent is not None:
            parent.append(element)
        for child in self.getchildren():
            child.clone(element)
        return element

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
            for i in range (len(parent)):
                if parent[i] is self:
                    return i

    def shortrepr(self, encoding=None):
        file = StringIO()
        _write_html(file, self, encoding, {}, maxdepth=2)
        file.seek(0)
        return file.read()

    def meldid(self):
        return self.attrib.get(_MELD_ID)

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

_HTMLTAGS_UNBALANCED    = ['area', 'base', 'basefont', 'br', 'col', 'frame',
                           'hr', 'img', 'input', 'isindex', 'link', 'meta',
                           'param']
_HTMLTAGS_NOESCAPE      = ['script', 'style']
_HTMLATTRS_BOOLEAN      = ['selected', 'checked', 'compact', 'declare',
                           'defer', 'disabled', 'ismap', 'multiple', 'nohref',
                           'noresize', 'noshade', 'nowrap']

def _write_html(file, node, encoding, namespaces, depth=-1, maxdepth=None):
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
                if maxdepth is not None:
                    depth = depth + 1
                    if depth < maxdepth:
                        _write_html(file, n, encoding, namespaces, depth,
                                    maxdepth)
                    elif depth == maxdepth:
                        file.write(' [...]\n')
                                 
                else:
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
                    if not pipeline:
                        # special-case for HTML input
                        if k == 'xmlns:meld':
                            continue
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


# utility functions

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

def diffreduce(elements):
    # come up with a reasonable diff-reducing algorithm here ;-)
    return elements

def test(filename):
    root = parse_xml(open(filename, 'r'))
    ob = root.findmeld('tr')
    values = []
    for thing in range(0, 20):
        values.append((str(thing), str(thing)))
    for tr, (name, desc) in ob.repeat(values):
        tr.findmeld('td1').content(name)
        tr.findmeld('td2').content(desc)
    root.write_xml(StringIO())
    
if __name__ == '__main__':
    import sys
    filename = sys.argv[1]
    import timeit
    t = timeit.Timer("test('%s')" % filename, "from __main__ import test")
    print t.timeit(300) / 300
    
    
