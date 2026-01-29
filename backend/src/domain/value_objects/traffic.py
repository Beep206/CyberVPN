from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Traffic:
    bytes: int

    def __post_init__(self) -> None:
        if self.bytes < 0:
            raise ValueError("Traffic bytes cannot be negative")

    @property
    def kb(self) -> float:
        return self.bytes / 1024

    @property
    def mb(self) -> float:
        return self.bytes / (1024 ** 2)

    @property
    def gb(self) -> float:
        return self.bytes / (1024 ** 3)

    def __str__(self) -> str:
        if self.gb >= 1:
            return f"{self.gb:.2f} GB"
        if self.mb >= 1:
            return f"{self.mb:.2f} MB"
        return f"{self.kb:.2f} KB"
