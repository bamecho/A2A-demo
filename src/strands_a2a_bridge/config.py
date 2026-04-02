from dataclasses import dataclass


@dataclass(slots=True)
class AppConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    public_url: str = "http://127.0.0.1:8000"
    service_name: str = "Strands A2A Bridge"
