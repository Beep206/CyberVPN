from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Geolocation:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {self.longitude}")

    def __str__(self) -> str:
        return f"({self.latitude}, {self.longitude})"
