# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 UNINETT AS
#
# This file is part of Network Administration Visualized (NAV).
#
# NAV is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.  You should have received a copy of the GNU General Public License
# along with NAV. If not, see <http://www.gnu.org/licenses/>.

"""
Utility class for creating prefix heaps from Prefix objects in NAV. Also
contains ad-hoc serializer methods (self.fields) for API purposes.

"""

from __future__ import unicode_literals
from IPy import IP, IPSet
import json
import copy

from django.core.urlresolvers import reverse, NoReverseMatch

class PrefixHeap(object):
    "Pseudo-heap ordered topologically by prefixes"
    def __init__(self, children=None):
        if children is None:
            children = []
        self.children = children

    @property
    def fields(self):
        "Return the children of the heap as a dictionary"
        payload = {
            "children": [child.fields for child in self.children]
        }
        return payload

    @property
    def is_leaf(self):
        "Whether or not the node has any children"
        return len(self.children) == 0

    @property
    def json_walk(self):
        "JSON output of self.walk"
        return json.dumps(self.walk)

    @property
    def walk(self):
        "List of all the nodes (preorder walk)."
        acc = []
        queue = [self]
        while queue:
            _node = queue.pop()
            # remove children to avoid duplication
            node = copy.deepcopy(_node.fields)
            del node["children"]
            acc.append(node)
            if not _node.is_leaf:
                queue.extend(_node.children)
        return acc

    @property
    def json(self):
        "Exported fields as a JSON map"
        return json.dumps(self.fields)

    @property
    def children_count(self):
        "Number of children (shallow)"
        return len(self.children)

    def add(self, node):
        "Add a node to the heap"
        assert isinstance(node, PrefixHeap), \
            "Can only add classes inheriting from PrefixHeap"
        # first, try adding to children (recursively)
        matches = (child for child in self.children if node in child)
        for child in matches:
            child.add(node)
            return
        # if this fails, add to self
        self.children.append(node)
        self.children.sort()

# To maintain our sanity, we need a somewhat decent contract between the view
# and any controller logic. The solution is to use the Facade pattern, which
# wraps internal complexities (serialization, nested attributes and so on) and
# exposes a clean, non-nested attribute contract (we promise that the field 'x'
# will exist and be populated with some value) etc.

class IpNode(PrefixHeap):
    "PrefixHeap node class"
    def __init__(self, ip_addr):
        super(IpNode, self).__init__()
        self._ip = IP(ip_addr)

    @property
    def ip(self):
        "Return the IP object of the node"
        return self._ip

    # Comparison utilities
    def __contains__(self, other):
        assert isinstance(other, IpNode), \
            "Can only compare with other IpNode elements"
        return other.ip in self.ip

    def __cmp__(self, other):
        assert isinstance(other, IpNode), \
            "Can only compare with other IpNode elements"
        return self.ip.__cmp__(other.ip)

class IpNodeFacade(IpNode):
    "Utility mixin for nodes with IPy.IP objects in in the 'self.ip' field"

    # Class attributes to export to JSON
    FIELDS = [
        "pk",
        "length",
        "net_type",
        "children_pks",
        "ip_version",
        "edit_url",
        "prefix",
        "prefixlen",
        "organization",
        "description",
        "vlan_number",
        "is_mock_node",
        "last_octet"
    ]

    def __init__(self, ip_addr, pk, net_type, sort_fn=None):
        super(IpNodeFacade, self).__init__(ip_addr)
        self.pk = pk
        self.net_type = net_type
        self.sort_fn = sort_fn

    @property
    def fields(self):
        """Return all fields marked for serialization (in self.FIELDS) as a
        Python dict. Also serializes children, creating a nested object.

        """
        payload = {}
        for field in self.FIELDS:
            try:
                value = getattr(self, field, None)
                payload[field] = value
            except AttributeError:
                payload[field] = None
        if self.sort_fn is not None:
            children = [child.fields for child in self.children]
            payload["children"] = sorted(children, key=self.sort_fn)
        else:
            payload["children"] = [child.fields for child in self.children]
        return payload

    @property
    def last_octet(self):
        "Return last octet of address"
        return self.ip.ip & 0xFF

    @property
    def vlan_number(self):
        "Return ID number of associated VLAN"
        return getattr(self, "_vlan_number", None)

    @property
    def ip_version(self):
        "Return the IP family of this prefix (4 or 6)"
        return self.ip.version()

    @property
    def edit_url(self):
        "URL to edit this node in SeedDB, if applicable"
        try:
            return reverse("seeddb-prefix-edit", kwargs={"prefix_id": self.pk})
        except NoReverseMatch:
            return None

    @property
    def prefixlen(self):
        "Return the length of the prefix (e.g. 8 in 10.0.0.0/8)"
        return self.ip.prefixlen()

    @property
    def prefix(self):
        "Return the prefix (as a string)"
        return str(self.ip)

    @property
    def children_pks(self):
        "Return the primary keys of all children"
        if not self.children:
            return []
        return [child.pk for child in self.children]

    @property
    def length(self):
        "Return number of children (in total, e.g. not shallow)"
        deep_count = sum(child.children_count for child in self.children)
        return self.children_count + deep_count

    @property
    def organization(self):
        "The name of the organization connected to the prefix"
        return str(getattr(self, "_organization", ""))

    @property
    def description(self):
        "The description of the prefix"
        return getattr(self, "_description", "")

    @property
    def is_mock_node(self):
        "Marker property for declaring the node as fake (templating reasons)"
        return False

class FauxNode(IpNodeFacade):
    "'Fake' nodes (manual constructor) in a prefix heap"
    def __init__(self, ip_addr, pk, net_type):
        super(FauxNode, self).__init__(ip_addr, pk, net_type)

    @property
    def is_mock_node(self):
        "Marker propery for declaring the node as fake (templating reasons)"
        return True

class PrefixNode(IpNodeFacade):
    "Wrapper node for Prefix results"
    def __init__(self, prefix, sort_fn=None):
        self._prefix = prefix # cache of prefix
        ip_addr = prefix.net_address
        pk = prefix.pk
        net_type = str(prefix.vlan.net_type)
        super(PrefixNode, self).__init__(ip_addr, pk, net_type, sort_fn)
        self._description = prefix.vlan.description
        self._organization = prefix.vlan.organization
        self._vlan_number = prefix.vlan.vlan

def make_prefix_heap(prefixes, initial_children=None, family=None,
                     sort_fn=None, show_available=False):
    """Return a prefix heap of all prefixes. Might optionally filter out IPv4
    and IPv6 as needed

    """
    def accept(prefix):
        "Helper function for filtering prefixes by IP family"
        ip = IP(prefix.net_address)
        if "ipv4" in family and ip.version() == 4:
            return True
        if "ipv6" in family and ip.version() == 6:
            return True
        return False

    heap = PrefixHeap(initial_children)
    filtered = [prefix for prefix in prefixes if accept(prefix)]
    nodes = [PrefixNode(prefix, sort_fn=sort_fn) for prefix in filtered]
    for node in sorted(nodes, reverse=False):
        heap.add(node)
    # create/show fake nodes
    if show_available:
        available = get_available_subnets(filtered)
        for node in sorted(get_available_subnets(filtered)):
            heap.add(node)
    return heap

SORT_BY = {
    "vlan_number": lambda x: x.vlan_number
}

def make_tree(prefixes, family=None, show_available=False, sort_by="ip"):
    """Return a prefix heap initially populated with RFC1918 addresses. Accepts
parameters rfc1918, ipv4 and ipv6 to return addresses of those respective
families.

    """
    family = {"ipv4", "ipv6"} if family is None else set(family)
    init = []

    # Create fake RFC1918 nodes
    if "rfc1918" in family:
        family.add("ipv4")
        init = [
            FauxNode("10.0.0.0/8", "rfc1918-a", "RFC1918"),
            FauxNode("172.16.0.0/12", "rfc1918-b", "RFC1918"),
            FauxNode("192.168.0.0/16", "rfc1918-c", "RFC1918")
        ]
    opts = {
        "initial_children": init,
        "family": family,
        "sort_fn": SORT_BY.get(sort_by, None),
        "show_available": show_available
    }
    result = make_prefix_heap(prefixes, **opts)
    return result


