from dataclasses import dataclass
from typing import Tuple

@dataclass
class EigenFamily:
    eigenvalues: Tuple[float, ...]
    eigenvectors: Tuple[Tuple[float, ...], ...]

class NotComputable(Exception):
    """A derived output's validity conditions are not met for this coil.

    Raised by facade properties whose formulas only apply under documented
    geometric assumptions (e.g. Medhurst's proximity model). The analysis
    converter catches it per-field and reports {value: null, reason} instead
    of failing the whole analysis; downstream properties that depend on the
    value chain the reason ("X depends on Y: ...").
    """

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)
