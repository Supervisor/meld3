#include <Python.h>

static PyObject *PySTR__class__, *PySTR__dict__, *PySTR_children;
static PyObject *PySTRattrib, *PySTRparent, *PySTR_MELD_ID;
static PyObject *PySTRtag, *PySTRtext, *PySTRtail;

static PyObject*
clone(PyObject *node, PyObject *parent)
{

    PyObject *klass    = PyObject_GetAttr(node, PySTR__class__);
    PyObject *children = PyObject_GetAttr(node, PySTR_children);
    PyObject *text     = PyObject_GetAttr(node, PySTRtext);
    PyObject *tail     = PyObject_GetAttr(node, PySTRtail);
    /*PyObject *dict     = PyObject_GetAttr(node, PySTR__dict__);*/
    PyObject *tag      = PyObject_GetAttr(node, PySTRtag);
    PyObject *attrib   = PyObject_GetAttr(node, PySTRattrib);
   
    /* element = self.__class__(self.tag, self.attrib.copy()) */

    PyObject *newdict = PyDict_New();
    PyObject *newchildren = PyList_New(0);
    PyObject *attrib_copy = PyDict_Copy(attrib);

    PyDict_SetItem(newdict, PySTR_children, newchildren);
    PyDict_SetItem(newdict, PySTRattrib, attrib_copy);
    PyDict_SetItem(newdict, PySTRtext, text);
    PyDict_SetItem(newdict, PySTRtail, tail);
    PyDict_SetItem(newdict, PySTRtag, tag);
    
    /* element.tail = self.tail */
    /*PyObject_SetAttr(element, PySTRtail, tail);
    PyObject *args = PyTuple_Pack(2, tag, attrib_copy);
    PyObject *element = PyObject_CallObject(klass, args);*/

    PyObject *element = PyInstance_NewRaw(klass, newdict);
 
    /* element.text = self.text */
    
    /*PyObject_SetAttr(element, PySTRtext, text);*/
    
    /* element.tail = self.tail */
    /*PyObject_SetAttr(element, PySTRtail, tail);*/
    
    /* if parent is not None:
       parent._children.append(element)
       element.parent = parent */
    
    if (parent != Py_None) {
        PyObject *pchildren = PyObject_GetAttr(parent, PySTR_children);
	PyList_Append(pchildren, element);
	PyObject_SetAttr(element, PySTRparent, parent);
	}
    
    /* for child in self._children:
       child.clone(element) */

    int len, i;
    len = PyList_Size(children);
    for (i = 0; i < len; i++) {
	PyObject *child = PyList_GetItem(children, i);
	clone(child, element);
	}
    
    return element;

}

static PyObject*
clonehandler(PyObject *self, PyObject *args)
{
    PyObject *node, *parent;
	
    if (!PyArg_ParseTuple(args, "OO:clone", &node, &parent)) {
	return NULL;
    }
    
    return clone(node, parent);
}

static char clonehandler_doc[] =
"clone(node, parent=None)\n			\
\n\
Return a clone of the meld3 node named by node.  If parent is not None, \n\
append the clone to the parent.\n";

static PyObject*
getiterator(PyObject *node, PyObject *list) {
    Py_INCREF(node);
    PyList_Append(list, node);

    PyObject *children = PyObject_GetAttr(node, PySTR_children);
    int len, i;
    len = PyList_Size(children);

    for (i = 0; i < len; i++) {
	PyObject *child = PyList_GetItem(children, i);
        Py_INCREF(child);
        getiterator(child, list);
	}
    
    return list;
}

static PyObject*
getiteratorhandler(PyObject *self, PyObject *args)
{
    PyObject *node;
	
    if (!PyArg_ParseTuple(args, "O:getiterator", &node)) {
	return NULL;
    }
    PyObject *list = PyList_New(0);
    PyObject *result = getiterator(node, list);
    return result;
}

static char getiteratorhandler_doc[] =
"getiterator(node)\n\
\n\
Returns an iterator for the node.\n";

static char* _MELD_ID = "{http://www.plope.com/software/meld3}id";
/*static PyObject *PySTR_MELD_ID = PyString_FromString(_MELD_ID);*/

static PyObject*
findmeld(PyObject *node, PyObject *name) {
    PyObject *attrib = PyObject_GetAttr(node, PySTRattrib);
    PyObject *meldid = PyDict_GetItem(attrib, PySTR_MELD_ID);
    PyObject *result = Py_None;

    if (meldid != NULL) {
        if ( PyUnicode_Compare(meldid, name) == 0) {
	    result = node;
	}
    }

    if (result == Py_None) {
	int len, i;
	PyObject *children = PyObject_GetAttr(node, PySTR_children);
	len = PyList_Size(children);
	for (i = 0; i < len; i++) {
	    PyObject *child = PyList_GetItem(children, i);
	    Py_INCREF(child);
	    result = findmeld(child, name);
            if (result != Py_None) {
		break;
	    }
	    Py_DECREF(child);
	}
    }

    return result;
    
}

static PyObject*
findmeldhandler(PyObject *self, PyObject *args)
{
    PyObject *node, *name;
	
    if (!PyArg_ParseTuple(args, "OO:findmeld", &node, &name)) {
	return NULL;
    }
    PyObject *result = findmeld(node, name);
    Py_INCREF(result);
    return result;
}

static char findmeldhandler_doc[] =
"findmeld(node, meldid)\n\
\n\
Return a meld node or None.\n";

static PyMethodDef methods[] = {
    {"clone", clonehandler, METH_VARARGS, clonehandler_doc},
    {"getiterator", getiteratorhandler, METH_VARARGS, getiteratorhandler_doc},
    {"findmeld", findmeldhandler, METH_VARARGS, findmeldhandler_doc},
    {NULL, NULL}
};

PyMODINIT_FUNC
initcmeld3(void) 
{
#define DEFINE_STRING(s) \
    if (!(PySTR##s = PyString_FromString(#s))) return 
    DEFINE_STRING(__class__); 
    DEFINE_STRING(__dict__); 
    DEFINE_STRING(_children);
    DEFINE_STRING(parent);
    DEFINE_STRING(tag);
    DEFINE_STRING(attrib);
    DEFINE_STRING(text);
    DEFINE_STRING(tail);
#undef DEFINE_STRING
    PySTR_MELD_ID = PyString_FromString(_MELD_ID);
    if (!PySTR_MELD_ID) {
	return;
    }
    Py_InitModule3("cmeld3", methods,
		   "C helpers for meld3");
}
