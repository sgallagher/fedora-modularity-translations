#!/usr/bin/env python

import sys

import koji

tagname = sys.argv[-1]

print("Looking up modules in tag %r" % tagname)

k = koji.ClientSession('https://koji.fedoraproject.org/kojihub')
tagged = k.listTagged(tagname, latest=False)

# Find the latest, in module terms.  Pungi does this.
# Collect all contexts that share the same NSV.
NSVs = {}
for entry in tagged:
    name, stream = entry['name'], entry['version']
    version = entry['release'].rsplit('.', 1)[0]

    NSVs[name] = NSVs.get(name, {})
    NSVs[name][stream] = NSVs[name].get(stream, {})
    NSVs[name][stream][version] = NSVs[name][stream].get(version, [])
    NSVs[name][stream][version].append(entry)

latest = []
for name in NSVs:
    for stream in NSVs[name]:
        version = sorted(list(NSVs[name][stream].keys()))[-1]
        latest.extend(NSVs[name][stream][version])

# Lastly, write it out.
for entry in latest:
    build = k.getBuild(entry['id'])
    filename = '%s.yaml' % build['nvr']
    print("Writing %s" % filename)
    with open(filename, 'w') as f:
        f.write(build['extra']['typeinfo']['module']['modulemd_str'])