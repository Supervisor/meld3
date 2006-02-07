import meld3
from meldclone import clone
import time

parent = meld3._MeldElementInterface('a', {})
clonable = meld3._MeldElementInterface('b', {})
child1 = clonable.makeelement('d', {})
child2 = clonable.makeelement('e', {})
clonable.append(child1)
child1.append(child2)

for x in (0, 200):
    child2.append(child2.makeelement('tag', {str(x):1}))

for x in (0, 200):
    child1.append(child1.makeelement('tag', {str(x):1}))

NUM = 1000

start1 = time.time()
for x in range(0, NUM):
    thing = clone(clonable, parent)
end1 = time.time()

print "C: %010f" % (end1 - start1)

start2 = time.time()
for x in range(0, NUM):
    thing = clonable.clone()
end2 = time.time()

print "Py: %010f" % (end2 - start2)


