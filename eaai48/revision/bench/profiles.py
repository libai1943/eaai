"""Reconstruct executable time histories from each scene's lowest-cost accepted RegionCovOpt run."""
import csv
import json
import math
from pathlib import Path

import numpy as np

from verify import car, control, dock_many, spatial_many

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "figures" / "profiles"
FAMILIES = ("parking", "trailer", "uav", "arm")


def parking_profile(cfg, result):
    certificate, _ = car(cfg, result["z"])
    px, py, heading = cfg["endpoints"][:3]
    clock, steer, speed = 0., 0., 0.
    rows, changes = [], []
    old_gear = None

    def phase(duration, acceleration, steering_rate, curvature):
        nonlocal clock, px, py, heading, speed, steer
        if duration <= 0:
            return
        t = np.linspace(0., duration, max(2, math.ceil(duration / 0.035) + 1))
        ds = speed * t + 0.5 * acceleration * t * t
        dh = curvature * ds
        arc = ds * np.sinc(dh / (2 * np.pi))
        xx = px + arc * np.cos(heading + dh / 2)
        yy = py + arc * np.sin(heading + dh / 2)
        vv = speed + acceleration * t
        phi = steer + steering_rate * t
        rows.append(np.column_stack((clock + t, xx, yy, heading + dh, vv, phi,
                                     np.full(t.size, acceleration), np.full(t.size, steering_rate))))
        px, py, heading = xx[-1], yy[-1], heading + dh[-1]
        speed, steer, clock = vv[-1], phi[-1], clock + duration

    def steer_at_rest(target):
        delta = target - steer
        if abs(delta) > 1.e-14:
            phase(2. * abs(delta), 0., math.copysign(0.5, delta), 0.)

    for curvature, distance in np.array(result["z"]).reshape(-1, 2):
        if abs(distance) < 1.e-9:
            continue
        sign = np.sign(distance)
        steer_at_rest(math.atan(2.8 * curvature))
        if old_gear is not None and sign != old_gear:
            changes.append(clock)
        old_gear = sign
        length = abs(distance)
        peak = min(2.5, math.sqrt(length))
        phase(peak, sign, 0., curvature)
        phase(max(0., length - peak**2) / peak, 0., 0., curvature)
        phase(peak, -sign, 0., curvature)
    steer_at_rest(0.)
    values = np.vstack(rows)
    err = values[-1, 1:4] - cfg["endpoints"][3:]
    err[2] = math.remainder(err[2], 2 * np.pi)
    if max(abs(err)) > 1.e-5 or max(abs(values[-1, 4:6])) > 1.e-10:
        raise ValueError("Parking time law misses the terminal state")
    if abs(clock - certificate["J"]) > 1.e-8:
        raise ValueError("Parking duration disagrees with replay")
    return ["time", "x", "y", "theta", "v", "phi", "a", "omega"], values, changes, certificate


def trailer_profile(cfg, result):
    steps = 400
    check, states, _, _ = dock_many(cfg, [result], steps=steps)
    rows, changes = [], []
    clock, previous = 0., None
    for k, stroke in enumerate(np.array(result["z"]).reshape(-1, 5)):
        duration, gear = stroke[3:]
        if previous is not None and gear != previous:
            changes.append(clock)
        tau = np.linspace(0., 1., steps + 1)
        v, _, phi, omega, accel = control(tau, stroke[None, :])
        xx = states[0, k * steps:(k + 1) * steps + 1]
        rows.append(np.column_stack((clock + tau * duration, xx, v, phi, accel, omega)))
        clock += duration
        previous = gear
    return ["time", "x", "y", "theta", "psi", "v", "phi", "a", "omega"], np.vstack(rows), changes, check[0]


def spatial_profile(cfg, result):
    check = spatial_many(cfg, [result])[0]
    duration = result["z"][0]
    nodes = np.array(result["z"][1:]).reshape(cfg["N"], 9)
    dt = duration / (cfg["N"] - 1)
    state = np.asarray(cfg["start"], dtype=float)
    rows = []
    for k, node in enumerate(nodes[:-1]):
        tau = np.linspace(0., dt, 33)[:, None]
        acc = node[6:]
        pos = state[:3] + tau * state[3:] + 0.5 * tau**2 * acc
        vel = state[3:] + tau * acc
        rows.append(np.column_stack((k * dt + tau, pos, vel, np.broadcast_to(acc, pos.shape))))
        state = np.r_[pos[-1], vel[-1]]
        if np.max(abs(state - nodes[k + 1, :6])) >= 1.e-6:
            raise ValueError("Profile and stored collocation state disagree")
    if np.max(abs(state - cfg["goal"])) >= 1.e-3:
        raise ValueError("Spatial replay misses the endpoint")
    names = (["x", "y", "z", "vx", "vy", "vz", "ax", "ay", "az"] if cfg["kind"] == "uav"
             else ["q1", "q2", "q3", "dq1", "dq2", "dq3", "ddq1", "ddq2", "ddq3"])
    return ["time", *names], np.vstack(rows), [], check


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    with (ROOT / "output/verified.csv").open() as inp:
        ledger = list(csv.DictReader(inp))
    index = []
    for family in FAMILIES:
        for number in range(1, 13):
            name = f"{family}_{number:02}"
            options = [r for r in ledger if r["case"] == name and r["method"] == "adaptive" and r["valid"] == "1"]
            selected = min(options, key=lambda row: (float(row["cost"]), int(row["seed"])))
            seed = int(selected["seed"])
            source = f"{name}_adaptive_{seed}.json"
            result = json.loads((ROOT / "runs" / source).read_text())
            base = ROOT if family == "trailer" else ROOT.parent
            cfg = json.loads((base / "data" / (name + ".json")).read_text())
            replay = {"parking": parking_profile, "trailer": trailer_profile}.get(family, spatial_profile)
            columns, rows, changes, check = replay(cfg, result)
            if not check["ok"] or abs(check["J"] - float(selected["cost"])) > 1.e-6:
                raise ValueError(f"{name}: cost or independent acceptance mismatch")
            if not np.isfinite(rows).all() or rows[0, 0] != 0 or np.min(np.diff(rows[:, 0])) < -1.e-12:
                raise ValueError(f"{name}: invalid time grid")
            T = float(rows[-1, 0])
            expected = check["J"] if family in ("trailer", "parking") else result["z"][0]
            if abs(T - expected) > 1.e-8:
                raise ValueError(f"{name}: wrong final time")
            np.savetxt(DEST / (name + ".csv"), rows, fmt="%.15g", delimiter=",", header=",".join(columns), comments="")
            index.append(dict(case=name, family=family, seed=seed, accepted_seeds=len(options), source=source,
                              T=T, cost=check["J"], terminal_error=check["error"], switches=list(map(float, changes))))
    (DEST / "index.json").write_text(json.dumps(index, indent=2))
    print(len(index), "best accepted profiles reconstructed; cost, time and endpoint checked")
    for row in index:
        if row["case"] in ("parking_02", "trailer_04", "arm_04", "uav_04"):
            print(row)


if __name__ == "__main__":
    main()
