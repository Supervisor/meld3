import copy

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
from elementtree.ElementTree import fixtag

_MELD_PREFIX = '{http://www.plope.com/software/meld3}'
_MELD_LOCAL = 'id'
_MELD_ID = '%s%s' % (_MELD_PREFIX, _MELD_LOCAL)
_XHTML_PREFIX = '{http://www.w3.org/1999/xhtml}'

_marker = []

class _MeldHelper(object):
    def __init__(self, element):
        self.element = element

    def __getitem__(self, name, default=_marker):
        iterator = self.element.getiterator()
        for element in iterator:
            val = element.attrib.get(_MELD_ID)
            if val == name:
                return element
        if default is _marker:
            raise AttributeError, name
        return default

    def get(self, name, default=None):
        return self.__getitem__(name, default)

    def repeat(self, iterable, childname=None):
        if childname is None:
            element = self.element
        else:
            element = self[childname]

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

class _MeldElementInterface(_ElementInterface):
    parent = None

    # overrides to support parent pointers
    def __setitem__(self, index, element):
        _ElementInterface.__setitem__(self, index, element)
        element.parent = self
        
    def append(self, element):
        _ElementInterface.append(self, element)
        element.parent = self

    def insert(self, index, element):
        _ElementInterface.insert(self, index, element)
        element.parent = self

    # meld-specific
    def _meld_helper(self):
        return _MeldHelper(self)

    meld = property(_meld_helper)

    def clone(self):
        element = copy.deepcopy(self)
        element.parent = None
        return element
    
    def remove(self):
        parent = self.parent
        if parent is not None:
            del self.parent
            for i in range (len(parent)):
                if parent[i] == self:
                    del parent[i]
                    break
            
def MeldTreeBuilder():
    return TreeBuilder(element_factory=_MeldElementInterface)

def parse(source):
    from elementtree.ElementTree import parse
    builder = MeldTreeBuilder()
    parser =  XMLTreeBuilder(target=builder)
    root = parse(source, parser=parser).getroot()

    iterator = root.getiterator()
    for p in iterator:
        for c in p:
            c.parent = p
            
    return root

def write(root, file, encoding="us-ascii", html=False, preserve_meldids=False):
    assert root is not None
    if not hasattr(file, "write"):
        file = open(file, "wb")
    if not encoding:
        encoding = "us-ascii"
    elif encoding != "utf-8" and encoding != "us-ascii":
        file.write("<?xml version='1.0' encoding='%s'?>\n" % encoding)
    if html:
        _write_html(file, root, encoding, {}, preserve_meldids)
    else:
        _write(file, root, encoding, {}, preserve_meldids)

def _write(file, node, encoding, namespaces, preserve_meldids):
    # write XML to file
    tag = node.tag
    if tag is Comment:
        file.write("<!-- %s -->" % _escape_cdata(node.text, encoding))
    elif tag is ProcessingInstruction:
        file.write("<?%s?>" % _escape_cdata(node.text, encoding))
    else:
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
                        if not preserve_meldids:
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
                _write(file, n, encoding, namespaces, preserve_meldids)
            file.write("</" + _encode(tag, encoding) + ">")
        else:
            file.write(" />")
        for k, v in xmlns_items:
            del namespaces[v]
    if node.tail:
        file.write(_escape_cdata(node.tail, encoding))

_HTMLTAGS_EMPTY    = ['area', 'base', 'basefont', 'br', 'col', 'frame',
                      'hr', 'img', 'input', 'isindex', 'link', 'meta',
                      'param']
_HTMLTAGS_NOESCAPE = ['script', 'style']
_HTMLATTRS_BOOLEAN = ['selected', 'checked', 'compact', 'declare',
                      'defer', 'disabled', 'ismap', 'multiple', 'nohref',
                      'noresize', 'noshade', 'nowrap']

def _write_html(file, node, encoding, namespaces, preserve_meldids):
    # write XML to file
    tag = node.tag
    if tag is Comment:
        file.write("<!-- %s -->" % _escape_cdata(node.text, encoding))
    elif tag is ProcessingInstruction:
        file.write("<?%s?>" % _escape_cdata(node.text, encoding))
    else:
        if tag.startswith(_XHTML_PREFIX):
            tag = tag[len(_XHTML_PREFIX):]
        items = node.items()
        xmlns_items = [] # new namespaces in this scope
        try:
            if isinstance(tag, QName) or tag[:1] == "{":
                tag, xmlns = fixtag(tag, namespaces)
                if xmlns: xmlns_items.append(xmlns)
        except TypeError:
            _raise_serialization_error(tag)
        file.write("<" + _encode(tag, encoding))
        if items or xmlns_items:
            items.sort() # lexical order
            for k, v in items:
                try:
                    if isinstance(k, QName) or k[:1] == "{":
                        if not preserve_meldids:
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
                file.write(_escape_cdata(node.text, encoding))
            for n in node:
                _write_html(file, n, encoding, namespaces, preserve_meldids)
            file.write("</" + _encode(tag, encoding) + ">")
        else:
            if node.tag.lower() in _HTMLTAGS_EMPTY:
                file.write('>')
            else:
                file.write('>')
                file.write("</" + _encode(tag, encoding) + ">")
        for k, v in xmlns_items:
            del namespaces[v]
    if node.tail:
        file.write(_escape_cdata(node.tail, encoding))


def test(filename):
    root = parse(open(filename, 'r'))
    ob = root.meld['tr']
    values = []
    for thing in range(0, 20):
        values.append((str(thing), str(thing)))
    for tr, (name, desc) in ob.meld.repeat(values):
        tr.meld['td1'].text = name
        tr.meld['td2'].text = desc
    from cStringIO import StringIO
    write(root, StringIO())
    
if __name__ == '__main__':
    import sys
    filename = sys.argv[1]
    import timeit
    t = timeit.Timer("test('%s')" % filename, "from __main__ import test")
    print t.timeit(300) / 300
    
    
