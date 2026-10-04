"""One media selection policy shared by synchronous and unpublished assembly."""

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from .finalize_media import _configuration_for
from .flv import FlvFormatError, avc_configuration_dimensions
from .frame_rate import nominal_frame_rate


@dataclass(frozen=True)
class MediaPlan:
    """Ordered media and encoder facts, with no process or publication authority."""

    parts: tuple[Path, ...]
    stream_copy: bool
    target_size: tuple[int, int] | None
    nominal_rate: Fraction | None


def plan_media(parts, *, frame_rate_inspector, dimension_inspector=None, rate_selector=None):
    """Select the existing copy/reencode path for already validated, ordered parts."""
    configurations = tuple(_configuration_for(part) for part in parts)
    if len(set(configurations)) == 1:
        return MediaPlan(parts, True, None, None)
    target = target_size(configurations, dimension_inspector=dimension_inspector)
    rate = (rate_selector or nominal_frame_rate)(parts, inspector=frame_rate_inspector)
    return MediaPlan(parts, False, target, rate)


def target_size(configurations, *, dimension_inspector=None):
    """Use the existing maximum source dimensions without inventing encoder policy."""
    dimensions = dimension_inspector or avc_configuration_dimensions
    try:
        sizes = [dimensions(configuration) for configuration in configurations]
    except FlvFormatError as error:
        raise ValueError(f"could not determine AVC dimensions: {error}") from error
    return max(width for width, _ in sizes), max(height for _, height in sizes)
