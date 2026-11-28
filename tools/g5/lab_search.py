"""Lab-only copy of the M7 search schedule at 020fcc793e74.

Changes are a dense per-view objective hook and optional snapshots. D0 calls
the qualified application service independently.
"""
import numpy as np

from human3d.experimental import ContourLoss, RegisteredPose, raster
from human3d.native_rig import pose_transforms, rebind_joints, validate_rebind

def bounded_fit(basis, body, observations, checkpoint, dense=None, snapshots=None):
    """Reuse G4's bounded search and guarded progression towards rejected candidates."""
    quads = np.asarray([[index for index, _ in f["corners"]] for f in body["mesh"]["faces"]
                        if f["group"] == "body"], dtype=np.int32)
    rig = body["rig"]
    packed = {}
    for index, influences in enumerate(rig["skin"]):
        for name, weight in influences.items():
            packed.setdefault(name, [[], []])
            packed[name][0].append(index)
            packed[name][1].append(weight)
    packed = {name: (np.array(indices, dtype=int), np.array(weights)[:, None])
              for name, (indices, weights) in packed.items()}
    skinned = np.unique(np.concatenate([indices for indices, _ in packed.values()]))
    scaled = any(view.scale == "independent" for view in observations)
    fields = [key for key in basis.globals if key != "Height" or scaled]
    weights = np.array([1 / (1 + (view.uncertainty / 9) ** 2) for view in observations])
    calls = 0

    def objective(size):
        losses = [ContourLoss(view.mask, size, view.uncertainty) for view in observations]

        def calculate(parameters):
            nonlocal calls
            checkpoint()
            calls += 1
            mesh = basis.evaluate(parameters)
            joints = rebind_joints(rig, mesh)
            costs, overlap = [], {}
            for view, loss in zip(observations, losses):
                points = mesh
                if view.pose is not None:
                    points = mesh.copy()
                    points[skinned] = 0
                    transforms = (view.pose.transforms(joints) if isinstance(view.pose, RegisteredPose)
                                  else pose_transforms(rig, joints, view.pose))
                    for name, (rotation, translation) in transforms.items():
                        if name in packed:
                            indices, weights_ = packed[name]
                            points[indices] += (mesh[indices] @ rotation.T + translation) * weights_
                cost, overlap[view.id] = loss(raster(view.project, points, quads, size))
                if dense is not None:
                    cost += dense(view, points, size)
                costs.append(cost)
            if len(costs) > 2:
                costs = .22 * np.log1p(np.array(costs) / .22)
            prior = np.mean([(value - basis.initial[key]) ** 2 for key, value in parameters.items()])
            return float(np.average(costs, weights=weights) + .0015 * prior), overlap
        return calculate

    low, final = objective(96), objective(160)
    seed = basis.initial.copy()
    candidates = [seed]

    def sweep(parameters, selected, steps, evaluate):
        best, _ = evaluate(parameters)
        for step in steps:
            for key in selected:
                bounds = (.10, .90) if key in basis.globals else (-.65, .65)
                if key == "Age":
                    bounds = (.49, .90)
                center = parameters[key]
                for sign in (-1, 1):
                    value = float(np.clip(center + sign * step, *bounds))
                    if value == parameters[key]:
                        continue
                    trial = parameters | {key: value}
                    score, _ = evaluate(trial)
                    if score < best:
                        best, parameters = score, trial
        return parameters

    for gender in (.28, .72):
        candidates.append(sweep(seed | {"Gender": gender}, fields, (.18,), low))
    best = min(candidates, key=lambda p: low(p)[0])
    if snapshots is not None:
        snapshots["global"] = basis.evaluate(best)
    best = sweep(best, fields + list(basis.regional), (.12, .055), low)
    if snapshots is not None:
        snapshots["regional"] = basis.evaluate(best)
    candidates.append(best)
    candidates.append(sweep(best, fields + list(basis.regional), (.03,), final))
    ranked = sorted(((final(parameters), parameters) for parameters in candidates), key=lambda entry: entry[0][0])
    rejected = []
    unsafe = None
    for (loss, iou), parameters in ranked:
        vertices = basis.evaluate(parameters)
        try:
            validate_rebind(body, vertices)
        except ValueError as error:
            rejected.append(str(error))
            if unsafe is None:
                unsafe = parameters
            continue
        if unsafe:
            safe = parameters.copy()
            lo, hi = 0., 1.
            for _ in range(8):
                alpha = (lo + hi) / 2
                trial = {key: (1 - alpha) * safe[key] + alpha * unsafe[key] for key in safe}
                candidate = basis.evaluate(trial)
                try:
                    validate_rebind(body, candidate)
                except ValueError:
                    hi = alpha
                    continue
                lo = alpha
                score, overlap = final(trial)
                if score < loss:
                    vertices, parameters, loss, iou = candidate, trial, score, overlap
        return vertices, parameters, iou, {"loss": loss, "evaluations": calls,
                                           "rebind_rejections": rejected, "stature_optimized": scaled}
    raise ValueError(f"No structurally valid Engine B candidate. Try Engine A. {', '.join(rejected)}")

