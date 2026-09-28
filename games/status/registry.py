from games.status.a2s import A2SStatusAdapter
from games.status.generic import GenericStatusAdapter
from games.status.minecraft import MinecraftStatusAdapter

STATUS_ADAPTERS = {
    "generic": GenericStatusAdapter(),
    "minecraft": MinecraftStatusAdapter(),
    "a2s": A2SStatusAdapter(),
}
SUPPORTED_STATUS_TYPES = frozenset(STATUS_ADAPTERS)
