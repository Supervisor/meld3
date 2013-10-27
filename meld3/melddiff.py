from .meld3 import parse_html
import sys

def main(srcfile, tgtfile, out=sys.stdout):
    srcroot = parse_html(srcfile)
    tgtroot = parse_html(tgtfile)
    changes = srcroot.diffmeld(tgtroot)

    added = changes['unreduced']['added']
    if added:
        out.write('Added: %s\n' % ', '.join(
            [ x.meldid() for x in added]))

    removed = changes['unreduced']['removed']
    if removed:
        out.write('Removed: %s\n' % ', '.join(
            [ x.meldid() for x in removed]))

    moved = changes['reduced']['moved']
    if moved:
        out.write('Moved: %s\n' % ', '.join(
            [ x.meldid() for x in moved]))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
