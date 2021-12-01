"""A workaround to make auto-completion work for dataclass of pydantic

https://github.com/samuelcolvin/pydantic/issues/650#issuecomment-709945440
"""

from typing import TYPE_CHECKING

# Trick
if TYPE_CHECKING:
    from dataclasses import dataclass
else:
    from pydantic.dataclasses import dataclass

__all__ = ("dataclass",)
