import unittest

from meeting_ai.providers.asr.openai_whisper import _resolve_cuda_device


class ASRGPURequiredTest(unittest.TestCase):
    def test_auto_uses_cuda_when_available(self) -> None:
        self.assertEqual(_resolve_cuda_device("auto", True), "cuda")

    def test_auto_fails_when_cuda_missing(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "does not fall back to CPU"):
            _resolve_cuda_device("auto", False)

    def test_cpu_device_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "requires CUDA"):
            _resolve_cuda_device("cpu", True)

    def test_cuda_device_fails_when_unavailable(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "cannot see a CUDA device"):
            _resolve_cuda_device("cuda", False)


if __name__ == "__main__":
    unittest.main()
