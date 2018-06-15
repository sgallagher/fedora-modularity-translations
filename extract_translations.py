#!/usr/bin/python3

import os
import sys
import koji
import git
import gi

from collections import defaultdict

gi.require_version('Modulemd', '1.0')
from gi.repository import Modulemd


def get_rawhide_version(session):
    return session.getBuildTargets('rawhide')[0]['build_tag_name'].partition('-build')[0]


def get_latest_modules_in_tag(session, tag):
    tagged = session.listTagged(tag, latest=False)

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

    return latest


def main():
    k = koji.ClientSession('https://koji.fedoraproject.org/kojihub')
    script_dir = os.path.dirname(os.path.realpath(__file__))

    # Get the repo we're running in
    repo = git.Repo(script_dir,
                    search_parent_directories=True)
    branch_version = repo.active_branch

    print(repr(branch_version.name))
    if branch_version.name == "master":
        branch_version = get_rawhide_version(k)
        print("Setting branch_version: %s" % branch_version)

    tags = ['%s-modular' % branch_version,
            '%s-modular-override' % branch_version,
            '%s-modular-pending' % branch_version,
            '%s-modular-signing-pending' % branch_version,
            '%s-modular-updates' % branch_version,
            '%s-modular-updates-candidate' % branch_version,
            '%s-modular-updates-pending' % branch_version,
            '%s-modular-updates-testing' % branch_version,
            '%s-modular-updates-testing-pending' % branch_version]

    tagged_builds = []
    for tag in tags:
        tagged_builds.extend(get_latest_modules_in_tag(k, tag))

    # Make the list unique since some modules may have multiple tags
    unique_builds = {}
    for build in tagged_builds:
        unique_builds[build['id']] = build

    translatable_strings = defaultdict(set)
    for build_id in unique_builds.keys():
        build = k.getBuild(build_id)
        print("Processing %s:%s" % (build['package_name'], build['nvr']))

        modulemds = Modulemd.objects_from_string(
            build['extra']['typeinfo']['module']['modulemd_str'])

        # We should only get a single modulemd document from Koji
        assert len(modulemds) == 1

        tstrings = translatable_strings[build['package_name']]
        tstrings.add(modulemds[0].props.summary)
        tstrings.add(modulemds[0].props.description)

        # Get any profile descriptions
        for profile_name, profile in modulemds[0].peek_profiles().items():
            if profile.props.description:
                tstrings.add(profile.props.description)

    for key, value in translatable_strings.items():
        with open("%s.pot" % key, 'w') as f:
            for tstring in value:
                f.write("msgid \"%s\"\n"
                        "msgstr \"\"\n\n" % tstring)



if __name__ == "__main__":
    main()