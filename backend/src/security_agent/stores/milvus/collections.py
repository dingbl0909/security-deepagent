from security_agent.stores.models import MilvusCollectionSpec

SECURITY_KNOWLEDGE = MilvusCollectionSpec(
    name="security_knowledge",
    description="Security SOP and knowledge chunks",
)

AGENT_EPISODIC_MEMORY = MilvusCollectionSpec(
    name="agent_episodic_memory",
    description="Agent episodic memory records",
)

DEFAULT_COLLECTIONS = [SECURITY_KNOWLEDGE, AGENT_EPISODIC_MEMORY]


class MilvusDependencyError(RuntimeError):
    pass


def ensure_collections(uri: str, specs: list[MilvusCollectionSpec] | None = None) -> list[str]:
    """Ensure Milvus collections exist.

    The concrete collection schema is intentionally deferred until embedding
    model dimensions and hybrid-search strategy are finalized. This helper gives
    T26 a stable import path and a clear error when pymilvus is unavailable.
    """

    try:
        from pymilvus import MilvusClient
    except ModuleNotFoundError as exc:
        raise MilvusDependencyError(
            "pymilvus is not installed; install the Milvus extra before running collection initialization"
        ) from exc

    client = MilvusClient(uri=uri)
    ensured: list[str] = []
    for spec in specs or DEFAULT_COLLECTIONS:
        if not client.has_collection(spec.name):
            client.create_collection(
                collection_name=spec.name,
                dimension=spec.dim,
                description=spec.description,
            )
        ensured.append(spec.name)
    return ensured

