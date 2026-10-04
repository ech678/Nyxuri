import "shapes"
import "shapes/MaterialShapes.js" as MaterialShapes

// Canvas-backed Material 3 shape. Ported 1:1 from end4-pC's MaterialShape
// (modules/common/widgets/MaterialShape.qml).
//
// Renamed because nyxuri already ships a `MaterialShape` in the M3Shapes
// fallback module, and eight files import both M3Shapes and qs.shared.controls
// — a second type of the same name would make those ambiguous. Everything else,
// including the enum order, is unchanged.
ShapeCanvas {
    id: root

    enum Shape {
        Circle,
        Square,
        Slanted,
        Arch,
        Fan,
        Arrow,
        SemiCircle,
        Oval,
        Pill,
        Triangle,
        Diamond,
        ClamShell,
        Pentagon,
        Gem,
        Sunny,
        VerySunny,
        Cookie4Sided,
        Cookie6Sided,
        Cookie7Sided,
        Cookie9Sided,
        Cookie12Sided,
        Ghostish,
        Clover4Leaf,
        Clover8Leaf,
        Burst,
        SoftBurst,
        Boom,
        SoftBoom,
        Flower,
        Puffy,
        PuffyDiamond,
        PixelCircle,
        PixelTriangle,
        Bun,
        Heart
    }

    required property var shape
    property double implicitSize

    implicitHeight: implicitSize
    implicitWidth: implicitSize
    polygonIsNormalized: true
    roundedPolygon: {
        switch (root.shape) {
        case MaterialShapeCanvas.Shape.Circle:
            return MaterialShapes.getCircle();
        case MaterialShapeCanvas.Shape.Square:
            return MaterialShapes.getSquare();
        case MaterialShapeCanvas.Shape.Slanted:
            return MaterialShapes.getSlanted();
        case MaterialShapeCanvas.Shape.Arch:
            return MaterialShapes.getArch();
        case MaterialShapeCanvas.Shape.Fan:
            return MaterialShapes.getFan();
        case MaterialShapeCanvas.Shape.Arrow:
            return MaterialShapes.getArrow();
        case MaterialShapeCanvas.Shape.SemiCircle:
            return MaterialShapes.getSemiCircle();
        case MaterialShapeCanvas.Shape.Oval:
            return MaterialShapes.getOval();
        case MaterialShapeCanvas.Shape.Pill:
            return MaterialShapes.getPill();
        case MaterialShapeCanvas.Shape.Triangle:
            return MaterialShapes.getTriangle();
        case MaterialShapeCanvas.Shape.Diamond:
            return MaterialShapes.getDiamond();
        case MaterialShapeCanvas.Shape.ClamShell:
            return MaterialShapes.getClamShell();
        case MaterialShapeCanvas.Shape.Pentagon:
            return MaterialShapes.getPentagon();
        case MaterialShapeCanvas.Shape.Gem:
            return MaterialShapes.getGem();
        case MaterialShapeCanvas.Shape.Sunny:
            return MaterialShapes.getSunny();
        case MaterialShapeCanvas.Shape.VerySunny:
            return MaterialShapes.getVerySunny();
        case MaterialShapeCanvas.Shape.Cookie4Sided:
            return MaterialShapes.getCookie4Sided();
        case MaterialShapeCanvas.Shape.Cookie6Sided:
            return MaterialShapes.getCookie6Sided();
        case MaterialShapeCanvas.Shape.Cookie7Sided:
            return MaterialShapes.getCookie7Sided();
        case MaterialShapeCanvas.Shape.Cookie9Sided:
            return MaterialShapes.getCookie9Sided();
        case MaterialShapeCanvas.Shape.Cookie12Sided:
            return MaterialShapes.getCookie12Sided();
        case MaterialShapeCanvas.Shape.Ghostish:
            return MaterialShapes.getGhostish();
        case MaterialShapeCanvas.Shape.Clover4Leaf:
            return MaterialShapes.getClover4Leaf();
        case MaterialShapeCanvas.Shape.Clover8Leaf:
            return MaterialShapes.getClover8Leaf();
        case MaterialShapeCanvas.Shape.Burst:
            return MaterialShapes.getBurst();
        case MaterialShapeCanvas.Shape.SoftBurst:
            return MaterialShapes.getSoftBurst();
        case MaterialShapeCanvas.Shape.Boom:
            return MaterialShapes.getBoom();
        case MaterialShapeCanvas.Shape.SoftBoom:
            return MaterialShapes.getSoftBoom();
        case MaterialShapeCanvas.Shape.Flower:
            return MaterialShapes.getFlower();
        case MaterialShapeCanvas.Shape.Puffy:
            return MaterialShapes.getPuffy();
        case MaterialShapeCanvas.Shape.PuffyDiamond:
            return MaterialShapes.getPuffyDiamond();
        case MaterialShapeCanvas.Shape.PixelCircle:
            return MaterialShapes.getPixelCircle();
        case MaterialShapeCanvas.Shape.PixelTriangle:
            return MaterialShapes.getPixelTriangle();
        case MaterialShapeCanvas.Shape.Bun:
            return MaterialShapes.getBun();
        case MaterialShapeCanvas.Shape.Heart:
            return MaterialShapes.getHeart();
        default:
            return MaterialShapes.getCircle();
        }
    }
}
