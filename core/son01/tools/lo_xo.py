"""Duong cong lo xo (giong engine/lib/runtime.js) de dat keyframe trong CapCut."""


def spring_curve(stiffness=170, damping=18, mass=1.0, dur=1.0, dt=0.001):
    x, v, pts = 0.0, 0.0, []
    for i in range(int(dur / dt) + 1):
        pts.append(x)
        a = (-stiffness * (x - 1) - damping * v) / mass
        v += a * dt
        x += v * dt
    return pts


def spring_keys(stiffness=170, damping=18, mass=1.0, n=5, dur=0.45):
    """n diem (giay, tien_do) dat tai cac moc quan trong: dau, giua tang, dinh vot, ve, lang."""
    pts = spring_curve(stiffness, damping, mass, dur)
    # chon diem theo thoi gian chia deu tren duong cong (dau nhanh, cuoi cham)
    idx = [round((len(pts) - 1) * (i / (n - 1)) ** 1.6) for i in range(n)]
    out = [(i / 1000.0, round(pts[i], 4)) for i in idx]
    out[-1] = (out[-1][0], 1.0)
    return out


if __name__ == "__main__":
    for t, p in spring_keys(260, 22, n=5, dur=0.42):
        print(f"{t:.3f}s -> {p:.3f}")
