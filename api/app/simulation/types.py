from dataclasses import dataclass
from typing import Tuple

@dataclass
class EigenFamily:
    eigenvalues: Tuple[float, ...]
    eigenvectors: Tuple[Tuple[float, ...], ...]