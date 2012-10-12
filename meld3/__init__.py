# make these easier to import
try:
    from .meld3 import parse_xml
    from .meld3 import parse_html
    from .meld3 import parse_xmlstring
    from .meld3 import parse_htmlstring
except ImportError:
    from meld3 import parse_xml
    from meld3 import parse_html
    from meld3 import parse_xmlstring
    from meld3 import parse_htmlstring
