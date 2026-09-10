from cpython.unicode cimport PyUnicode_DecodeUTF8
from xml.dom import HierarchyRequestErr, NotFoundErr

import re

_HTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
_NODE_NAMES = {3: "#text", 4: "#cdata-section", 8: "#comment", 9: "#document", 11: "#document-fragment"}
_ASCII_WS = " \t\r\n"
_RAW_TEXT = frozenset(["SCRIPT", "STYLE", "XMP", "IFRAME", "NOEMBED", "NOFRAMES", "PLAINTEXT"])
_SERIALIZER_VOID = frozenset([
    "area", "base", "basefont", "bgsound", "br", "col", "embed", "frame", "hr",
    "img", "input", "keygen", "link", "meta", "param", "source", "track", "wbr",
])


cdef inline str _decode(const lxb_char_t *data, size_t length):
    if data == NULL:
        return ""
    return PyUnicode_DecodeUTF8(<const char *>data, length, "surrogatepass")


cdef tuple _html_tag_names():
    cdef size_t tag, length = 0
    cdef const lxb_char_t *data
    names = []
    for tag in range(LXB_TAG__LAST_ENTRY):
        data = lxb_tag_name_by_id(tag, &length)
        names.append(_decode(data, length).upper())
    return tuple(names)


cdef tuple _HTML_TAG_NAMES = _html_tag_names()


cdef class _Document:
    cdef lxb_html_document_t *_doc
    cdef dict _cache
    cdef list _retained
    cdef bint _scripting_enabled

    def __cinit__(self):
        self._doc = lxb_html_document_create()
        if self._doc == NULL:
            raise MemoryError("Cannot allocate HTML document")
        self._cache = {}
        self._retained = []
        self._scripting_enabled = True

    def __dealloc__(self):
        if self._doc != NULL:
            lxb_html_document_destroy(self._doc)


cdef class Node:
    """A DOM node backed directly by its owning native HTML document."""

    cdef dict __dict__
    cdef _Document _document
    cdef lxb_dom_node_t *_node
    cdef object _children_cache
    cdef object _value
    cdef readonly int nodeType
    cdef readonly str nodeName
    cdef readonly object namespaceURI
    cdef public bint isCode, isBlock, isBlank, _metadata_valid
    cdef public object flankingWhitespace
    cdef public object _text_index, _blank_text, _has_void, _has_meaningful
    cdef public object _element_indices
    cdef public Py_ssize_t _text_start, _text_end, _leading_end, _trailing_start

    def __init__(self, node, cache=None):
        cdef _Document document = _Document()
        cdef Node imported = _import_dom(document, node, True)
        self._initialize(document, imported._node)

    cdef void _initialize(self, _Document document, lxb_dom_node_t *node) except *:
        cdef size_t length = 0
        cdef const lxb_char_t *data
        self._document = document
        self._node = node
        self.nodeType = node.type
        self.namespaceURI = None
        if node.type == 1:
            if node.ns == LXB_NS_HTML:
                self.namespaceURI = _HTML_NAMESPACE
            else:
                data = lxb_ns_by_id(node.owner_document.ns, node.ns, &length)
                if length:
                    self.namespaceURI = _decode(data, length)
            if (node.ns == LXB_NS_HTML and node.local_name < LXB_TAG__LAST_ENTRY
                    and (<lxb_dom_element_t *>node).qualified_name == 0):
                self.nodeName = _HTML_TAG_NAMES[node.local_name]
            else:
                data = lxb_dom_element_qualified_name(<lxb_dom_element_t *>node, &length)
                self.nodeName = _decode(data, length)
                if self.namespaceURI in (None, _HTML_NAMESPACE):
                    self.nodeName = self.nodeName.upper()
        elif node.type == 7:
            data = lxb_dom_processing_instruction_target(<lxb_dom_processing_instruction_t *>node, &length)
            self.nodeName = _decode(data, length)
        elif node.type == 10:
            data = lxb_dom_document_type_name(<lxb_dom_document_type_t *>node, &length)
            self.nodeName = _decode(data, length)
        else:
            self.nodeName = _NODE_NAMES.get(node.type, "")
        document._cache[<uintptr_t>node] = self
        node.user = <void *>self

    @property
    def _dom(self):
        return self

    def _wrap(self, node):
        return node

    @property
    def tagName(self):
        return self.nodeName

    @property
    def localName(self):
        cdef size_t length = 0
        cdef const lxb_char_t *data
        if self.nodeType != 1:
            return None
        data = lxb_dom_element_qualified_name(<lxb_dom_element_t *>self._node, &length)
        return _decode(data, length).split(":", 1)[-1]

    @property
    def prefix(self):
        return self.nodeName.split(":", 1)[0] if ":" in self.nodeName else None

    @property
    def childNodes(self):
        cdef lxb_dom_node_t *child
        if self._children_cache is None:
            self._children_cache = []
            child = self._node.first_child
            while child != NULL:
                self._children_cache.append(_wrap_native(self._document, child))
                child = child.next
        return self._children_cache

    cpdef Py_ssize_t _child_count(self):
        return len(self.childNodes)

    cpdef Node _child_at(self, Py_ssize_t index):
        cdef list children = self.childNodes
        return children[index] if index < len(children) else None

    @property
    def children(self):
        cdef lxb_dom_node_t *child = self._node.first_child
        result = []
        while child != NULL:
            if child.type == 1:
                result.append(_wrap_native(self._document, child))
            child = child.next
        return result

    @property
    def parentNode(self):
        return _wrap_native(self._document, self._node.parent)

    @property
    def previousSibling(self):
        return _wrap_native(self._document, self._node.prev)

    @property
    def nextSibling(self):
        return _wrap_native(self._document, self._node.next)

    @property
    def firstChild(self):
        return _wrap_native(self._document, self._node.first_child)

    @property
    def lastChild(self):
        return _wrap_native(self._document, self._node.last_child)

    @property
    def lastElementChild(self):
        cdef lxb_dom_node_t *child = self._node.last_child
        while child != NULL and child.type != 1:
            child = child.prev
        return _wrap_native(self._document, child)

    @property
    def ownerDocument(self):
        if self.nodeType == 9:
            return None
        return _wrap_native(self._document, <lxb_dom_node_t *>self._node.owner_document)

    @property
    def _scripting_enabled(self):
        return self._document._scripting_enabled

    @_scripting_enabled.setter
    def _scripting_enabled(self, enabled):
        self._document._scripting_enabled = bool(enabled)

    @property
    def nodeValue(self):
        cdef lxb_dom_character_data_t *data
        if self.nodeType not in (3, 4, 7, 8):
            return None
        if self._value is None:
            data = <lxb_dom_character_data_t *>self._node
            self._value = _decode(data.data.data, data.data.length)
        return self._value

    @nodeValue.setter
    def nodeValue(self, value):
        if self.nodeType in (3, 4, 7, 8):
            self._set_data(value)

    @property
    def data(self):
        if self.nodeType not in (3, 4, 7, 8):
            raise AttributeError("data")
        return self.nodeValue

    @data.setter
    def data(self, value):
        if self.nodeType not in (3, 4, 7, 8):
            raise AttributeError("data")
        self._set_data(value)

    cdef void _set_data(self, str value) except *:
        cdef bytes encoded
        cdef lxb_dom_character_data_t *data = <lxb_dom_character_data_t *>self._node
        if self._value is not None and self._value == value:
            return
        encoded = value.encode("utf-8", "surrogatepass")
        if lxb_dom_character_data_replace(data, <const lxb_char_t *>encoded, len(encoded), 0, data.data.length) != 0:
            raise MemoryError("Cannot replace DOM text")
        self._value = value
        self._invalidate()

    @property
    def textContent(self):
        cdef Node node
        if self.nodeType in (3, 4, 7, 8):
            return self.nodeValue
        if self._metadata_valid:
            return self._text_index[0][self._text_start:self._text_end]
        parts = []
        pending = list(reversed(self.childNodes))
        while pending:
            node = pending.pop()
            if node.nodeType in (3, 4):
                parts.append(node.nodeValue)
            else:
                pending.extend(reversed(node.childNodes))
        return "".join(parts)

    @textContent.setter
    def textContent(self, value):
        if self.nodeType in (3, 4, 7, 8):
            self._set_data(value)
            return
        for child in list(self.childNodes):
            self.removeChild(child)
        if value:
            self.appendChild(self.createTextNode(value))
        self._invalidate()

    @property
    def attributes(self):
        return _Attributes(self) if self.nodeType == 1 else None

    cpdef getAttribute(self, str name):
        cdef bytes encoded
        cdef lxb_dom_attr_t *attribute
        if self.nodeType != 1:
            return None
        if self.namespaceURI in (None, _HTML_NAMESPACE):
            name = name.lower()
        encoded = name.encode("utf-8", "surrogatepass")
        attribute = lxb_dom_element_attr_by_name(<lxb_dom_element_t *>self._node, <const lxb_char_t *>encoded, len(encoded))
        if attribute == NULL:
            return None
        if attribute.value == NULL:
            return ""
        return _decode(attribute.value.data, attribute.value.length)

    cpdef bint hasAttribute(self, str name):
        return self.getAttribute(name) is not None

    cpdef setAttribute(self, str name, value):
        cdef bytes key, encoded
        if self.nodeType != 1:
            raise AttributeError("setAttribute")
        if self.namespaceURI in (None, _HTML_NAMESPACE):
            name = name.lower()
        key = name.encode("utf-8", "surrogatepass")
        encoded = str(value).encode("utf-8", "surrogatepass")
        if lxb_dom_element_set_attribute(<lxb_dom_element_t *>self._node, <const lxb_char_t *>key, len(key), <const lxb_char_t *>encoded, len(encoded)) == NULL:
            raise MemoryError("Cannot set DOM attribute")

    @property
    def className(self):
        return self.getAttribute("class") or ""

    @property
    def id(self):
        return self.getAttribute("id") or ""

    @property
    def content(self):
        if self._node.type == 1 and self._node.ns == LXB_NS_HTML and self._node.local_name == LXB_TAG_TEMPLATE:
            return _wrap_native(self._document, <lxb_dom_node_t *>(<lxb_html_template_element_t *>self._node).content)
        return None

    @property
    def _turndown_content(self):
        content = self.content
        if content is None:
            raise AttributeError("_turndown_content")
        return content

    cpdef list getElementsByTagName(self, str name):
        cdef Node node
        cdef str html_name = name.upper()
        result = []
        pending = list(reversed(self.childNodes))
        while pending:
            node = pending.pop()
            expected = html_name if node.namespaceURI in (None, _HTML_NAMESPACE) else name
            if node.nodeType == 1 and (name == "*" or node.nodeName == expected):
                result.append(node)
            pending.extend(reversed(node.childNodes))
        return result

    def getElementById(self, value):
        return next((node for node in self.getElementsByTagName("*") if node.getAttribute("id") == value), None)

    cpdef Node removeChild(self, Node child):
        if child._node.parent != self._node:
            raise NotFoundErr("Node is not a child")
        lxb_dom_node_remove_wo_events(child._node)
        if self._children_cache is not None:
            self._children_cache.remove(child)
        self._invalidate()
        return child

    cpdef Node appendChild(self, Node child):
        cdef lxb_dom_node_t *ancestor = self._node
        cdef Node parent
        if self.nodeType not in (1, 9, 11):
            raise HierarchyRequestErr("This node cannot contain children")
        while ancestor != NULL:
            if ancestor == child._node:
                raise HierarchyRequestErr("A node cannot contain itself")
            ancestor = ancestor.parent
        if child.nodeType == 11:
            for item in list(child.childNodes):
                self.appendChild(item)
            return child
        parent = child.parentNode
        if parent is not None:
            parent.removeChild(child)
        if child._document is not self._document and child._document not in self._document._retained:
            self._document._retained.append(child._document)
            # ponytail: moved nodes retain both arenas; adopt allocations if
            # long-lived cross-document moves make arena retention significant.
            child._document._retained.append(self._document)
        lxb_dom_node_insert_child_wo_events(self._node, child._node)
        if self._children_cache is not None:
            self._children_cache.append(child)
        self._invalidate()
        return child

    @property
    def element_index(self):
        cdef Node parent = self.parentNode
        if parent._element_indices is None:
            parent._element_indices = {id(child): index for index, child in enumerate(parent.children)}
        return parent._element_indices[id(self)]

    cpdef _invalidate(self):
        cdef Node node = self
        while node is not None:
            node._element_indices = None
            if not node._metadata_valid:
                break
            node._metadata_valid = False
            node._blank_text = node._has_void = node._has_meaningful = None
            node._text_index = None
            node = node.parentNode

    cpdef Node cloneNode(self, bint deep=False):
        return _import_dom(_Document(), self, deep)

    cpdef Node createTextNode(self, str value):
        cdef bytes encoded = value.encode("utf-8", "surrogatepass")
        cdef lxb_dom_node_t *node = <lxb_dom_node_t *>lxb_dom_document_create_text_node(&self._document._doc.dom_document, <const lxb_char_t *>encoded, len(encoded))
        if node == NULL:
            raise MemoryError("Cannot allocate DOM text")
        return _wrap_native(self._document, node)

    def createDocumentFragment(self):
        cdef lxb_dom_node_t *node = <lxb_dom_node_t *>lxb_dom_document_create_document_fragment(&self._document._doc.dom_document)
        if node == NULL:
            raise MemoryError("Cannot allocate DOM fragment")
        return _wrap_native(self._document, node)

    @property
    def name(self):
        return self.nodeName

    @property
    def target(self):
        return self.nodeName

    @property
    def publicId(self):
        cdef size_t length = 0
        cdef const lxb_char_t *data
        if self.nodeType != 10:
            raise AttributeError("publicId")
        data = lxb_dom_document_type_public_id(<lxb_dom_document_type_t *>self._node, &length)
        return _decode(data, length)

    @property
    def systemId(self):
        cdef size_t length = 0
        cdef const lxb_char_t *data
        if self.nodeType != 10:
            raise AttributeError("systemId")
        data = lxb_dom_document_type_system_id(<lxb_dom_document_type_t *>self._node, &length)
        return _decode(data, length)

    @property
    def outerHTML(self):
        return _serialize([self])

    @property
    def innerHTML(self):
        return _serialize((self.content or self).childNodes)

    def toxml(self):
        return _serialize([self])


cdef Node _wrap_native(_Document document, lxb_dom_node_t *node):
    cdef Node wrapped
    if node == NULL:
        return None
    if node.user != NULL:
        return <Node><object>node.user
    wrapped = Node.__new__(Node)
    wrapped._initialize(document, node)
    return wrapped


cdef class _Attribute:
    cdef Node _owner
    cdef lxb_dom_attr_t *_attr

    @property
    def name(self):
        cdef size_t length = 0
        cdef const lxb_char_t *data = lxb_dom_attr_qualified_name(self._attr, &length)
        return _decode(data, length)

    @property
    def localName(self):
        cdef size_t length = 0
        cdef const lxb_char_t *data = lxb_dom_attr_local_name(self._attr, &length)
        return _decode(data, length)

    @property
    def namespaceURI(self):
        cdef size_t length = 0
        cdef const lxb_char_t *data = lxb_ns_by_id(self._attr.node.owner_document.ns, self._attr.node.ns, &length)
        return _decode(data, length) if length else None

    @property
    def value(self):
        return _decode(self._attr.value.data, self._attr.value.length) if self._attr.value != NULL else ""

    @value.setter
    def value(self, value):
        cdef bytes encoded = str(value).encode("utf-8", "surrogatepass")
        if lxb_dom_attr_set_value(self._attr, <const lxb_char_t *>encoded, len(encoded)) != 0:
            raise MemoryError("Cannot set DOM attribute")


cdef class _Attributes:
    cdef Node _node

    def __init__(self, Node node):
        self._node = node

    def values(self):
        cdef lxb_dom_attr_t *attr = (<lxb_dom_element_t *>self._node._node).first_attr
        cdef _Attribute value
        values = []
        while attr != NULL:
            value = _Attribute.__new__(_Attribute)
            value._owner = self._node
            value._attr = attr
            values.append(value)
            attr = attr.next
        return values

    def keys(self):
        return [attribute.name for attribute in self.values()]

    def items(self):
        return [(attribute.name, attribute.value) for attribute in self.values()]

    def __len__(self):
        cdef lxb_dom_attr_t *attr = (<lxb_dom_element_t *>self._node._node).first_attr
        cdef Py_ssize_t count = 0
        while attr != NULL:
            count += 1
            attr = attr.next
        return count

    @property
    def length(self):
        return len(self)

    def __getitem__(self, name):
        attribute = self.getNamedItem(name)
        if attribute is None:
            raise KeyError(name)
        return attribute

    def getNamedItem(self, name):
        return next((attribute for attribute in self.values() if attribute.name == name), None)

    def item(self, index):
        values = self.values()
        return values[index] if 0 <= index < len(values) else None


cdef Node _import_shallow(_Document owner, object source):
    cdef lxb_dom_document_t *document = &owner._doc.dom_document
    cdef lxb_dom_node_t *node = NULL
    cdef lxb_dom_attr_t *attr
    cdef bytes name, namespace, prefix, data, key, value, public, system
    cdef const lxb_char_t *namespace_pointer
    cdef const lxb_char_t *prefix_pointer
    cdef Node wrapped
    kind = source.nodeType
    if kind == 9:
        node = <lxb_dom_node_t *>document
    elif kind == 1:
        name = (source.localName or source.nodeName).encode("utf-8", "surrogatepass")
        namespace = (source.namespaceURI or "").encode("utf-8", "surrogatepass")
        source_prefix = getattr(source, "prefix", None)
        if not source_prefix and ":" in source.nodeName:
            source_prefix = source.nodeName.split(":", 1)[0]
        prefix = (source_prefix or "").encode("utf-8", "surrogatepass")
        namespace_pointer = <const lxb_char_t *>namespace if namespace else NULL
        prefix_pointer = <const lxb_char_t *>prefix if prefix else NULL
        node = <lxb_dom_node_t *>lxb_dom_element_create(document, <const lxb_char_t *>name, len(name),
            namespace_pointer, len(namespace), prefix_pointer, len(prefix), NULL, 0, False)
        if node == NULL:
            raise MemoryError("Cannot import DOM element")
        if lxb_dom_element_qualified_name_set(<lxb_dom_element_t *>node, prefix_pointer, len(prefix),
                <const lxb_char_t *>name, len(name)) != 0:
            raise MemoryError("Cannot preserve DOM element name")
        for attribute in source.attributes.values():
            key = attribute.name.encode("utf-8", "surrogatepass")
            value = attribute.value.encode("utf-8", "surrogatepass")
            attr = lxb_dom_element_set_attribute(<lxb_dom_element_t *>node, <const lxb_char_t *>key, len(key),
                <const lxb_char_t *>value, len(value))
            if attr == NULL:
                raise MemoryError("Cannot import DOM attribute")
            if attribute.namespaceURI:
                namespace = attribute.namespaceURI.encode("utf-8", "surrogatepass")
                if lxb_dom_attr_set_name_ns(attr, <const lxb_char_t *>namespace, len(namespace),
                    <const lxb_char_t *>key, len(key), False) != 0:
                    raise MemoryError("Cannot import attribute namespace")
    elif kind == 11:
        node = <lxb_dom_node_t *>lxb_dom_document_create_document_fragment(document)
    elif kind in (3, 4, 8):
        data = source.nodeValue.encode("utf-8", "surrogatepass")
        if kind == 3:
            node = <lxb_dom_node_t *>lxb_dom_document_create_text_node(document, <const lxb_char_t *>data, len(data))
        elif kind == 8:
            node = <lxb_dom_node_t *>lxb_dom_document_create_comment(document, <const lxb_char_t *>data, len(data))
        else:
            node = <lxb_dom_node_t *>lxb_dom_document_create_cdata_section(document, <const lxb_char_t *>b"", 0)
    elif kind == 7:
        name = source.target.encode("utf-8", "surrogatepass")
        node = <lxb_dom_node_t *>lxb_dom_document_create_processing_instruction(document,
            <const lxb_char_t *>name, len(name), <const lxb_char_t *>b"", 0)
    elif kind == 10:
        name = source.name.encode("utf-8", "surrogatepass")
        public = (source.publicId or "").encode("utf-8", "surrogatepass")
        system = (source.systemId or "").encode("utf-8", "surrogatepass")
        node = <lxb_dom_node_t *>lxb_dom_document_type_create(document, <const lxb_char_t *>name, len(name),
            <const lxb_char_t *>public, len(public), <const lxb_char_t *>system, len(system), NULL)
    else:
        raise TypeError("Unsupported DOM node type")
    if node == NULL:
        raise MemoryError("Cannot import DOM node")
    wrapped = _wrap_native(owner, node)
    if kind in (4, 7):
        wrapped._set_data(source.nodeValue)
    return wrapped


cdef Node _import_dom(_Document owner, object source, bint deep):
    cdef Node target, child_target, root
    source_document = source if source.nodeType == 9 else source.ownerDocument
    if source_document is not None:
        owner._scripting_enabled = bool(getattr(source_document, "_scripting_enabled", True))
    root = _import_shallow(owner, source)
    pending = [(source, root)] if deep else []
    while pending:
        source, target = pending.pop()
        for child in source.childNodes:
            child_target = _import_shallow(owner, child)
            lxb_dom_node_insert_child_wo_events(target._node, child_target._node)
            pending.append((child, child_target))
        content = getattr(source, "_turndown_content", None)
        if content is not None and target.content is not None:
            pending.append((content, target.content))
    return root


cpdef Node parse_html(str text):
    cdef _Document document = _Document()
    cdef bytes encoded = text.encode("utf-8", "surrogatepass")
    cdef const lxb_char_t *data = <const lxb_char_t *>encoded
    cdef size_t length = len(encoded)
    cdef lxb_status_t status
    with nogil:
        status = lxb_html_document_parse(document._doc, data, length)
    if status != 0:
        raise ValueError("HTML parser failed")
    return _wrap_native(document, <lxb_dom_node_t *>&document._doc.dom_document)


cpdef Node root_node(input, options):
    cdef Node root, node
    if isinstance(input, str):
        document = parse_html('<x-turndown id="turndown-root">' + input + '</x-turndown>')
        pending = [document]
        while pending:
            root = pending.pop()
            if root.nodeType == 1 and root.nodeName == "X-TURNDOWN" and root.getAttribute("id") == "turndown-root":
                break
            pending.extend(reversed(root.childNodes))
        else:
            raise TypeError("Cannot read properties of null (reading 'firstChild')")
    else:
        root = _import_dom(_Document(), input, True)
    collapse_whitespace(root, bool(_option(options, "preformattedCode")))
    _cache_blankness(root)
    return root


def _escape_html(value, attribute=False):
    value = (
        value.replace("&", "&amp;")
        .replace("\xa0", "&nbsp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return value.replace('"', "&quot;") if attribute else value


def _escape_closing_raw_tag(text, name):
    cdef Py_ssize_t previous = 0
    cdef Py_ssize_t offset = 0
    closing = "</" + name
    if closing not in text.lower():
        return text
    parts = list(text)
    for match in re.finditer(re.escape(closing), text, re.IGNORECASE | re.ASCII):
        # Domino indexes a code-point array with UTF-16 regex offsets.
        offset += (
            len(text[previous : match.start()].encode("utf-16-le", "surrogatepass"))
            // 2
        )
        if offset >= len(parts):
            parts.extend([""] * (offset + 1 - len(parts)))
        parts[offset] = "&lt;"
        previous = match.start()
    return "".join(parts)


def _serialize(nodes):
    output = []
    pending = list(reversed(nodes))
    while pending:
        node = pending.pop()
        if isinstance(node, str):
            output.append(node)
        elif isinstance(node, tuple):
            name, start = node
            content = _escape_closing_raw_tag("".join(output[start:]), name)
            output[start:] = [content, "</" + name + ">"]
        elif node.nodeType == 1:
            html = node.namespaceURI in (None, _HTML_NAMESPACE)
            name = node.nodeName.lower() if html else node.nodeName
            attributes = "".join(
                " " + attribute.name + '="' + _escape_html(attribute.value, True) + '"'
                for attribute in node.attributes.values()
            )
            output.append("<" + name + attributes + ">")
            if not html or name not in _SERIALIZER_VOID:
                pending.append(
                    (name, len(output))
                    if name.upper() in _RAW_TEXT
                    else "</" + name + ">"
                )
                source = getattr(node, "_turndown_content", node)
                pending.extend(reversed(source.childNodes))
        elif node.nodeType in (3, 4):
            parent = node.parentNode
            raw = (
                parent is not None
                and parent.namespaceURI in (None, _HTML_NAMESPACE)
                and (
                    parent.nodeName.upper() in _RAW_TEXT
                    or (
                        parent.nodeName.upper() == "NOSCRIPT"
                        and getattr(parent.ownerDocument, "_scripting_enabled", True)
                    )
                )
            )
            output.append(node.nodeValue if raw else _escape_html(node.nodeValue))
        elif node.nodeType == 8:
            output.append("<!--" + re.sub(r"(--!?)>", r"\1&gt;", node.data) + "-->")
        elif node.nodeType == 10:
            output.append("<!DOCTYPE " + node.name + ">")
        elif node.nodeType == 7:
            output.append(
                "<?" + node.target + " " + node.data.replace(">", "&gt;") + "?>"
            )
        else:
            pending.extend(reversed(node.childNodes))
    return "".join(output)


def _option(options, name):
    return (
        options.get(name) if isinstance(options, dict) else getattr(options, name, None)
    )




cdef inline bint _js_whitespace(Py_UCS4 char):
    return (char == 32 or 9 <= char <= 13 or 0x2000 <= char <= 0x200a
            or char in (0xa0, 0x1680, 0x2028, 0x2029, 0x202f, 0x205f, 0x3000, 0xfeff))


def _cache_blankness(Node root):
    cdef Node node, child
    cdef Py_ssize_t offset = 0
    cdef Py_ssize_t leading_end, trailing_start, length, left, right
    cdef bint blank, has_void, has_meaningful
    cdef str text
    cdef int kind
    cdef void *data
    # One shared string keeps deeply nested markup from storing a copy of each
    # ancestor's text. Offsets also make whitespace boundary checks constant-time.
    text_index = [""]
    text_parts = []
    pending = [(root, None)]
    while pending:
        node, children = pending.pop()
        if children is None:
            node._text_start = offset
            node._text_index = text_index
            node._metadata_valid = True
            if node.nodeType in (3, 4):
                text = node.nodeValue
                text_parts.append(text)
                length = PyUnicode_GET_LENGTH(text)
                kind = PyUnicode_KIND(text)
                data = PyUnicode_DATA(text)
                left = 0
                while left < length and _js_whitespace(PyUnicode_READ(kind, data, left)):
                    left += 1
                right = length if left < length else 0
                while right > left and _js_whitespace(PyUnicode_READ(kind, data, right - 1)):
                    right -= 1
                offset += length
                node._text_end = offset
                node._blank_text = left == length
                node._has_void = node._has_meaningful = False
                node._leading_end = node._text_start + left
                node._trailing_start = node._text_start + right
                continue
            children = node.childNodes
            if children:
                pending.append((node, children))
                pending.extend((child, None) for child in reversed(children))
                continue
        node._text_end = offset
        blank = True
        has_void = has_meaningful = False
        leading_end = trailing_start = offset
        for child in children:
            if not child._blank_text:
                if blank:
                    leading_end = child._leading_end
                trailing_start = child._trailing_start
                blank = False
            name = child.nodeName
            has_void = has_void or child._has_void or name in VOID_ELEMENTS
            has_meaningful = (
                has_meaningful
                or child._has_meaningful
                or name in MEANINGFUL_WHEN_BLANK_ELEMENTS
            )
        node._blank_text = blank
        node._has_void = has_void
        node._has_meaningful = has_meaningful
        node._leading_end = leading_end
        node._trailing_start = trailing_start
    text_index[0] = "".join(text_parts)


cpdef Node decorate_node(Node node, options):
    cdef Node parent
    name = node.nodeName
    node.isBlock = name in BLOCK_ELEMENTS
    parent = node.parentNode
    node.isCode = name == "CODE" or bool(parent and parent.isCode)
    blank_text = getattr(node, "_blank_text", None)
    if blank_text is None:
        blank_text = not js_trim(node.textContent)
    node.isBlank = (
        name not in VOID_ELEMENTS
        and name not in MEANINGFUL_WHEN_BLANK_ELEMENTS
        and blank_text
        and not has_void(node)
        and not has_meaningful_when_blank(node)
    )
    node.flankingWhitespace = flanking_whitespace(node, options)
    return node


def edge_whitespace(string):
    leading_end = len(string) - len(string.lstrip(JS_WS))
    leading = string[:leading_end]
    trailing = string[len(string.rstrip(JS_WS)) :] if leading_end != len(string) else ""
    return _edge_parts(leading, trailing)


def _edge_parts(leading, trailing):
    leading_ascii_end = len(leading) - len(leading.lstrip(_ASCII_WS))
    trailing_non_ascii_end = len(trailing.rstrip(_ASCII_WS))
    return {
        "leading": leading,
        "leadingAscii": leading[:leading_ascii_end],
        "leadingNonAscii": leading[leading_ascii_end:],
        "trailing": trailing,
        "trailingNonAscii": trailing[:trailing_non_ascii_end],
        "trailingAscii": trailing[trailing_non_ascii_end:],
    }


cpdef flanking_whitespace(Node node, options):
    cdef Node sibling
    preformatted = _option(options, "preformattedCode")
    if node.isBlock or (preformatted and node.isCode):
        return {"leading": "", "trailing": ""}
    if node._metadata_valid:
        if node._text_start == node._leading_end and (
            node._blank_text or node._trailing_start == node._text_end
        ):
            return {"leading": "", "trailing": ""}
        text = node._text_index[0]
        edges = _edge_parts(
            text[node._text_start : node._leading_end],
            "" if node._blank_text else text[node._trailing_start : node._text_end],
        )
    else:
        edges = edge_whitespace(node.textContent)
    for side in ("leading", "trailing"):
        if not edges[side + "Ascii"]:
            continue
        sibling = node.previousSibling if side == "leading" else node.nextSibling
        if sibling is None:
            continue
        if sibling.nodeType == 3:
            text = sibling.nodeValue
        elif (
            sibling.nodeType == 1
            and not is_block(sibling)
            and not (preformatted and sibling.nodeName == "CODE")
        ):
            if sibling._metadata_valid:
                index = (
                    sibling._text_end - 1 if side == "leading" else sibling._text_start
                )
                text = (
                    sibling._text_index[0][index : index + 1]
                    if sibling._text_end > sibling._text_start
                    else ""
                )
            else:
                text = sibling.textContent
        else:
            continue
        if text.endswith(" ") if side == "leading" else text.startswith(" "):
            edges[side] = edges[side + "NonAscii"]
    return {"leading": edges["leading"], "trailing": edges["trailing"]}


cpdef str _collapse_text(str text):
    if text is None:
        raise TypeError("text must be a string")
    cdef Py_ssize_t length = PyUnicode_GET_LENGTH(text)
    cdef Py_ssize_t index, size = 0
    cdef int kind = PyUnicode_KIND(text)
    cdef void *data = PyUnicode_DATA(text)
    cdef Py_UCS4 char, maxchar = 32
    cdef bint space, previous_space = False, changed = False
    cdef str result
    cdef void *output
    # Count the result before allocating: regex substitution otherwise allocates
    # a Python substring for every word and whitespace run in long prose.
    for index in range(length):
        char = PyUnicode_READ(kind, data, index)
        space = char == 32 or char == 9 or char == 10 or char == 13
        if space:
            changed = changed or previous_space or char != 32
            if not previous_space:
                size += 1
        else:
            size += 1
            if char > maxchar:
                maxchar = char
        previous_space = space
    if not changed:
        return text
    result = PyUnicode_New(size, maxchar)
    output = PyUnicode_DATA(result)
    previous_space = False
    size = 0
    for index in range(length):
        char = PyUnicode_READ(kind, data, index)
        space = char == 32 or char == 9 or char == 10 or char == 13
        if not space or not previous_space:
            PyUnicode_WRITE(PyUnicode_KIND(result), output, size, 32 if space else char)
            size += 1
        previous_space = space
    return result


cdef inline bint _whitespace_pre(Node node, bint preformatted_code):
    name = node.nodeName if type(node) is Node else (<object>node).nodeName
    return name == "PRE" or (preformatted_code and name == "CODE")


cdef Node _next_whitespace_node(Node previous, Node current, bint preformatted_code):
    if ((previous is not None and previous.parentNode is current)
            or _whitespace_pre(current, preformatted_code)):
        return current.nextSibling or current.parentNode
    return current.firstChild or current.nextSibling or current.parentNode


cdef Node _remove_whitespace_node(Node node):
    cdef Node following = node.nextSibling or node.parentNode
    cdef Node parent = node.parentNode
    parent.removeChild(node)
    return following


def collapse_whitespace(Node element, preformatted_code=False):
    """Port of collapse-whitespace by Luc Thevenard (MIT, 2014)."""
    cdef Node previous_text, previous, node, following
    cdef str text, name
    cdef bint keep_leading_ws = False
    cdef bint preformatted = bool(preformatted_code)
    if element.firstChild is None or _whitespace_pre(element, preformatted):
        return
    previous_text = None
    previous = None
    node = _next_whitespace_node(previous, element, preformatted)
    while node is not element:
        node_type = node.nodeType if type(node) is Node else (<object>node).nodeType
        if node_type in (3, 4):
            text = _collapse_text(node.data)
            if (
                (previous_text is None or previous_text.data.endswith(" "))
                and not keep_leading_ws
                and text.startswith(" ")
            ):
                text = text[1:]
            if not text:
                node = _remove_whitespace_node(node)
                continue
            node.data = text
            previous_text = node
        elif node_type == 1:
            name = node.nodeName if type(node) is Node else (<object>node).nodeName
            if name in BLOCK_ELEMENTS or name == "BR":
                if previous_text is not None:
                    previous_text.data = previous_text.data.removesuffix(" ")
                previous_text = None
                keep_leading_ws = False
            elif name in VOID_ELEMENTS or _whitespace_pre(node, preformatted):
                previous_text = None
                keep_leading_ws = True
            elif previous_text is not None:
                keep_leading_ws = False
        else:
            node = _remove_whitespace_node(node)
            continue
        following = _next_whitespace_node(previous, node, preformatted)
        previous, node = node, following
    if previous_text is not None:
        previous_text.data = previous_text.data.removesuffix(" ")
        if not previous_text.data:
            _remove_whitespace_node(previous_text)
