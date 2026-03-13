"""Voice backend factory."""

from backends.base import VoiceBackend
from backends.nova_sonic import NovaSonicBackend
from backends.cascade import CascadeBackend

BACKENDS = {
    "nova_sonic": NovaSonicBackend,
    "cascade": CascadeBackend,
}


def create_backend(config: dict) -> VoiceBackend:
    """Create a VoiceBackend from a config dict.

    Args:
        config: Must contain "backend" key ("nova_sonic" or "cascade").
                Remaining keys are passed to the backend constructor.
    """
    backend_type = config.get("backend", "nova_sonic")
    cls = BACKENDS.get(backend_type)
    if cls is None:
        raise ValueError(
            f"Unknown backend: {backend_type!r}. Available: {list(BACKENDS)}"
        )
    return cls(config)
