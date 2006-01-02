from meld3 import parse_html
import sys

def main(srcfile, tgtfile):
    srcroot = parse_html(srcfile)
    tgtroot = parse_html(tgtfile)
    changes = srcroot.diffmeld(tgtroot)
    added = changes['added']
    if added:
        print 'Added: %s' % ', '.join([ x.meldid() for x in added])
    removed = changes['removed']
    if removed:
        print 'Removed: %s' % ', '.join([ x.meldid() for x in removed])
    moved = changes['moved']
    if moved:
        print 'Moved: %s' % ', '.join([ x.meldid() for x in moved])

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
