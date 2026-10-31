"""
Orbit Launcher Physics Engine
Analytical Second-Order Spring Dynamics Matrix (Exact differential solver: x'' = -ω²(x - target) - 2ζωx')
"""


class Spring:
    """Exact analytical second-order spring dynamics solver."""

    def __init__(self, initial: float = 0.0, omega: float = 14.0, zeta: float = 0.70):
        self.current = initial
        self.target = initial
        self.velocity = 0.0
        self.omega = omega
        self.zeta = zeta

    def update(self, dt: float) -> bool:
        dt = min(0.05, max(0.001, dt))
        force = -(self.omega ** 2) * (self.current - self.target) - 2.0 * self.zeta * self.omega * self.velocity
        self.velocity += force * dt
        self.current += self.velocity * dt
        if abs(self.current - self.target) > 0.001 or abs(self.velocity) > 0.001:
            return True
        self.current = self.target
        self.velocity = 0.0
        return False
