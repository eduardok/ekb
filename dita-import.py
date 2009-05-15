import xml.sax, sys, re

def join(between, l):
    return unicode(between).join([unicode(i) for i in l])


treetop = None
def _die_find(n, list, path):
    if n == list:
	return path
    for i in list:
	p = _die_find(n, i, path + [list.name])
	if p:
	    return p

    
def die(n):
    if not treetop:
	raise Exception('treetop not set')
    path = _die_find(n, treetop, [])
    if path:
	raise Exception("%s->[%s]" % (join("->", path), repr(n)))
    else:
	raise Exception('node not found: %s' % repr(n))


class XmlNode:
    def __init__(self, name, attrs={}):
	self.name = str(name)
	self.attrs = dict(attrs)
	self.children = []

    def __repr__(self):
	if self.attrs:
	    return "<%s %s>" % (self.name, repr(self.attrs))
	else:
	    return "<%s>" % self.name

    def __iter__(self):
	return iter(self.children)

    def add(self, child):
	self.children.append(child)


class TextXmlNode(XmlNode):
    def __init__(self, text):
	XmlNode.__init__(self, '')
	self.text = text

    def __repr__(self):
	return repr(self.text)
    

class TreeHandler(xml.sax.ContentHandler):
    def __init__(self):
	xml.sax.ContentHandler.__init__(self)
	self.root = XmlNode('root')
	self.stack = [self.root]

    def startElement(self, name, attrs):
	e = XmlNode(name, attrs = attrs)
	self.stack[-1].add(e)
	self.stack.append(e)
	#print 'se(%s)' % repr(name)

    def endElement(self, name):
	e = self.stack.pop()
	#print 'ee(%s)' % repr(name)

    def characters(self, chars):
	#print 'tx(%s)' % repr(chars)
	top = self.stack[-1]
	e = TextXmlNode(text = chars)
	top.add(e)
	

def xml_to_tree(filename):
    p = xml.sax.make_parser()
    p.setFeature('http://xml.org/sax/features/validation', False)
    p.setFeature("http://xml.org/sax/features/external-general-entities", False)
    h = TreeHandler()
    p.setContentHandler(h)
    p.parse(open(filename))
    return h.root


def print_xmltree(children, indent):
    for n in children:
	print_xmlnode(n, indent)


def print_xmlnode(n, indent = 0):
    print '%s%s' % (' '*indent, repr(n))
    print_xmltree(n.children, indent+4)


class Element:
    def __init__(self):
	pass

    def __repr__(self):
	print 'representing(%s)' % self.__class__.__name__
	return "%s(%s)" % (self.__class__.__name__, repr(self.render(1)))

    def dump(self, indent):
	print indent + self.__class__.__name__

    def render(self, raw):
	print 'rendering(%s)' % self.__class__.__name__
	return ""


class Literal(Element):
    def __init__(self, text):
	assert(isinstance(text, basestring))
	self.text = text

    def dump(self, indent):
	Element.dump(self, indent)
	print "%s    %s" % (indent, repr(self.text))

    def render(self, raw):
	print 'rendering(%s)' % self.__class__.__name__
	if raw:
	    return self.text
	else:
	    return re.sub(r'[\n\r \t]+', u' ', self.text)


class Span(Element):
    def __init__(self, items):
	Element.__init__(self)
	assert(isinstance(items, list))
	for i in items:
	    print i
	    assert(isinstance(i, Element))
	self.items = items

    def dump(self, indent):
	Element.dump(self, indent)
	for i in self.items:
	    i.dump(indent + '    ')

    def render_item(self, item, raw):
	return item.render(raw)

    def render(self, raw):
	print 'rendering(%s)' % self.__class__.__name__
	out = []
	for i in self.items:
	    out.append(self.render_item(i, raw))
	return join("", out)


class Block(Span):
    def __init__(self, lineprefix, items):
	Span.__init__(self, items)
	assert(isinstance(lineprefix, basestring))
	self.lineprefix = lineprefix

    def render(self, raw):
	print 'rendering(%s)' % self.__class__.__name__
	t = Span.render(self, raw)
	t = re.sub("\n", "\n%s" % self.lineprefix, t)
	if not raw:
	    t = re.sub(r'^\s+|\s+$', '', t)
	return "\n%s\n" % t


class List(Span):
    def __init__(self, itemprefix, lineprefix, items):
	Span.__init__(self, items)
	assert(isinstance(itemprefix, basestring))
	assert(isinstance(lineprefix, basestring))
	self.itemprefix = itemprefix
	self.lineprefix = lineprefix

    def render_item(self, item, raw):
	if isinstance(item, Block):
	    ri = Span.render_item(self, item, raw).lstrip()
	    ri = re.sub("\n", "\n%s" % self.lineprefix, ri)
	    return (self.itemprefix + ri)
	else:
	    assert(item.render(0).strip() == '')
	    return ''

    def render(self, raw):
	print 'rendering(%s)' % self.__class__.__name__
	t = Span.render(self, raw)
	if not raw:
	    t = re.sub(r'^\s+|\s+$', '', t)
	return "\n%s\n" % t


class Section(Block):
    def __init__(self, title, items):
	Block.__init__(self, '', items)
	assert(isinstance(title, basestring))
	self.title = title

    def render(self, raw):
	print 'rendering(%s)' % self.__class__.__name__
	t = Block.render(self, raw)
	t = re.sub(re.compile("^#", re.M), "##", t)
	return "\n# %s\n%s" % (self.title, t)


def _subs(n):
    return list([parse_element(sub) for sub in n])

def parse_element(n):
    print 'pe(%s)' % n
    assert(isinstance(n, XmlNode))
    if isinstance(n, TextXmlNode):
	return Literal(n.text)
    elif n.name in ['root', 'task', 'taskbody', 'postreq', 'prereq']:
	return Section('Section (%s)' % n.name, _subs(n))
    elif n.name in ['steps']:
	return List('\n1. ', '    ', _subs(n))
    elif n.name in ['step', 'p', 'cmd', 'stepresult']:
	return Block('', _subs(n))
    elif n.name in ['note']:
	return Block('> ', [Literal('> **Note:**')] + _subs(n))
    elif n.name in ['info']:
	#return Block('', [Literal('<i>')] + _subs(n) + [Literal('</i>')])
	return Block('', _subs(n))
    elif n.name in ['uicontrol', 'wintitle']:
	return Span([Literal('**')] + _subs(n) + [Literal('**')])
    elif n.name in ['title']:
	# FIXME: capture the title to go into the parent section
	return Literal('')
    else:
	die(n)


def process(filename):
    tree = xml_to_tree(filename)
    global treetop
    treetop = tree
    print_xmlnode(tree)
    print "--------------------\n"

    pt = parse_element(tree)
    pt.dump('')
    print "--------------------\n"
    
    print repr(pt)
    if pt:
	enc = pt.render(0).encode('utf-8')
	print enc
	open("%s.txt" % filename, "w").write(enc)
    else:
	print 'Skipping %s' % filename

for name in sys.argv[1:]:
    process(name)

print 'done'
