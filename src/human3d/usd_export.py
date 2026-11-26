"""Author the fitted rest mesh, skin binding and initialized pose as OpenUSD."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import json
from zipfile import ZipFile
from math import isfinite
import re

from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdShade, UsdSkel, UsdUtils, Vt

from .frozen_body import deform_vertices
from .native_rig import infer_support_plane, pose_transforms, skin_vertices, validate_rebind, validate_pose
from .garments import measure_clearance, measure_garment_contacts, posed_garment, verify_layers


def _joint_paths(bones):
    paths = {}

    def path(name):
        if name not in paths:
            parent = bones[name]["parent"]
            token = Tf.MakeValidIdentifier(name)
            paths[name] = f"{path(parent)}/{token}" if parent else token
        return paths[name]

    ordered = sorted(bones, key=path)
    names = [paths[name] for name in ordered]
    if len(names) != len(set(names)):
        raise ValueError("ambiguous_joint_paths")
    valid, reason = UsdSkel.Topology(Vt.TokenArray(names)).Validate()
    if not valid:
        raise ValueError(reason)
    return ordered, names


def _matrix(rotation, position):
    result = Gf.Matrix4d(1)
    if rotation is not None:
        result.SetRotate(Gf.Matrix3d(*rotation.T.flatten().tolist()))
    result.SetTranslateOnly(Gf.Vec3d(*map(float, position)))
    return result


def _texture_material(stage, mesh, texture, directory, roughness, *, material_path="/Human/Appearance", file_name="albedo.png"):
    texture.save(directory / file_name, format="PNG")
    material = UsdShade.Material.Define(stage, material_path)
    surface = UsdShade.Shader.Define(stage, f"{material_path}/Surface")
    surface.CreateIdAttr("UsdPreviewSurface")
    surface.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
    surface.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    material.CreateSurfaceOutput().ConnectToSource(surface.ConnectableAPI(), "surface")
    coordinate = UsdShade.Shader.Define(stage, f"{material_path}/Coordinates")
    coordinate.CreateIdAttr("UsdPrimvarReader_float2")
    coordinate.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    coordinate.CreateOutput("result", Sdf.ValueTypeNames.Float2)
    image = UsdShade.Shader.Define(stage, f"{material_path}/Albedo")
    image.CreateIdAttr("UsdUVTexture")
    image.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(f"./{file_name}"))
    image.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
    image.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(coordinate.ConnectableAPI(), "result")
    image.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
    surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(image.ConnectableAPI(), "rgb")
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)


def _bind_mesh(stage, path, vertices, faces, texcoords, skin, joint_indices, skeleton_path):
    used = sorted({index for face in faces for index, _ in face})
    remap = {index: local_index for local_index, index in enumerate(used)}
    if not used:
        raise ValueError("empty_export_mesh")
    width = max(len(skin[index]) for index in used)
    indices, weights = [], []
    if any(not skin[index] for index in used):
        raise ValueError("unweighted_mesh_vertex")
    for index in used:
        influences = sorted(skin[index].items(), key=lambda pair: joint_indices[pair[0]])
        indices.extend([joint_indices[name] for name, _ in influences] + [0] * (width - len(influences)))
        weights.extend([weight for _, weight in influences] + [0.0] * (width - len(influences)))

    mesh = UsdGeom.Mesh.Define(stage, path)
    points = Vt.Vec3fArray([Gf.Vec3f(*map(float, vertices[index])) for index in used])
    mesh.CreatePointsAttr(points)
    mesh.CreateExtentAttr(UsdGeom.PointBased.ComputeExtent(points))
    mesh.CreateFaceVertexCountsAttr([len(face) for face in faces])
    mesh.CreateFaceVertexIndicesAttr([remap[index] for face in faces for index, _ in face])
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    uv = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
    uv.Set(Vt.Vec2fArray([Gf.Vec2f(*point) for point in texcoords]))
    uv.SetIndices([index for face in faces for _, index in face])
    binding = UsdSkel.BindingAPI.Apply(mesh.GetPrim())
    binding.CreateSkeletonRel().SetTargets([skeleton_path])
    binding.CreateGeomBindTransformAttr(Gf.Matrix4d(1))
    binding.CreateJointIndicesPrimvar(False, width).Set(indices)
    binding.CreateJointWeightsPrimvar(False, width).Set(weights)
    return mesh


def export_body(destination: Path, body, fit, alignment, *, texture=None, roughness=0.65, garments=(), ground=False):
    garments = tuple(garments)
    if any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', item.garment.name) for item in garments):
        raise ValueError("invalid_export_garment_name")
    if any(not isfinite(item.observed_fraction) or not 0 <= item.observed_fraction <= 1 for item in garments):
        raise ValueError("invalid_export_coverage")
    suffix = destination.suffix.lower()
    if texture is None and suffix not in {".usd", ".usda", ".usdc"}:
        raise ValueError("Use an OpenUSD filename ending in .usd, .usda, or .usdc.")
    if texture is not None and (suffix != ".usdz" or not 0.05 <= roughness <= 1):
        raise ValueError("Textured export requires a .usdz filename and valid roughness.")
    if garments and texture is None:
        raise ValueError("Garment assembly requires textured USDZ.")
    mesh_data, rig = body["mesh"], body["rig"]
    vertices = deform_vertices(body, fit.controls)
    joints = validate_rebind(body, vertices)
    transforms = pose_transforms(rig, joints, alignment)
    manifest = {"schema_version": 1, "garments": []}
    posed_body = skin_vertices(vertices, rig["skin"], transforms)
    validate_pose(body, vertices, posed_body)
    if garments:
        layer = verify_layers([item.garment for item in garments], body, posed_body, transforms)
        if layer is not None and layer.violations:
            raise ValueError("The garment layers do not have sufficient sampled clearance.")
        for item in garments:
            garment = item.garment
            posed_shell = posed_garment(garment, transforms)
            clearance = measure_clearance(garment, body, posed_body, posed_shell)
            if clearance.violations:
                raise ValueError(f"{garment.name} has {clearance.violations} sampled penetrations.")
            contacts = measure_garment_contacts(garment, body, vertices, posed_body, posed_shell)
            if contacts.intersections:
                raise ValueError(f"{garment.name} intersects the body. {contacts.describe()}")
            manifest["garments"].append({"prim": f"/Human/Garments/{garment.name}", "category": garment.category,
                                         "layer": garment.layer, "minimum_sampled_clearance_mm": clearance.minimum * 100,
                                         "observed_uv_fraction": item.observed_fraction})
    bones = rig["bones"]
    ordered, paths = _joint_paths(bones)
    joint_indices = {name: index for index, name in enumerate(ordered)}
    rest = {}
    posed = {}
    for name in ordered:
        head = joints[bones[name]["head"]]
        rest[name] = _matrix(None, head)
        rotation, translation = transforms[name]
        posed[name] = _matrix(rotation, rotation @ head + translation)

    def local(globals_):
        return Vt.Matrix4dArray([
            globals_[name] * globals_[parent].GetInverse() if (parent := bones[name]["parent"]) else globals_[name]
            for name in ordered
        ])

    faces = [face["corners"] for face in mesh_data["faces"] if face["group"] == "body"]

    with TemporaryDirectory(dir=destination.parent) as temporary:
        directory = Path(temporary)
        output = directory / ("body.usdc" if texture is not None else destination.name)
        pose = local(posed)

        def author_stage():
            stage = Usd.Stage.CreateNew(str(output))
            root = UsdSkel.Root.Define(stage, "/Human")
            stage.SetDefaultPrim(root.GetPrim())
            if ground:
                body_vertices = sorted({index for face in faces for index, _ in face})
                floor = infer_support_plane(rig, posed_body, body_vertices)
                if floor is not None:
                    root.AddTranslateOp().Set(Gf.Vec3d(0, -floor, 0))
                    root.GetPrim().SetCustomDataByKey("supportPlaneY", floor)
            UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
            UsdGeom.SetStageMetersPerUnit(stage, 0.1)
            skeleton = UsdSkel.Skeleton.Define(stage, "/Human/Rig")
            skeleton.CreateJointsAttr(paths)
            skeleton.CreateBindTransformsAttr(Vt.Matrix4dArray([rest[name] for name in ordered]))
            skeleton.CreateRestTransformsAttr(local(rest))
            animation = UsdSkel.Animation.Define(stage, "/Human/Pose")
            animation.CreateJointsAttr(paths)
            if not animation.SetTransforms(pose):
                raise ValueError("default_pose_authoring_failed")
            # Blender imports a constant authored animation when it spans two samples.
            stage.SetStartTimeCode(1)
            stage.SetEndTimeCode(2)
            for frame in (1, 2):
                if not animation.SetTransforms(pose, Usd.TimeCode(frame)):
                    raise ValueError("pose_sample_authoring_failed")
            UsdSkel.BindingAPI.Apply(skeleton.GetPrim()).CreateAnimationSourceRel().SetTargets([animation.GetPath()])
            mesh = _bind_mesh(stage, "/Human/Body", vertices, faces, mesh_data["texcoords"],
                              rig["skin"], joint_indices, skeleton.GetPath())
            if garments:
                UsdGeom.Scope.Define(stage, "/Human/Garments")
                UsdGeom.Scope.Define(stage, "/Human/GarmentMaterials")
            for item in garments:
                garment = item.garment
                path = f"/Human/Garments/{garment.name}"
                shell = _bind_mesh(stage, path, garment.points, garment.faces, garment.uv,
                                   garment.skin, joint_indices, skeleton.GetPath())
                material_path = f"/Human/GarmentMaterials/{garment.name}"
                _texture_material(stage, shell, item.texture, directory, 0.8,
                                  material_path=material_path, file_name=f"{garment.name}.png")
            if garments:
                stage.GetRootLayer().customLayerData = {"human3d_manifest": json.dumps(manifest, sort_keys=True)}
            if texture is not None:
                _texture_material(stage, mesh, texture, directory, roughness)
            stage.GetRootLayer().Save()
        author_stage()
        if texture is not None:
            package = directory / destination.name
            if not UsdUtils.CreateNewUsdzPackage(Sdf.AssetPath(str(output)), str(package)):
                raise ValueError("textured_package_creation_failed")
            output = package
        if texture is not None:
            with ZipFile(output) as archive:
                names = archive.namelist()
                expected = {"albedo.png", *(f"{item.garment.name}.png" for item in garments)}
                if (archive.testzip() is not None or len(names) != len(set(names))
                        or not expected <= {Path(name).name for name in names}):
                    raise ValueError("invalid_texture_package")
        def validate_stage():
            reopened = Usd.Stage.Open(str(output))
            if not reopened:
                raise ValueError("exported_stage_validation_failed")
            reopened_pose = UsdSkel.Animation.Get(reopened, "/Human/Pose")
            for frame in (1, 2):
                actual = reopened_pose.GetTransforms(Usd.TimeCode(frame))
                if len(actual) != len(pose) or any(not Gf.IsClose(a, b, 1e-5) for a, b in zip(actual, pose)):
                    raise ValueError("exported_pose_validation_failed")
            cache = UsdSkel.Cache()
            cache.Populate(UsdSkel.Root.Get(reopened, "/Human"), Usd.PrimDefaultPredicate)
            if not cache.GetSkelQuery(UsdSkel.Skeleton.Get(reopened, "/Human/Rig")):
                raise ValueError("exported_skeleton_validation_failed")
            if not cache.GetSkinningQuery(reopened.GetPrimAtPath("/Human/Body")):
                raise ValueError("exported_skin_validation_failed")
            if texture is not None:
                material, _ = UsdShade.MaterialBindingAPI(reopened.GetPrimAtPath("/Human/Body")).ComputeBoundMaterial()
                texture_shader = UsdShade.Shader.Get(reopened, "/Human/Appearance/Albedo")
                if not material or not texture_shader.GetInput("file").Get().resolvedPath:
                    raise ValueError("packaged_texture_validation_failed")
            for record in manifest["garments"]:
                prim = reopened.GetPrimAtPath(record["prim"])
                if not cache.GetSkinningQuery(prim):
                    raise ValueError("exported_garment_skin_validation_failed")
                material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
                shader = UsdShade.Shader.Get(reopened, material.GetPath().AppendChild("Albedo")) if material else None
                if not shader or not shader.GetInput("file").Get().resolvedPath:
                    raise ValueError("exported_garment_material_validation_failed")
        validate_stage()
        os.replace(output, destination)
