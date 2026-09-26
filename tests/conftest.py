"""Keep the test suite hermetic.

Set before any ARGUS module is imported: a developer's local .env must not change which code
paths run, so local results match CI, which has no .env.
"""

import os

os.environ["ARGUS_DISABLE_DOTENV"] = "1"
