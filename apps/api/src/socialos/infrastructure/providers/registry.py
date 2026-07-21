from socialos.application.posts.ports import SocialPublisher


class ProviderNotConfiguredError(LookupError):
    pass


class SocialProviderRegistry:
    def __init__(self, providers: list[SocialPublisher] | None = None) -> None:
        self._providers = {provider.provider_name: provider for provider in (providers or [])}

    def get(self, provider_name: str) -> SocialPublisher:
        try:
            return self._providers[provider_name]
        except KeyError as exc:
            raise ProviderNotConfiguredError(
                f"Social provider '{provider_name}' is not configured"
            ) from exc
