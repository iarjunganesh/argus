"""Keep the test suite hermetic.

Set before any ARGUS module is imported: a developer's local .env or shell credentials must not
change which code paths run, so local results match CI, which has neither.
"""

import os

os.environ["ARGUS_DISABLE_DOTENV"] = "1"

_CREDENTIAL_PREFIXES = ("AZURE_", "COSMOS_", "FOUNDRY_")
for _name in list(os.environ):
    if _name.startswith(_CREDENTIAL_PREFIXES) or _name in ("GITHUB_TOKEN", "USE_GITHUB_MODELS"):
        del os.environ[_name]
