class SocialProviderError(RuntimeError):
    """Base error with a stable meaning across provider adapters."""


class ProviderNotImplemented(SocialProviderError):
    pass


class CapabilityNotSupported(SocialProviderError):
    pass


class AuthenticationRequired(SocialProviderError):
    pass


class PermissionMissing(SocialProviderError):
    pass


class RetryableProviderError(SocialProviderError):
    pass


class PermanentProviderError(SocialProviderError):
    pass


class RateLimited(RetryableProviderError):
    pass


class MediaValidationError(PermanentProviderError):
    pass


class UncertainPublicationResult(SocialProviderError):
    pass
