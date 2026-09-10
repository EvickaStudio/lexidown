from libc.stdint cimport uintptr_t

cdef extern from "lexbor/html/html.h" nogil:
    ctypedef unsigned char lxb_char_t
    ctypedef unsigned int lxb_status_t
    ctypedef struct lexbor_hash_t:
        pass
    ctypedef struct lexbor_str_t:
        lxb_char_t *data
        size_t length
    ctypedef struct lxb_dom_node_t:
        uintptr_t local_name
        uintptr_t ns
        lxb_dom_document_t *owner_document
        lxb_dom_node_t *parent
        lxb_dom_node_t *prev
        lxb_dom_node_t *next
        lxb_dom_node_t *first_child
        lxb_dom_node_t *last_child
        void *user
        unsigned int type
    ctypedef struct lxb_dom_document_t:
        lxb_dom_node_t node
        lexbor_hash_t *ns
        bint scripting
    ctypedef struct lxb_html_document_t:
        lxb_dom_document_t dom_document
    ctypedef struct lxb_dom_element_t:
        lxb_dom_node_t node
        uintptr_t qualified_name
        lxb_dom_attr_t *first_attr
    ctypedef struct lxb_dom_attr_t:
        lxb_dom_node_t node
        lexbor_str_t *value
        lxb_dom_attr_t *next
    ctypedef struct lxb_dom_character_data_t:
        lxb_dom_node_t node
        lexbor_str_t data
    ctypedef struct lxb_dom_text_t:
        pass
    ctypedef struct lxb_dom_comment_t:
        pass
    ctypedef struct lxb_dom_cdata_section_t:
        pass
    ctypedef struct lxb_dom_document_fragment_t:
        pass
    ctypedef struct lxb_dom_processing_instruction_t:
        pass
    ctypedef struct lxb_dom_document_type_t:
        pass
    lxb_html_document_t *lxb_html_document_create()
    lxb_html_document_t *lxb_html_document_destroy(lxb_html_document_t *)
    lxb_status_t lxb_html_document_parse(lxb_html_document_t *, const lxb_char_t *, size_t)
    void lxb_dom_node_remove_wo_events(lxb_dom_node_t *)
    void lxb_dom_node_insert_child_wo_events(lxb_dom_node_t *, lxb_dom_node_t *)
    lxb_dom_node_t *lxb_dom_document_import_node(lxb_dom_document_t *, lxb_dom_node_t *, bint)
    const lxb_char_t *lxb_dom_element_qualified_name(const lxb_dom_element_t *, size_t *)
    const lxb_char_t *lxb_dom_element_local_name(lxb_dom_element_t *, size_t *)
    lxb_dom_element_t *lxb_dom_element_create(lxb_dom_document_t *, const lxb_char_t *, size_t,
        const lxb_char_t *, size_t, const lxb_char_t *, size_t, const lxb_char_t *, size_t, bint)
    lxb_dom_attr_t *lxb_dom_element_set_attribute(lxb_dom_element_t *, const lxb_char_t *, size_t,
        const lxb_char_t *, size_t)
    lxb_dom_attr_t *lxb_dom_element_attr_by_name(lxb_dom_element_t *, const lxb_char_t *, size_t)
    const lxb_char_t *lxb_dom_attr_qualified_name(const lxb_dom_attr_t *, size_t *)
    const lxb_char_t *lxb_dom_attr_local_name(const lxb_dom_attr_t *, size_t *)
    lxb_status_t lxb_dom_attr_set_value(lxb_dom_attr_t *, const lxb_char_t *, size_t)
    lxb_status_t lxb_dom_character_data_replace(lxb_dom_character_data_t *, const lxb_char_t *, size_t,
        size_t, size_t)
    lxb_dom_text_t *lxb_dom_document_create_text_node(lxb_dom_document_t *, const lxb_char_t *, size_t)
    lxb_dom_comment_t *lxb_dom_document_create_comment(lxb_dom_document_t *, const lxb_char_t *, size_t)
    lxb_dom_cdata_section_t *lxb_dom_document_create_cdata_section(lxb_dom_document_t *, const lxb_char_t *, size_t)
    lxb_dom_document_fragment_t *lxb_dom_document_create_document_fragment(lxb_dom_document_t *)
    lxb_dom_processing_instruction_t *lxb_dom_document_create_processing_instruction(lxb_dom_document_t *,
        const lxb_char_t *, size_t, const lxb_char_t *, size_t)

cdef extern from "lexbor/dom/interfaces/document_type.h" nogil:
    lxb_dom_document_type_t *lxb_dom_document_type_create(lxb_dom_document_t *, const lxb_char_t *, size_t,
        const lxb_char_t *, size_t, const lxb_char_t *, size_t, void *)
    const lxb_char_t *lxb_dom_document_type_name(const lxb_dom_document_type_t *, size_t *)
    const lxb_char_t *lxb_dom_document_type_public_id(lxb_dom_document_type_t *, size_t *)
    const lxb_char_t *lxb_dom_document_type_system_id(lxb_dom_document_type_t *, size_t *)

cdef extern from "lexbor/dom/interfaces/processing_instruction.h" nogil:
    const lxb_char_t *lxb_dom_processing_instruction_target(lxb_dom_processing_instruction_t *, size_t *)

cdef extern from "lexbor/html/interfaces/template_element.h" nogil:
    ctypedef struct lxb_html_template_element_t:
        lxb_dom_document_fragment_t *content

cdef extern from "lexbor/ns/ns.h" nogil:
    enum:
        LXB_NS_HTML
        LXB_NS_SVG
        LXB_NS_MATH
    const lxb_char_t *lxb_ns_by_id(lexbor_hash_t *, uintptr_t, size_t *)

cdef extern from "lexbor/tag/tag.h" nogil:
    enum:
        LXB_TAG_TEMPLATE
        LXB_TAG__LAST_ENTRY
    const lxb_char_t *lxb_tag_name_by_id(uintptr_t, size_t *)

cdef extern from *:
    """
    lxb_status_t lxb_dom_attr_set_name_ns(lxb_dom_attr_t *, const lxb_char_t *,
        size_t, const lxb_char_t *, size_t, bool);
    lxb_status_t lxb_dom_element_qualified_name_set(lxb_dom_element_t *,
        const lxb_char_t *, size_t, const lxb_char_t *, size_t);
    """
    lxb_status_t lxb_dom_attr_set_name_ns(lxb_dom_attr_t *, const lxb_char_t *, size_t,
        const lxb_char_t *, size_t, bint)
    lxb_status_t lxb_dom_element_qualified_name_set(lxb_dom_element_t *, const lxb_char_t *, size_t,
        const lxb_char_t *, size_t)
