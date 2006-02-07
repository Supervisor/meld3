#!/Users/chrism/projects/revelation/bin/python
import hotshot
import hotshot.stats
import profile as profiler
import pstats
import meld3
# get rid of the noise of setting up an encoding
# in profile output
'.'.encode('utf-8')

template = """<html xmlns:meld="http://www.plope.com/software/meld3">
  <head>
    <title meld:id="title">This is the title</title>
    <div meld:id="headslot">This is the head slot</div>
  </head>
  <body>
   <div>
     <form action="." method="POST">
     <table border="0" meld:id="table1">
       <tbody meld:id="tbody">
         <tr meld:id="tr" class="foo">
           <td meld:id="td1">Name</td>
           <td meld:id="td2">Description</td>
         </tr>
       </tbody>
     </table>
     </form>
    </div>
  </body>
</html>"""

class IO:
    def __init__(self):
        self.data = []

    def write(self, data):
        self.data.append(data)

    def getvalue(self):
        return ''.join(self.data)

    def clear(self):
        self.data = []

values = []
for thing in range(0, 20):
    values.append((str(thing), str(thing)))

io = IO()

def run(root, trace=False):
    clone = root.clone()
    ob = clone.findmeld('tr')
    for tr, (name, desc) in ob.repeat(values):
        tr.findmeld('td1').content(name)
        tr.findmeld('td2').content(desc)
    if trace:
        import pdb; pdb.set_trace()
    clone.write_html(io)
    foo = io.getvalue()
    io.clear()

def profile(num):
    #profiler= hotshot.Profile("logfile.dat")
    #profiler.run("run(root)")
    profiler.run("run(root)", 'logfile.dat')
    #profiler.close() 
    #stats = hotshot.stats.load("logfile.dat")
    stats = pstats.Stats('logfile.dat')
    stats.strip_dirs()
    stats.sort_stats('cumulative', 'calls')
    #stats.sort_stats('calls')
    stats.print_stats(num)

if __name__ == '__main__':
    root = meld3.parse_xmlstring(template)
    profile(40)
    import timeit
    t = timeit.Timer("run(root)", "from __main__ import run, root")
    print "300 runs", t.timeit(300)
    #run(root, trace=True)
