import os
# import json

try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources

libraries = {}

fwArray = []
fwEnv = os.getenv("frameworks", None)
if fwEnv is not None:
    fwArray = fwEnv.split(",")
else:
    with pkg_resources.open_text("aimmx", "frameworks.txt") as fwFile:
        fwArray = fwFile.read().splitlines()

# print("Frameworks array:", ",".join(fwArray))
for f in fwArray:
    if ":" in f:
        temp = f.split(":")
        libraries[temp[0].strip().lower()] = temp[1].strip()
    else:
        libraries[f.strip().lower()] = f.strip()

# print("Frameworks libraries:", json.dumps(libraries, indent=2))


def getFrameworks(modules):
    fws = []
    for mod in modules:
        if mod.lower() in libraries.keys():
            fws.append(libraries[mod.lower()])
    return fws
