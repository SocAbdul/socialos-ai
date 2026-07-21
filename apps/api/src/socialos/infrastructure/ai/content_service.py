import time

from socialos.domain.social import Platform


class LocalAIContentService:
    provider = "local"
    model = "socialos-local-v1"
    prompt_version = "2026-07-21"

    async def generate_caption(self, text: str) -> tuple[str, dict[str, int], str, int]:
        return await self._result(text)

    async def adapt_for_platform(
        self, text: str, platform: Platform
    ) -> tuple[str, dict[str, int], str, int]:
        if platform == Platform.INSTAGRAM:
            result = f"{text.strip()}\n\nBuilt for the feed. Clear, visual, and easy to save."
        else:
            result = f"{text.strip()}\n\nA concise update for our community."
        return await self._result(result)

    async def generate_hashtags(self, text: str) -> tuple[str, dict[str, int], str, int]:
        return await self._result(f"{text.strip()}\n\n#marketing #smallbusiness #socialmedia")

    async def generate_call_to_action(self, text: str) -> tuple[str, dict[str, int], str, int]:
        return await self._result(f"{text.strip()}\n\nTell us what you would try first.")

    async def rewrite_tone(self, text: str, tone: str) -> tuple[str, dict[str, int], str, int]:
        return await self._result(f"[{tone}] {text.strip()}")

    async def translate_content(
        self, text: str, locale: str
    ) -> tuple[str, dict[str, int], str, int]:
        return await self._result(f"[{locale}] {text.strip()}")

    async def _result(self, text: str) -> tuple[str, dict[str, int], str, int]:
        started = time.perf_counter()
        token_usage = {
            "input_tokens": max(1, len(text) // 4),
            "output_tokens": max(1, len(text) // 5),
        }
        latency_ms = int((time.perf_counter() - started) * 1000)
        return text, token_usage, "0.000000", latency_ms
