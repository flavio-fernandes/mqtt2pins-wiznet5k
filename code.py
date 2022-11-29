import sys

cwd = ("/" + __file__).rsplit("/", 1)[
    0
]  # the current working directory (where this file is)
sys.path.append(cwd)

import mqtt2pins_wiznet5k
