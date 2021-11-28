"""A workaround to make auto-completion work for dataclass of pydantic

https://github.com/samuelcolvin/pydantic/issues/650#issuecomment-709945440
"""

from typing import TYPE_CHECKING
from pydantic.dataclasses import dataclass

# Trick
if TYPE_CHECKING:
    from dataclasses import dataclass as dataclass
