"""Author the fitted rest mesh, skin binding and initialized pose as OpenUSD."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os

from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdShade, UsdSkel, UsdUtils, Vt

from .frozen_body import deform_vertices
from .native_rig import pose_transforms, validate_rebind


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


def _texture_material(stage, mesh, texture, directory, roughness):
    texture.save(directory / "albedo.png", format="PNG")
    material = UsdShade.Material.Define(stage, "/Human/Appearance")
    surface = UsdShade.Shader.Define(stage, "/Human/Appearance/Surface")
    surface.CreateIdAttr("UsdPreviewSurface")
    surface.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
    surface.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    material.CreateSurfaceOutput().ConnectToSource(surface.ConnectableAPI(), "surface")
    coordinate = UsdShade.Shader.Define(stage, "/Human/Appearance/Coordinates")
    coordinate.CreateIdAttr("UsdPrimvarReader_float2")
    coordinate.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    coordinate.CreateOutput("result", Sdf.ValueTypeNames.Float2)
    image = UsdShade.Shader.Define(stage, "/Human/Appearance/Albedo")
    image.CreateIdAttr("UsdUVTexture")
    image.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath("./albedo.png"))
    image.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
    image.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(coordinate.ConnectableAPI(), "result")
    image.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
    surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(image.ConnectableAPI(), "rgb")
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)


def export_body(destination: Path, body, fit, alignment, *, texture=None, roughness=0.65):
    suffix = destination.suffix.lower()
    if texture is None and suffix not in {".usd", ".usda", ".usdc"}:
        raise ValueError("Use an OpenUSD filename ending in .usd, .usda, or .usdc.")
    if texture is not None and (suffix != ".usdz" or not 0.05 <= roughness <= 1):
        raise ValueError("Textured export requires a .usdz filename and valid roughness.")
    mesh_data, rig = body["mesh"], body["rig"]
    vertices = deform_vertices(body, fit.controls)
    joints = validate_rebind(body, vertices)
    transforms = pose_transforms(rig, joints, alignment)
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
    used = sorted({index for face in faces for index, _ in face})
    remap = {index: local_index for local_index, index in enumerate(used)}
    width = max(len(rig["skin"][index]) for index in used)
    indices, weights = [], []
    if any(not rig["skin"][index] for index in used):
        raise ValueError("unweighted_body_vertex")
    for index in used:
        influences = sorted(rig["skin"][index].items(), key=lambda pair: joint_indices[pair[0]])
        indices.extend([joint_indices[name] for name, _ in influences] + [0] * (width - len(influences)))
        weights.extend([weight for _, weight in influences] + [0.0] * (width - len(influences)))

    with TemporaryDirectory(dir=destination.parent) as temporary:
        directory = Path(temporary)
        output = directory / ("body.usdc" if texture is not None else destination.name)
        stage = Usd.Stage.CreateNew(str(output))
        root = UsdSkel.Root.Define(stage, "/Human")
        stage.SetDefaultPrim(root.GetPrim())
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, 0.1)
        skeleton = UsdSkel.Skeleton.Define(stage, "/Human/Rig")
        skeleton.CreateJointsAttr(paths)
        skeleton.CreateBindTransformsAttr(Vt.Matrix4dArray([rest[name] for name in ordered]))
        skeleton.CreateRestTransformsAttr(local(rest))
        animation = UsdSkel.Animation.Define(stage, "/Human/Pose")
        animation.CreateJointsAttr(paths)
        animation.SetTransforms(local(posed))
        UsdSkel.BindingAPI.Apply(skeleton.GetPrim()).CreateAnimationSourceRel().SetTargets([animation.GetPath()])
        mesh = UsdGeom.Mesh.Define(stage, "/Human/Body")
        points = Vt.Vec3fArray([Gf.Vec3f(*vertices[index]) for index in used])
        mesh.CreatePointsAttr(points)
        mesh.CreateExtentAttr(UsdGeom.PointBased.ComputeExtent(points))
        mesh.CreateFaceVertexCountsAttr([len(face) for face in faces])
        mesh.CreateFaceVertexIndicesAttr([remap[index] for face in faces for index, _ in face])
        mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        uv = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
        uv.Set(Vt.Vec2fArray([Gf.Vec2f(*point) for point in mesh_data["texcoords"]]))
        uv.SetIndices([index for face in faces for _, index in face])
        binding = UsdSkel.BindingAPI.Apply(mesh.GetPrim())
        binding.CreateSkeletonRel().SetTargets([skeleton.GetPath()])
        binding.CreateGeomBindTransformAttr(Gf.Matrix4d(1))
        binding.CreateJointIndicesPrimvar(False, width).Set(indices)
        binding.CreateJointWeightsPrimvar(False, width).Set(weights)
        if texture is not None:
            _texture_material(stage, mesh, texture, directory, roughness)
        stage.GetRootLayer().Save()
        if texture is not None:
            package = directory / destination.name
            if not UsdUtils.CreateNewUsdzPackage(Sdf.AssetPath(str(output)), str(package)):
                raise ValueError("textured_package_creation_failed")
            output = package
        reopened = Usd.Stage.Open(str(output))
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
        os.replace(output, destination)
