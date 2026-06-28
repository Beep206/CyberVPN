from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any


class CodeSetRejectedError(ValueError):
    def __init__(
        self,
        *,
        applications: Sequence[Mapping[str, Any]],
        message: str = "CODE_SET_REJECTED",
    ) -> None:
        super().__init__(message)
        self.code = "CODE_SET_REJECTED"
        self.applications = [dict(deepcopy(application)) for application in applications]
