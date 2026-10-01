import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import QtQuick.Window

Item {
    id: scene
    width: bridge.cardSize + 56; height: bridge.cardSize + 68
    focus: true
    readonly property var info: bridge.state
    readonly property real unit: bridge.cardScale
    readonly property bool awake: Window.window ? Window.window.visible : false
    readonly property bool dark: info.dark
    readonly property bool motion: info.motion
    readonly property color ink: dark ? "#f3f5f2" : "#171d1c"
    readonly property color muted: dark ? "#b6c2c4" : "#667270"
    readonly property color topTint: dark ? (info.tone === "peach" ? "#333039" : "#273b46")
                                             : (info.tone === "peach" ? "#e8e0dd" : "#dceaf2")
    readonly property color bottomTint: dark ? (info.tone === "blue" ? "#25333c" : info.tone === "cream" ? "#3c392b" : "#48352b")
                                                : (info.tone === "blue" ? "#eef4ec" : info.tone === "cream" ? "#fbefce" : "#ffe1be")
    readonly property color accent: info.tone === "peach" ? "#e79d59" : "#4386c2"
    readonly property color accentEnd: info.tone === "peach" ? "#f3c085" : "#9eb7dd"
    readonly property color materialTop: Qt.rgba(topTint.r, topTint.g, topTint.b, .97)
    readonly property color materialBottom: Qt.rgba(bottomTint.r, bottomTint.g, bottomTint.b, .97)

    Shortcut { sequence: "F5"; onActivated: bridge.refresh() }
    Shortcut { sequence: "Escape"; onActivated: bridge.hideWindow() }
    Shortcut { sequence: "Ctrl+Q"; onActivated: bridge.quit() }
    Shortcut { sequence: "Ctrl+M"; onActivated: bridge.openMenu() }
    Shortcut { sequence: "Ctrl+Left"; onActivated: bridge.nudge(-12, 0) }
    Shortcut { sequence: "Ctrl+Right"; onActivated: bridge.nudge(12, 0) }
    Shortcut { sequence: "Ctrl+Up"; onActivated: bridge.nudge(0, -12) }
    Shortcut { sequence: "Ctrl+Down"; onActivated: bridge.nudge(0, 12) }

    Timer {
        id: collapse
        interval: 320
        onTriggered: {
            if (!cardHover.hovered && !bubbleHover.hovered) bridge.setExpanded(false)
        }
    }

    Item {
        id: card
        objectName: "fullCard"
        x: 28; y: 28; width: bridge.cardSize; height: bridge.cardSize
        opacity: info.expanded ? 1 : 0
        // Text uses actual logical font sizes; only vector contours are
        // transformed. This keeps software-rendered small Chinese text clear.
        scale: info.expanded ? 1 : .94
        transformOrigin: Item.TopLeft
        visible: opacity > .001
        enabled: info.expanded
        Behavior on opacity { NumberAnimation { duration: scene.motion ? 140 : 0; easing.type: Easing.OutCubic } }
        Behavior on scale { NumberAnimation { duration: scene.motion ? 180 : 0; easing.type: Easing.OutCubic } }

        Item {
            width: 240; height: 240
            transform: Scale { xScale: scene.unit; yScale: scene.unit }
            Image {
                x: -28; y: -28; width: 296; height: 308
                source: "assets/card-shadow.png"
                sourceSize: Qt.size(592, 616)
                opacity: scene.dark ? .25 : .10
                smooth: true
            }
            Shape {
                id: surface
                anchors.fill: parent
                preferredRendererType: Shape.CurveRenderer
                antialiasing: true
                ShapePath {
                    strokeWidth: 0
                    fillGradient: LinearGradient {
                        x1: 200; y1: 0; x2: 20; y2: 240
                        GradientStop { position: 0; color: scene.materialTop }
                        GradientStop { position: 1; color: scene.materialBottom }
                    }
                    PathSvg { path: bridge.outline }
                }
            }
            Shape {
                anchors.fill: parent
                antialiasing: true
                preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    strokeWidth: 0
                    fillGradient: LinearGradient {
                        x1: 0; y1: 0; x2: 200; y2: 230
                        GradientStop { position: 0; color: scene.dark ? "#17ffffff" : "#22ffffff" }
                        GradientStop { position: .52; color: "#00ffffff" }
                        GradientStop { position: 1; color: "#02ffffff" }
                    }
                    PathSvg { path: bridge.outline }
                }
                ShapePath {
                    fillRule: ShapePath.OddEvenFill
                    strokeWidth: 0
                    fillGradient: LinearGradient {
                        x1: 0; y1: 0; x2: 230; y2: 240
                        GradientStop { position: 0; color: scene.dark ? "#65ffffff" : "#caffffff" }
                        GradientStop { position: .5; color: scene.dark ? "#22ffffff" : "#60ffffff" }
                        GradientStop { position: 1; color: "#13ffffff" }
                    }
                    PathSvg { path: bridge.rim }
                }
            }
        }
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onPressed: mouse => { if (mouse.button === Qt.LeftButton) bridge.dragStart() }
            onPositionChanged: mouse => { if (pressedButtons & Qt.LeftButton) bridge.dragMove() }
            onReleased: mouse => { if (mouse.button === Qt.LeftButton) bridge.dragEnd() }
            onCanceled: bridge.dragEnd()
            onClicked: mouse => { if (mouse.button === Qt.RightButton) bridge.openMenu() }
        }
        HoverHandler {
            id: cardHover
            onHoveredChanged: { if (hovered) collapse.stop(); else collapse.restart() }
        }

        Text {

            renderType: Text.NativeRendering
            x: 23 * scene.unit; y: 22 * scene.unit
            width: 122 * scene.unit
            text: info.brand
            color: scene.ink
            font.family: bridge.fontFamily
            font.pixelSize: 10 * scene.unit
            font.weight: Font.DemiBold
            font.letterSpacing: 1.25 * scene.unit
            elide: Text.ElideRight
        }
        Rectangle {
            id: dot
            x: 153 * scene.unit; y: 28 * scene.unit; width: 5 * scene.unit; height: 5 * scene.unit; radius: 2.5 * scene.unit
            color: info.stale ? "#cba875" : info.loading ? "#8dada9" : "#80dfac"
            Rectangle {
                anchors.centerIn: parent; width: 11 * scene.unit; height: 11 * scene.unit; radius: 5.5 * scene.unit
                color: dot.color; opacity: info.consuming ? .14 : .08
            }
            Rectangle {
                anchors.centerIn: parent; width: 8 * scene.unit; height: 8 * scene.unit; radius: 4 * scene.unit
                color: dot.color; opacity: info.consuming ? .20 : .12
            }
            HoverHandler { id: activityHover }
            ToolTip.visible: activityHover.hovered
            ToolTip.delay: 500
            ToolTip.text: info.activity + "\n" + info.status
            Accessible.name: info.activity
            SequentialAnimation on opacity {
                running: info.consuming && scene.motion && scene.awake
                loops: 3
                NumberAnimation { to: .40; duration: 850 }
                NumberAnimation { to: 1; duration: 850 }
            }
        }
        MiniButton {
            x: 163 * scene.unit; y: 16 * scene.unit; width: 24 * scene.unit
            caption: info.english ? "中" : "EN"
            description: info.english ? "Switch to Chinese" : "切换为英文"
            onClicked: bridge.toggleLanguage()
        }
        MiniButton {
            id: refreshButton
            x: 192 * scene.unit; y: 16 * scene.unit; width: 24 * scene.unit
            iconSource: "icons/refresh-cw.svg"
            description: info.english ? "Refresh quota" : "刷新额度"
            enabled: !info.loading
            onClicked: bridge.refresh()
        }

        Text {

            renderType: Text.NativeRendering
            x: 23 * scene.unit; y: 42 * scene.unit
            text: info.primaryTitle
            color: scene.ink
            font.family: info.english ? bridge.fontFamily : bridge.labelFontFamily
            font.pixelSize: Math.max(info.english ? 8 : 10, Math.round(11 * scene.unit))
        }
        Item {
            x: 21 * scene.unit; y: 61 * scene.unit; width: 196 * scene.unit; height: 65 * scene.unit
            Text {
                renderType: Text.NativeRendering
                id: mainNumber
                text: info.primary.number
                color: scene.ink
                font.family: bridge.fontFamily
                font.pixelSize: 54 * scene.unit
                font.weight: Font.Normal
                font.letterSpacing: -2.5 * scene.unit
            }
            Text {
                renderType: Text.NativeRendering
                anchors.left: mainNumber.right; anchors.leftMargin: 4 * scene.unit
                anchors.baseline: mainNumber.baseline
                text: info.primary.valid ? "%" : ""
                color: scene.ink
                font.family: bridge.fontFamily
                font.pixelSize: 17 * scene.unit
                font.weight: Font.DemiBold
            }
        }
        Rectangle {
            x: 23 * scene.unit; y: 126 * scene.unit; width: 194 * scene.unit; height: 4 * scene.unit; radius: 2 * scene.unit
            color: scene.dark ? "#244f6673" : "#1961778a"
            Rectangle {
                width: parent.width * info.primary.fraction
                height: parent.height; radius: 2 * scene.unit
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: scene.accent }
                    GradientStop { position: 1; color: scene.accentEnd }
                }
                Behavior on width { NumberAnimation { duration: scene.motion ? 350 : 0; easing.type: Easing.OutCubic } }
            }
        }
        Text {
            renderType: Text.NativeRendering
            x: 23 * scene.unit; y: 138 * scene.unit; width: 196 * scene.unit
            text: info.resetCaption
            color: scene.muted
            font.family: info.english ? bridge.fontFamily : bridge.labelFontFamily; font.pixelSize: Math.max(info.english ? 8 : 10, Math.round(10 * scene.unit))
            elide: Text.ElideRight
        }
        Text {
            renderType: Text.NativeRendering
            x: 23 * scene.unit; y: 167 * scene.unit; width: 196 * scene.unit
            text: info.weeklyTitle
            color: scene.muted
            font.family: info.english ? bridge.fontFamily : bridge.labelFontFamily; font.pixelSize: Math.max(info.english ? 8 : 10, Math.round(10 * scene.unit))
            elide: Text.ElideRight
        }
        Item {
            x: 22 * scene.unit; y: 180 * scene.unit; width: 130 * scene.unit; height: 33 * scene.unit
            Text {
                renderType: Text.NativeRendering
                id: weekNumber
                text: info.secondary.number
                color: scene.ink
                font.family: bridge.fontFamily; font.pixelSize: 29 * scene.unit
                font.letterSpacing: -1 * scene.unit
            }
            Text {
                renderType: Text.NativeRendering
                anchors.left: weekNumber.right; anchors.leftMargin: 1 * scene.unit
                anchors.baseline: weekNumber.baseline
                text: info.secondary.valid ? "%" : ""
                color: scene.ink
                font.family: bridge.fontFamily; font.pixelSize: 11 * scene.unit
            }
        }
        Button {
            id: credits
            x: 19 * scene.unit; y: 212 * scene.unit; width: 152 * scene.unit; height: 19 * scene.unit
            visible: info.creditsKnown && !info.stale
            padding: 4 * scene.unit
            text: info.creditsLabel + "  " + info.viewLabel
            hoverEnabled: true
            Accessible.name: info.creditsLabel
            contentItem: Text {
            renderType: Text.NativeRendering
                text: credits.text
                color: scene.ink
                font.family: info.english ? bridge.fontFamily : bridge.labelFontFamily; font.pixelSize: Math.max(info.english ? 8 : 10, Math.round(9 * scene.unit))
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle {
                radius: 5 * scene.unit
                color: credits.hovered ? (scene.dark ? "#17ffffff" : "#35ffffff") : "transparent"
                border.color: credits.activeFocus ? scene.accent : "transparent"
            }
            onClicked: bridge.showCredits()
        }
        MiniButton {
            x: 185 * scene.unit; y: 200 * scene.unit; width: 30 * scene.unit; height: 30 * scene.unit
            round: true
            iconSource: "icons/terminal.svg"
            description: info.english ? "Appearance and settings" : "外观与设置 · 切换小浮球"
            onClicked: bridge.openMenu()
        }
        Text {
            renderType: Text.NativeRendering
            x: 23 * scene.unit; y: 217 * scene.unit; width: 150 * scene.unit
            visible: !info.creditsKnown || info.stale
            text: info.status
            color: scene.muted
            font.family: info.english ? bridge.fontFamily : bridge.labelFontFamily; font.pixelSize: Math.max(info.english ? 8 : 10, Math.round(9 * scene.unit))
        }
        // Sample exports explicitly mark their content; real credit text stays
        // unobscured in production.
        Text {
            renderType: Text.NativeRendering
            x: 23 * scene.unit; y: 244 * scene.unit; width: 210 * scene.unit
            visible: bridge.isDemo
            text: info.english ? "SAMPLE DATA" : "示例数据 · 非真实额度"
            color: scene.muted
            font.family: bridge.fontFamily; font.pixelSize: 9 * scene.unit
        }
    }

    Item {
        id: bubble
        objectName: "compactBubble"
        x: 28; y: 28; width: 72; height: 72
        visible: opacity > .001
        opacity: info.expanded ? 0 : 1
        enabled: !info.expanded
        Behavior on opacity { NumberAnimation { duration: scene.motion ? 100 : 0 } }
        Image {
            x: -28; y: -28; width: 128; height: 140
            source: "assets/bubble-shadow.png"
            sourceSize: Qt.size(256, 280)
            opacity: .13
            smooth: true
        }
        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            antialiasing: true
            ShapePath {
                strokeWidth: 1; strokeColor: scene.dark ? "#38ffffff" : "#96ffffff"
                fillGradient: LinearGradient {
                    x1: 65; y1: 0; x2: 0; y2: 72
                    GradientStop { position: 0; color: scene.materialTop }
                    GradientStop { position: 1; color: scene.materialBottom }
                }
                PathSvg { path: bridge.bubbleOutline }
            }
        }
        Item {
            anchors.centerIn: parent
            width: bubbleNum.width + bubblePercent.width; height: bubbleNum.height
            Text {
                renderType: Text.NativeRendering
                id: bubbleNum
                text: info.primary.number
                color: scene.ink
                font.family: bridge.fontFamily; font.pixelSize: 26
                font.letterSpacing: -1
            }
            Text {
                renderType: Text.NativeRendering
                id: bubblePercent
                anchors.left: bubbleNum.right; anchors.baseline: bubbleNum.baseline
                text: info.primary.valid ? "%" : ""
                color: scene.ink
                font.family: bridge.fontFamily; font.pixelSize: 10
            }
        }
        HoverHandler {
            id: bubbleHover
            onHoveredChanged: {
                if (hovered && !bridge.exporting) { collapse.stop(); bridge.setExpanded(true) }
            }
        }
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            onPressed: mouse => { if (mouse.button === Qt.LeftButton) bridge.dragStart() }
            onPositionChanged: mouse => { if (pressedButtons & Qt.LeftButton) bridge.dragMove() }
            onReleased: mouse => { if (mouse.button === Qt.LeftButton) bridge.dragEnd() }
            onCanceled: bridge.dragEnd()
            onClicked: mouse => { if (mouse.button === Qt.RightButton) bridge.openMenu(); else bridge.setExpanded(true) }
        }
    }

    component MiniButton: Button {
        id: button
        property string caption: ""
        property url iconSource: ""
        property string description: ""
        property bool round: false
        height: 28 * scene.unit
        hoverEnabled: true
        Accessible.name: description
        ToolTip.visible: hovered
        ToolTip.delay: 600
        ToolTip.text: description
        background: Rectangle {
            radius: button.round ? 15 * scene.unit : 7 * scene.unit
            color: button.down ? "#60ffffff" : button.hovered ? "#50ffffff" : button.round ? "#b8ffffff" : "transparent"
            border.width: 1 * scene.unit
            border.color: button.activeFocus ? scene.accent : "transparent"
            Behavior on color { ColorAnimation { duration: scene.motion ? 100 : 0 } }
        }
        contentItem: Item {
            Text {
                renderType: Text.NativeRendering
                anchors.centerIn: parent
                text: button.caption
                color: scene.dark ? "#d8e6ea" : "#728b92"
                font.family: bridge.fontFamily; font.pixelSize: 9 * scene.unit; font.weight: Font.DemiBold
            }
            Image {
                anchors.centerIn: parent
                width: button.round ? 16 * scene.unit : 12 * scene.unit; height: width
                visible: button.iconSource.toString().length > 0
                source: button.iconSource.toString().length ? "assets/" +
                        (button.round ? "terminal" : "refresh-cw") +
                        (scene.dark && !button.round ? "-light.svg" : "-muted.svg") : ""
                sourceSize: Qt.size(32, 32)
                opacity: button.round ? .55 : .40
                RotationAnimation on rotation {
                    running: button === refreshButton && info.loading && scene.motion && scene.awake
                    loops: Animation.Infinite; from: 0; to: 360; duration: 900
                }
            }
        }
    }
}
