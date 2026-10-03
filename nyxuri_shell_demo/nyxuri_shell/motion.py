import math
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else hi if v > hi else v


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def ease_standard(t: float) -> float:
    return 4.0 * t * t * t if t < 0.5 else 1.0 - pow(-2.0 * t + 2.0, 3.0) / 2.0


def ease_emphasized(t: float) -> float:
    if t < 0.5:
        return 8.0 * t * t * t * t
    return 1.0 - pow(-2.0 * t + 2.0, 5.0) / 2.0


def ease_out_expo(t: float) -> float:
    return 1.0 if t >= 1.0 else 1.0 - pow(2.0, -10.0 * t)


def ease_out_quint(t: float) -> float:
    return 1.0 - pow(1.0 - t, 5.0)


EASING: dict = {
    "standard": ease_standard,
    "emphasized": ease_emphasized,
    "expo": ease_out_expo,
    "quint": ease_out_quint,
    "linear": lambda t: t,
}


@dataclass
class Spring:
    value: float = 0.0
    target: float = 0.0
    velocity: float = 0.0
    damping: float = 0.85
    stiffness: float = 423.0
    epsilon: float = 1e-4

    def set(self, target: float, immediate: bool = False) -> None:
        self.target = target
        if immediate:
            self.value = target
            self.velocity = 0.0

    def step(self, dt: float) -> float:
        dt = clamp(dt, 0.0, 1.0 / 30.0)
        accel = -self.stiffness * (self.value - self.target) - 2.0 * self.damping * math.sqrt(self.stiffness) * self.velocity
        self.velocity += accel * dt
        self.value += self.velocity * dt
        if abs(self.value - self.target) < self.epsilon and abs(self.velocity) < self.epsilon:
            self.value = self.target
            self.velocity = 0.0
        return self.value

    @property
    def settled(self) -> bool:
        return self.value == self.target and self.velocity == 0.0


@dataclass
class Spring2D:
    x: Spring = field(default_factory=Spring)
    y: Spring = field(default_factory=Spring)

    def set(self, x: float, y: float, immediate: bool = False) -> None:
        self.x.set(x, immediate)
        self.y.set(y, immediate)

    def step(self, dt: float) -> Tuple[float, float]:
        return (self.x.step(dt), self.y.step(dt))

    @property
    def settled(self) -> bool:
        return self.x.settled and self.y.settled


SPRING_PRESETS: dict = {
    "ring_bloom": (0.70, 14.0),
    "sector_snap": (1.00, 18.0),
    "flick_settle": (0.78, 22.0),
    "subring_in": (0.80, 15.0),
    "subring_out": (0.90, 16.0),
    "capsule_morph": (0.65, 12.0),
    "osd_pop": (0.80, 20.0),
    "panel_slide": (0.90, 18.0),
}


def make_spring(preset: str, value: float = 0.0) -> Spring:
    damping, freq = SPRING_PRESETS.get(preset, SPRING_PRESETS["sector_snap"])
    return Spring(value=value, damping=damping, stiffness=freq * freq, epsilon=1e-4)


@dataclass
class Tween:
    duration: float = 0.25
    curve: str = "standard"
    elapsed: float = 0.0
    running: bool = False
    on_done: Optional[Callable[[], None]] = None

    def start(self, duration: Optional[float] = None) -> None:
        if duration is not None:
            self.duration = max(1e-6, duration)
        self.elapsed = 0.0
        self.running = True

    def step(self, dt: float) -> float:
        if not self.running:
            return 1.0
        self.elapsed += dt
        t = clamp(self.elapsed / self.duration)
        if t >= 1.0:
            self.running = False
            if self.on_done:
                self.on_done()
        return EASING.get(self.curve, ease_standard)(t)

    @property
    def progress(self) -> float:
        if not self.running:
            return 1.0
        return EASING.get(self.curve, ease_standard)(clamp(self.elapsed / self.duration))


class FrameClock:
    def __init__(self, fps: int = 60):
        self.interval = 1.0 / max(1, fps)
        self._last = time.monotonic()
        self.frames = 0
        self.dropped = 0

    def tick(self) -> float:
        now = time.monotonic()
        dt = now - self._last
        if dt > self.interval * 3:
            self.dropped += 1
            dt = self.interval * 3
        self._last = now
        self.frames += 1
        return dt

    def reset(self) -> None:
        self._last = time.monotonic()


class MotionGroup:
    def __init__(self) -> None:
        self.items: List = []

    def add(self, item) -> None:
        self.items.append(item)

    def step(self, dt: float) -> bool:
        active = False
        for item in self.items:
            if isinstance(item, Spring):
                item.step(dt)
                active = active or not item.settled
            elif isinstance(item, Tween):
                item.step(dt)
                active = active or item.running
        return active

    @property
    def settled(self) -> bool:
        return all(
            (i.settled if isinstance(i, Spring) else not i.running)
            for i in self.items
        )


def _self_check() -> List[str]:
    problems: List[str] = []

    s = make_spring("sector_snap", 0.0)
    s.set(1.0)
    steps = 0
    while not s.settled and steps < 1000:
        s.step(1.0 / 60.0)
        steps += 1
    if not s.settled:
        problems.append("spring did not settle within 1000 frames")
    if abs(s.value - 1.0) > 1e-3:
        problems.append(f"spring settled at {s.value}")
    if steps > 200:
        problems.append(f"spring too slow: {steps} frames")

    tw = Tween(duration=0.2, curve="emphasized")
    tw.start()
    last = 0.0
    for _ in range(20):
        v = tw.step(0.02)
        if v < last - 1e-9:
            problems.append("tween not monotonic")
            break
        last = v
    if abs(last - 1.0) > 1e-6:
        problems.append(f"tween did not finish at 1.0: {last}")

    for name, fn in EASING.items():
        if abs(fn(0.0)) > 1e-9:
            problems.append(f"{name}(0) != 0")
        if abs(fn(1.0) - 1.0) > 1e-9:
            problems.append(f"{name}(1) != 1")

    g = MotionGroup()
    a = make_spring("ring_bloom")
    a.set(10.0)
    g.add(a)
    g.add(Tween(duration=0.1))
    g.items[-1].start()
    for _ in range(600):
        if not g.step(1.0 / 60.0):
            break
    if not g.settled:
        problems.append("motion group did not settle")

    return problems


if __name__ == "__main__":
    import sys

    issues = _self_check()
    if issues:
        print("self-check failed:")
        for p in issues:
            print("  -", p)
        sys.exit(1)
    print("ok")
