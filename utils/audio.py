#utils/audio.py
import audioop

TWILIO_RATE   = 8_000
NOVA_IN_RATE  = 16_000
NOVA_OUT_RATE = 24_000


def twilio_to_nova(mulaw_bytes: bytes, resample_state=None) -> tuple[bytes, object]:
    """µ-law 8kHz → signed-16-bit PCM 16kHz (stateful)."""
    pcm_8k = audioop.ulaw2lin(mulaw_bytes, 2)
    pcm_16k, new_state = audioop.ratecv(
        pcm_8k, 2, 1, TWILIO_RATE, NOVA_IN_RATE, resample_state
    )
    return pcm_16k, new_state


def nova_to_twilio(pcm_24k: bytes, resample_state=None) -> tuple[bytes, object]:
    """Signed-16-bit PCM 24kHz → µ-law 8kHz (stateful)."""
    pcm_8k, new_state = audioop.ratecv(
        pcm_24k, 2, 1, NOVA_OUT_RATE, TWILIO_RATE, resample_state
    )
    mulaw = audioop.lin2ulaw(pcm_8k, 2)
    return mulaw, new_state